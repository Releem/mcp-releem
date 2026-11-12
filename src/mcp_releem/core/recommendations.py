"""Prioritized server or explicitly selected fleet reads, with bounded detail history."""

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ..api.client import APIError
from .inputs import RecommendationInput
from .recommendation_detail import STATUSES, detail_data, source_time
from .results import Coverage, DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics


class RecommendationDiagnostics:
    def __init__(self, context: "Diagnostics") -> None:
        self.context = context

    async def read(self, server_id: str | None = None, **arguments: Any) -> DiagnosticResult:
        try:
            request = RecommendationInput(server_id=server_id, **arguments)
            operation = (
                "recommendation"
                if request.view == "detail"
                else ("fleet_recommendations" if request.scope == "fleet" else "recommendations")
            )
            params = request.model_dump(
                exclude={"view", "scope", "history_limit", "server_id", "recommendation_id"},
                exclude_none=True,
            )
            if request.view == "detail":
                params = {"recommendation_id": request.recommendation_id}
            if request.server_id is not None:
                params["server_id"] = request.server_id
            evidence = []
            accessible: set[str] | None = None
            if request.scope == "fleet":
                inventory = await self.context.client.read("servers")
                accessible = {server.id for server in inventory}
                evidence.append(self.context.evidence("servers"))
            response = await self.context.client.read(operation, **params)
            scope = (
                {"server_id": request.server_id}
                if request.server_id is not None
                else {"selection": "fleet"}
            )
            result = DiagnosticResult(
                scope=scope, evidence=[*evidence, self.context.evidence(operation)]
            )
            if request.view == "detail":
                result.coverage = Coverage(requested=1, fetched=1, returned=1)
                result.data = {
                    "recommendation": detail_data(response, request.history_limit, result)
                }
                if not result.coverage.complete:
                    result.status = "partial"
            else:
                self.page(request, response, accessible, result)
            result.warn(
                "workflow_status_only",
                "A done status does not prove a change was applied or effective",
            )
            return self.context.finish(result)
        except (APIError, ValidationError) as exc:
            return self.context.error(exc)
        except (ValueError, OverflowError):
            return self.context.error(
                APIError("invalid_source_data", "Invalid upstream recommendation metadata")
            )

    def page(
        self,
        request: RecommendationInput,
        response: Any,
        accessible: set[str] | None,
        result: DiagnosticResult,
    ) -> None:
        if accessible is not None:
            if any(record.server_id not in accessible for record in response.items) or (
                not accessible and response.total
            ):
                raise APIError(
                    "invalid_source_data", "Fleet recommendations exceed accessible inventory"
                )
            result.warn(
                "active_servers_only",
                "Fleet recommendations exclude inactive/deleted servers; not full fleet health",
            )
        if (
            response.offset != request.offset
            or len(response.items) > request.limit
            or (response.items and request.offset + len(response.items) > response.total)
        ):
            raise APIError(
                "invalid_source_data", "Recommendation pagination does not match request"
            )
        identities = [(record.server_id, record.id) for record in response.items]
        if len(set(identities)) != len(identities):
            raise APIError("invalid_source_data", "Duplicate recommendation identities in page")
        for record in response.items:
            for field in ("type_id", "category_id", "source_type", "status"):
                expected = getattr(request, field)
                if expected is not None and getattr(record, field) != expected:
                    raise APIError(
                        "invalid_source_data", "Recommendation filter does not match source"
                    )
            if request.score_min is not None and (
                record.priority_score is None or record.priority_score < request.score_min
            ):
                raise APIError(
                    "invalid_source_data", "Recommendation score filter does not match source"
                )
            if request.score_max is not None and (
                record.priority_score is None or record.priority_score > request.score_max
            ):
                raise APIError(
                    "invalid_source_data", "Recommendation score filter does not match source"
                )
        more = request.offset + len(response.items) < response.total
        rows = []
        for record in response.items:
            row = record.model_dump()
            for key in ("created_at", "updated_at"):
                row[key] = source_time(row[key], result)
            if record.status not in STATUSES:
                result.warn(
                    "unknown_recommendation_status",
                    "Unknown recommendation workflow state retained",
                )
            rows.append(row)
        result.data = {"items": rows}
        result.coverage = Coverage(
            requested=request.limit,
            fetched=len(response.items),
            returned=len(response.items),
            upstream_total=response.total,
            next_offset=request.offset + len(response.items) if more and response.items else None,
            complete=request.offset == 0 and not more,
            snapshot_consistent=False,
        )
        result.status = "ok" if response.items else "no_data"
        result.warn(
            "recommendation_pages_shift",
            "Pagination is not a frozen snapshot; concurrent changes may shift rows",
        )
