"""Read configuration states and bounded, state-local variable evidence."""

import asyncio
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from ..api.client import APIError
from ..api.diagnostic_models import ConfigurationDetail, ConfigurationPage, ConfigurationState
from .configuration_changes import ConfigurationChanges
from .diagnostic_inputs import ConfigurationInput
from .redaction import Redactor
from .results import Coverage, DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics

APPLIED_DETAILS_TIMEOUT = 15


class ConfigurationDiagnostics:
    def __init__(self, context: "Diagnostics") -> None:
        self.context = context

    async def read(self, server_id: str, **arguments: Any) -> DiagnosticResult:
        try:
            request = ConfigurationInput(server_id=server_id, **arguments)
            if request.view == "detail":
                assert request.configuration_status_id is not None
                result = await self._detail(server_id, request.configuration_status_id)
            elif request.view == "applied_changes":
                result = await self._applied_changes(server_id, request.scan_limit)
            else:
                result = await self._list(request)
            result.warn(
                "configuration_state_only",
                "State records do not establish effective database settings or causation",
            )
            return self.context.finish(result)
        except (APIError, ValidationError) as exc:
            return self.context.error(exc)

    def _changes(self, state: ConfigurationDetail) -> ConfigurationChanges:
        return ConfigurationChanges(
            state, Redactor(self.context.client.settings.token.get_secret_value())
        )

    async def _read_state(self, server_id: str, state_id: int) -> ConfigurationDetail:
        response = cast(
            ConfigurationDetail,
            await self.context.client.read(
                "configuration", server_id=server_id, configuration_status_id=state_id
            ),
        )
        if response.configuration_status_id != state_id or str(response.server_id) != server_id:
            raise APIError("invalid_source_data", "Configuration state does not match target")
        return response

    async def _detail(self, server_id: str, state_id: int) -> DiagnosticResult:
        state = await self._read_state(server_id, state_id)
        row = state.model_dump(exclude={"variables"})
        row["variables_count"] = len(state.variables)
        changes = self._changes(state).detail(state)
        row["variable_changes"] = changes
        result = DiagnosticResult(
            status="partial",
            scope={"server_id": server_id},
            evidence=[self.context.evidence("configuration")],
            data={"configuration": row, "period_bounds": "[start,end)"},
            coverage=Coverage(
                requested=1,
                fetched=1,
                returned=1,
                complete=False,
                truncated_fields=["configuration_snapshots", "evaluation_metrics"],
            ),
        )
        result.warn(
            "configuration_source_omitted",
            "Raw configuration snapshots, recommendation text and untyped metrics omitted",
        )
        if any(change["omitted"] for change in changes.values()):
            result.warn(
                "configuration_values_withheld", "Unreviewed setting names or values withheld"
            )
        if state.history is None:
            result.warn("analysis_absent", "No configuration analysis snapshot is available")
        return result

    async def _list(self, request: ConfigurationInput) -> DiagnosticResult:
        latest = request.view == "latest"
        cap = 1 if latest else request.limit
        params = {"latest": True} if latest else {"limit": cap}
        page = cast(
            ConfigurationPage,
            await self.context.client.read("configurations", server_id=request.server_id, **params),
        )
        rows = page.items[:cap]
        result = DiagnosticResult(
            scope={"server_id": request.server_id},
            evidence=[self.context.evidence("configurations")],
            data={"items": [row.model_dump() for row in rows]},
            status="partial" if rows else "no_data",
            coverage=Coverage(
                requested=cap,
                fetched=len(page.items),
                returned=len(rows),
                omitted=max(0, len(page.items) - len(rows)),
                complete=False,
            ),
        )
        result.warn(
            "retrieval_limited",
            "List is bounded and has no total/cursor; omitted history cannot be ruled out",
        )
        return result

    async def _applied_changes(self, server_id: str, limit: int) -> DiagnosticResult:
        page = cast(
            ConfigurationPage,
            await self.context.client.read("configurations", server_id=server_id, limit=limit),
        )
        rows = page.items[:limit]
        eligible = {state.configuration_status_id: state for state in rows if _application(state)}
        items: list[dict[str, Any]] = []
        scan = {
            "state_limit": limit,
            "states_scanned": len(rows),
            "eligible_states": len(eligible),
            "detail_reads": 0,
            "states_with_insufficient_evidence": 0,
            "withheld_rows": 0,
        }
        result = DiagnosticResult(
            status="partial" if rows else "no_data",
            scope={"server_id": server_id},
            evidence=[self.context.evidence("configurations")],
            data={"items": items, "scan": scan, "application_time_unit": "unix_seconds_utc"},
            coverage=Coverage(requested=limit, fetched=len(page.items), complete=False),
        )
        completed = 0
        try:
            async with asyncio.timeout(APPLIED_DETAILS_TIMEOUT):
                for state_id, listed in eligible.items():
                    scan["detail_reads"] += 1
                    await self._collect_application(
                        result, listed, server_id, state_id, items, scan
                    )
                    completed += 1
        except TimeoutError:
            scan["states_with_insufficient_evidence"] += len(eligible) - completed
            result.warn("configuration_scan_timed_out", "The detail scan reached its time limit")
        items.sort(
            key=lambda row: (
                -row["applied_timestamp"],
                -row["configuration_status_id"],
                row["name"],
            )
        )
        result.coverage.returned = len(items)
        result.coverage.omitted = scan["withheld_rows"]
        if scan["withheld_rows"]:
            result.warn(
                "configuration_values_withheld", "Unreviewed setting names or values withheld"
            )
        if scan["states_with_insufficient_evidence"]:
            result.warn("configuration_evidence_incomplete", "Some states lack comparison evidence")
        result.warn("retrieval_limited", "Application dates are sorted within the scanned states")
        return result

    async def _collect_application(
        self,
        result: DiagnosticResult,
        listed: ConfigurationState,
        server_id: str,
        state_id: int,
        items: list[dict[str, Any]],
        scan: dict[str, int],
    ) -> None:
        try:
            state = await self._read_state(server_id, state_id)
        except APIError as exc:
            if exc.code not in {"not_found_or_inaccessible", "timeout", "dependency_unavailable"}:
                raise
            scan["states_with_insufficient_evidence"] += 1
            return
        evidence = self.context.evidence("configuration")
        if evidence.operation_id not in {item.operation_id for item in result.evidence}:
            result.evidence.append(evidence)
        if (
            not _application(state)
            or state.configuration_id != listed.configuration_id
            or state.applied_timestamp != listed.applied_timestamp
            or state.applied_status != listed.applied_status
            or state.history is None
            or not state.history.has_recommendation
        ):
            scan["states_with_insufficient_evidence"] += 1
            return
        comparison = self._changes(state).applied()
        if comparison["status"] == "unavailable" or comparison["uncompared"]:
            scan["states_with_insufficient_evidence"] += 1
        scan["withheld_rows"] += comparison["omitted"]
        metadata = {
            "applied_timestamp": state.applied_timestamp,
            "configuration_status_id": state_id,
            "configuration_id": state.configuration_id,
            "applied_status": state.applied_status,
        }
        if state.rollback_timestamp:
            metadata["rollback_timestamp"] = state.rollback_timestamp
        items.extend({**row, **metadata} for row in comparison["items"])


def _application(state: ConfigurationState) -> bool:
    initial = state.is_first and state.timestamp == state.configuration_timestamp
    return not initial and state.applied_timestamp > 0 and state.applied_status in {1, 2, 3}
