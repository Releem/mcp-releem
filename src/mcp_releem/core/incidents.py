"""Historical incident reads with explicit scope, permission and coverage."""

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ..api.client import APIError
from .diagnostic_inputs import instant
from .incident_inputs import CaptureInput, DeadlockInput, EventInput, TaskInput
from .incident_records import record_data
from .results import Coverage, DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics

INPUTS = {
    "events": EventInput,
    "deadlocks": DeadlockInput,
    "task_outcomes": TaskInput,
    "captured_sessions": CaptureInput,
}
DETAILS = {
    "events": ("event", "event_id"),
    "deadlocks": ("deadlock", "deadlock_id"),
    "task_outcomes": ("task", "task_id"),
}
LISTS = {
    "events": "events",
    "deadlocks": "deadlocks",
    "task_outcomes": "tasks",
    "captured_sessions": "captures",
}


class IncidentDiagnostics:
    def __init__(self, context: "Diagnostics") -> None:
        self.context = context

    async def read(self, name: str, server_id: str, **arguments: Any) -> DiagnosticResult:
        try:
            request = INPUTS[name](server_id=server_id, **arguments)
            detail = getattr(request, "view", "list") == "detail"
            if (
                detail or name == "captured_sessions"
            ) and not self.context.client.settings.sensitive_details:
                raise APIError(
                    "sensitive_detail_disabled",
                    "Administrator must enable RELEEM_MCP_SENSITIVE_DETAILS for this read",
                )
            params: dict[str, Any] = {"server_id": server_id}
            window: dict[str, str] | None = None
            if detail:
                operation, key = DETAILS[name]
                params[key] = getattr(request, key)
            else:
                operation = LISTS[name]
                params["limit"] = request.limit
                if isinstance(request, (EventInput, DeadlockInput)) or (
                    isinstance(request, CaptureInput) and request.mode == "window"
                ):
                    window = request.window(self.context.now())
                    params.update(window)
                if isinstance(request, EventInput):
                    params["offset"] = request.offset
                elif isinstance(request, TaskInput):
                    params.update(status=request.status, type_id=request.type_id)
            response = await self.context.client.read(operation, **params)
            result = DiagnosticResult(
                scope={"server_id": server_id},
                evidence=[self.context.evidence(operation)],
                coverage=Coverage(complete=False),
            )
            if detail:
                target = getattr(response, "event_id", getattr(response, "id", None))
                if str(target) != str(params[key]):
                    raise APIError("invalid_source_data", "Incident record does not match target")
                result.data = {operation: record_data(response, result)}
                if operation == "deadlock":
                    result.data["units"] = {"max_active_time": "s"}
                result.coverage.requested = result.coverage.fetched = result.coverage.returned = 1
                result.status = "partial"
            else:
                result = self.page(request, response.items, window, result)
            return self.context.finish(result)
        except (APIError, ValidationError) as exc:
            result = self.context.error(exc)
            if name == "events" and getattr(exc, "status", None) == 404:
                result.warn(
                    "event_payload_may_be_absent",
                    "A summary may lack a detail payload; absence does not establish health",
                )
            return result
        except (ValueError, OverflowError):
            return self.context.error(
                APIError("invalid_source_data", "Invalid upstream incident time")
            )

    def page(
        self,
        request: Any,
        records: list[Any],
        window: dict[str, str] | None,
        result: DiagnosticResult,
    ) -> DiagnosticResult:
        cap = 1 if isinstance(request, CaptureInput) and request.mode == "latest" else request.limit
        rows = []
        seen: set[str] = set()
        for record in records:
            if window is not None:
                time = instant(record.timestamp, source_utc=True)
                if not instant(window["start_time"]) <= time <= instant(window["end_time"]):
                    raise APIError(
                        "invalid_source_data", "Incident timestamp falls outside requested window"
                    )
            if isinstance(request, TaskInput):
                for field in ("status", "type_id"):
                    expected = getattr(request, field)
                    if expected is not None and getattr(record, field) != expected:
                        raise APIError("invalid_source_data", "Task filter does not match source")
        for record in records[:cap]:
            if isinstance(request, EventInput):
                if record.event_id in seen:
                    result.warn("duplicate_events", "Duplicate event IDs omitted within this page")
                    continue
                seen.add(record.event_id)
            rows.append(record_data(record, result))
        result.data = {"items": rows}
        result.coverage = Coverage(
            requested=cap,
            fetched=len(records),
            returned=len(rows),
            omitted=len(records) - len(rows),
            complete=False,
            truncated_fields=result.coverage.truncated_fields,
        )
        if window is not None:
            result.data.update(
                window=window,
                window_bounds="[start_time,end_time]"
                if isinstance(request, EventInput)
                else "upstream boundary inclusion unspecified",
            )
        if isinstance(request, EventInput):
            result.coverage.snapshot_consistent = False
            result.coverage.next_offset = (
                request.offset + min(len(records), cap) if len(records) >= cap else None
            )
            result.coverage.complete = (
                request.offset == 0 and len(records) < cap and not result.coverage.omitted
            )
            result.warn(
                "offset_pages_shift",
                "Concurrent events can cause duplicate/skipped offset pages; no total",
            )
        else:
            result.warn(
                "retrieval_limited",
                "Capped history has no total/cursor; omitted records cannot be ruled out",
            )
        if isinstance(request, DeadlockInput):
            result.data["units"] = {"max_active_time": "s"}
        if isinstance(request, CaptureInput):
            result.data["live"] = False
            result.warn(
                "historical_capture", "Stored snapshot, not live sessions; inspect its timestamp"
            )
        result.status = "no_data" if not rows else "ok" if result.coverage.complete else "partial"
        return result
