"""Bounded review and workflow history without identities or opaque evidence."""

from datetime import datetime
from typing import Any

from ..api.recommendation_models import RecommendationDetail, Review, StatusEvent
from .diagnostic_inputs import instant
from .recommendation_evidence import evidence_reference
from .results import DiagnosticResult

STATUSES = frozenset({"new", "dismissed", "done", "outdated"})


def source_time(value: str | None, result: DiagnosticResult) -> str | None:
    if value is None:
        return None
    if datetime.fromisoformat(value).tzinfo is None:
        result.warn(
            "source_timezone_utc", "Naive recommendation time normalized as owner-confirmed UTC"
        )
    return instant(value, source_utc=True).isoformat()


def review_data(review: Review, result: DiagnosticResult) -> dict[str, Any]:
    row = review.model_dump(exclude={"review_details", "review_input_snapshot"})
    row["created_at"] = source_time(review.created_at, result)
    row["review_details_state"] = (
        "not_provided"
        if "review_details" not in review.model_fields_set
        else ("omitted" if review.review_details else "empty")
    )
    row["input_snapshot_available"] = review.review_input_snapshot is not None
    if review.review_details or review.review_input_snapshot is not None:
        result.warn(
            "review_payloads_omitted",
            "Opaque review details and input snapshots omitted for privacy",
        )
        result.coverage.complete = False
    return row


def status_data(event: StatusEvent, result: DiagnosticResult) -> dict[str, Any]:
    row = event.model_dump(exclude={"reason", "actor_type"})
    row["actor_type"] = (
        event.actor_type if event.actor_type in {"user", "system", "agent", "api"} else None
    )
    row["actor_type_unknown"] = row["actor_type"] is None
    if row["actor_type_unknown"]:
        result.warn(
            "unknown_actor_type", "Unrecognized actor category omitted; no identity inferred"
        )
    row["reason_available"] = event.reason is not None
    row["created_at"] = source_time(event.created_at, result)
    if event.new_status not in STATUSES or event.old_status not in STATUSES | {None}:
        result.warn(
            "unknown_recommendation_status", "Unknown recommendation workflow state retained"
        )
    result.warn(
        "status_identity_omitted", "Actor identities and status reason text omitted for privacy"
    )
    result.coverage.complete = False
    return row


def detail_data(
    record: RecommendationDetail, limit: int, result: DiagnosticResult
) -> dict[str, Any]:
    row = record.model_dump(
        exclude={"evidence", "current_review", "review_history", "status_history"}
    )
    for key in ("created_at", "updated_at"):
        row[key] = source_time(row[key], result)
    if record.status not in STATUSES:
        result.warn(
            "unknown_recommendation_status", "Unknown recommendation workflow state retained"
        )
    row["current_review"] = (
        review_data(record.current_review, result) if record.current_review else None
    )
    if record.current_review is None:
        result.warn(
            "current_review_unavailable",
            "No current review is available; priority evidence is incomplete",
        )
        result.coverage.complete = False
    row["evidence_reference"] = evidence_reference(record)
    row["evidence_pointer_available"] = (
        record.evidence is not None and record.evidence.pointer is not None
    )
    if row["evidence_pointer_available"]:
        result.warn(
            "evidence_pointer_omitted",
            "Evidence pointer omitted; typed reference selects the containing response",
        )
        result.coverage.complete = False
    if record.evidence is not None and row["evidence_reference"] is None:
        result.warn(
            "evidence_reference_rejected",
            "Evidence link does not match a supported same-server read",
        )
        result.coverage.complete = False
    elif record.evidence is None:
        result.warn("evidence_reference_unavailable", "No linked source evidence is available")
        result.coverage.complete = False
    elif record.source_type == "schema_check":
        result.warn(
            "latest_schema_evidence",
            "Linked schema evidence uses the latest run, not a pinned historical snapshot",
        )
    row["history_coverage"] = {}
    histories: list[tuple[str, list[Review] | list[StatusEvent] | None]] = [
        ("review_history", record.review_history),
        ("status_history", record.status_history),
    ]
    for key, records in histories:
        if records is None:
            row[key] = None
            row["history_coverage"][key] = {
                "available": False,
                "fetched": 0,
                "returned": 0,
                "omitted": 0,
                "complete": False,
            }
            result.warn(
                "history_unavailable",
                "A history was not provided; absence does not establish no changes",
            )
            result.coverage.complete = False
            continue
        converted = [
            review_data(item, result) if isinstance(item, Review) else status_data(item, result)
            for item in records
        ]
        row[key] = converted[:limit]
        omitted = max(0, len(records) - limit)
        row["history_coverage"][key] = {
            "available": True,
            "fetched": len(records),
            "returned": len(row[key]),
            "omitted": omitted,
            "complete": not omitted,
            "ordering": "upstream_order_unspecified",
        }
        if omitted:
            result.coverage.omitted += omitted
            result.coverage.complete = False
            result.coverage.truncated_fields.append("recommendation." + key)
            result.warn(
                "history_truncated",
                "Histories capped locally; increase history_limit for more entries",
            )
    if any(
        w.code in {"review_payloads_omitted", "status_identity_omitted"} for w in result.warnings
    ):
        result.coverage.truncated_fields.extend(
            ["recommendation.review_payloads", "recommendation.actor_identity"]
        )
    return row
