"""Conservative incident presentation; opaque payloads are never model instructions."""

from typing import Any

from ..api.client import APIError
from ..api.incident_models import (
    Capture,
    Deadlock,
    DeadlockDetail,
    EventDetail,
    EventSummary,
    Task,
    TaskDetail,
)
from .captures import summarize_capture
from .diagnostic_inputs import instant
from .results import DiagnosticResult

TASK_STATUSES = {
    0: "queued",
    1: "succeeded",
    2: "claimed",
    3: "running",
    4: "failed",
    10: "succeeded",
}
TASK_TYPES = {
    0: "apply_configuration_manual",
    1: "generate_configuration",
    2: "update_agent",
    3: "query_optimization",
    4: "apply_configuration_dynamic",
    5: "apply_configuration_restart",
    6: "apply_schema_changes",
    7: "query_explain",
    8: "rollback_configuration",
}


def normalize_time(value: str | None) -> str | None:
    return instant(value, source_utc=True).isoformat() if value is not None else None


def record_data(record: Any, result: DiagnosticResult) -> dict[str, Any]:
    if isinstance(record, EventDetail):
        row = record.model_dump(exclude={"event_body"})
        row["event_id"] = str(record.event_id)
        row["payload_available"] = record.event_body is not None
        row["payload_omitted"] = True
        result.coverage.truncated_fields.append("event.event_body")
        result.warn("event_payload_omitted", "Arbitrary event payload omitted for privacy")
    elif isinstance(record, EventSummary):
        if int(record.event_id) > 18446744073709551615:
            raise APIError("invalid_source_data", "Upstream event ID exceeds UInt64")
        row = record.model_dump()
    elif isinstance(record, Deadlock):
        row = record.model_dump(exclude={"raw", "txn1", "txn2"})
        if record.max_active_time in {None, -1}:
            result.warn("duration_unknown", "Deadlock duration is unknown; -1/null is not zero")
        if isinstance(record, DeadlockDetail):
            row.update(
                raw_report_available=bool(record.raw),
                txn1_available=record.txn1 is not None,
                txn2_available=record.txn2 is not None,
            )
            result.coverage.truncated_fields.extend(["deadlock.raw", "deadlock.transactions"])
            result.warn(
                "deadlock_text_omitted", "Raw dump and transaction text omitted for privacy"
            )
    elif isinstance(record, Task):
        row = record.model_dump(exclude={"output", "error"})
        row.update(
            status_label=TASK_STATUSES.get(record.status),
            type=TASK_TYPES.get(record.type_id) if record.type_id is not None else None,
        )
        if record.status not in TASK_STATUSES or record.type_id not in TASK_TYPES:
            result.warn("unknown_task_code", "Unknown task codes retained without invented labels")
        row["status_time"] = normalize_time(record.status_time)
        if isinstance(record, TaskDetail):
            row.update(
                output_available=None if record.output is None else bool(record.output),
                error_available=None if record.error is None else bool(record.error),
                report_time=normalize_time(record.report_time),
            )
            result.coverage.truncated_fields.extend(["task.details", "task.output", "task.error"])
            result.warn(
                "task_text_omitted", "Task parameters/output/error text omitted for privacy"
            )
            if record.report_time is None:
                result.warn(
                    "final_report_absent",
                    "No final report is available; status alone is insufficient",
                )
        result.warn(
            "task_status_only", "Agent status does not establish effective changes or benefit"
        )
    elif isinstance(record, Capture):
        row = {
            "server_id": record.server_id,
            "timestamp": record.timestamp,
            "session_summary": summarize_capture(record.processlist),
        }
        result.coverage.truncated_fields.append("capture.session_rows")
        result.warn(
            "session_details_omitted", "Only recognized command counts and durations retained"
        )
        if row["session_summary"]["parse_status"] != "decoded":
            result.warn(
                "capture_not_decoded", "Snapshot content unavailable or not fully interpretable"
            )
        if row["session_summary"].get("rows_omitted", 0):
            result.warn("capture_rows_limited", "At most 500 sessions examined per capture")
    else:
        raise APIError("invalid_source_data", "Unexpected incident record shape")
    if "timestamp" in row:
        row["timestamp"] = normalize_time(row["timestamp"])
    return row
