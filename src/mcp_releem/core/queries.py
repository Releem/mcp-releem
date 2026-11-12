"""Read-only query investigation; no optimization creation or EXPLAIN execution."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ..api.client import APIError
from ..api.query_models import AnalyticsPage, Optimization, OptimizationPage, Proposal, ProposalPage
from .plans import summarize_plan
from .query_inputs import QueryInput
from .query_windows import check_window, normalize_period, query_time
from .results import Coverage, DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics

STATUS_LABELS = {
    0: "queued",
    1: "collecting_query_plan",
    2: "analyzing",
    3: "analysis_failed",
    4: "generated",
    5: "ready",
    6: "discovered",
    7: "awaiting_evaluation",
    8: "evaluated_with_improvement",
    9: "evaluated_without_improvement",
    10: "completed",
    11: "preserved",
    100: "dismissed",
}
OPERATIONS = {
    "analytics": "query_analytics",
    "proposals": "query_proposals",
    "optimizations": "optimizations",
    "optimization": "optimization",
}


def utc_time(value: str) -> datetime:
    """Upstream response timestamps are documented as UTC, including naive values."""
    return query_time(value, source_utc=True)


class QueryDiagnostics:
    def __init__(self, context: "Diagnostics") -> None:
        self.context = context

    async def read(self, server_id: str, **arguments: Any) -> DiagnosticResult:
        try:
            request = QueryInput(server_id=server_id, **arguments)
            operation = OPERATIONS[request.view]
            params = self.parameters(request)
            response = await self.context.client.read(operation, **params)
            result = self.result(request, response)
            result.evidence.append(self.context.evidence(operation))
        except (APIError, ValidationError) as exc:
            return self.context.error(exc)
        except (ValueError, OverflowError):
            return self.context.error(
                APIError("invalid_source_data", "Upstream query window is invalid")
            )
        return self.context.finish(result)

    def parameters(self, request: QueryInput) -> dict[str, Any]:
        common: dict[str, Any] = {"server_id": request.server_id}
        if request.view == "analytics":
            return {
                **common,
                "period": normalize_period(request.period, request.period_days)[0],
                **request.model_dump(
                    exclude={"view", "query_id", "optimization_id", "period_days", "period"},
                    exclude_none=True,
                ),
            }
        if request.view == "proposals":
            return {**common, "schema_name": request.schema_name, "query_id": request.query_id}
        if request.view == "optimizations":
            return {**common, "schema_name": request.schema_name, "limit": request.limit}
        return {**common, "optimization_id": request.optimization_id}

    def result(self, request: QueryInput, response: Any) -> DiagnosticResult:
        result = DiagnosticResult(scope={"server_id": request.server_id}, data={})
        assert result.data is not None
        if isinstance(response, AnalyticsPage):
            start, end = utc_time(response.start_time), utc_time(response.end_time)
            check_window(request, start, end)
            result.warn(
                "source_timezone",
                "Upstream offset-free timestamps are interpreted as confirmed UTC",
            )
            if request.end_date is not None and (
                request.period is not None or request.period_days is not None
            ):
                result.warn("period_overridden", "Explicit end_date overrides the supplied period")
            result.data = {
                "window": {"start_time": start.isoformat(), "end_time": end.isoformat()},
                "window_bounds": "[start_time,end_time)",
                "percentage_denominator": "all_queries_matching_filters",
                "units": {
                    "calls": "count",
                    "avg_time_ms": "ms",
                    "sum_time_sec": "s",
                    "sum_time_perc_total": "%",
                    "sum_time_perc_first": "% of highest-time query",
                },
                "items": [row.model_dump() for row in response.items[: request.limit]],
            }
            result.warn(
                "capped_query_ranking", "This is a capped ranking, not complete query coverage"
            )
            result.warn(
                "filtered_percentage_denominator",
                "Shares use all queries matching the filters, not only returned rows",
            )
        elif isinstance(response, ProposalPage):
            result.data["items"] = [
                self.proposal(item, result) for item in response.items[: request.limit]
            ]
        elif isinstance(response, OptimizationPage):
            result.data["items"] = [
                self.optimization(item, result, detail=False)
                for item in response.items[: request.limit]
            ]
        elif isinstance(response, Optimization):
            result.coverage = Coverage(requested=1, fetched=1, returned=1)
            result.data["optimization"] = self.optimization(response, result, detail=True)
            return result
        else:
            raise ValueError("Unexpected query response")
        returned = len(result.data["items"])
        fetched = len(response.items)
        result.coverage = Coverage(
            requested=request.limit,
            fetched=fetched,
            returned=returned,
            omitted=max(0, fetched - returned),
            complete=False,
        )
        if not returned:
            result.status = "no_data"
        result.warn(
            "retrieval_limited",
            "No upstream total/cursor is provided; omitted history cannot be ruled out",
        )
        return result

    def proposal(self, proposal: Proposal, result: DiagnosticResult) -> dict[str, Any]:
        row = proposal.model_dump()
        row["plan"] = summarize_plan(proposal.explain)
        self.plan_warning(row["plan"], result)
        return row

    def optimization(
        self, record: Optimization, result: DiagnosticResult, *, detail: bool
    ) -> dict[str, Any]:
        row = record.model_dump(exclude={"recommendations"})
        row["status_label"] = STATUS_LABELS.get(record.status)
        row["has_error"] = bool(record.error_message) or record.error_code not in (None, 0)
        result.warn(
            "workflow_status_only",
            "Optimization status is workflow state, not proof of safe application or benefit",
        )
        if record.status not in STATUS_LABELS:
            result.warn(
                "unknown_optimization_status",
                "Unknown numeric status retained without an invented label",
            )
        if detail:
            row["plan"] = summarize_plan(record.query_explain)
            self.plan_warning(row["plan"], result)
            row["recommendations"] = [
                self.proposal(item, result) for item in record.recommendations[:20]
            ]
            if len(record.recommendations) > 20:
                result.coverage.complete = False
                result.coverage.omitted += len(record.recommendations) - 20
                result.coverage.truncated_fields.append("optimization.recommendations")
                result.status = "partial"
                result.warn("proposals_truncated", "Linked proposals capped at 20")
        return row

    def plan_warning(self, plan: dict[str, Any], result: DiagnosticResult) -> None:
        if not plan["available"] or plan["details_omitted"]:
            result.coverage.complete = False
            if result.status == "ok":
                result.status = "partial"
        if not plan["available"]:
            result.warn(
                "plan_unavailable",
                "No existing plan is available; no plan was requested or invented",
            )
        elif plan["details_omitted"]:
            result.warn(
                "plan_details_omitted",
                "Selected JSON plan facts only; SQL, identifiers and predicates are omitted",
            )
