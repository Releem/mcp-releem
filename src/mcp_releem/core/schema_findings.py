"""Interpret schema snapshot availability without exposing arbitrary schema payloads."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, get_args

from ..api.client import APIError, finite_float, reject_constant
from ..api.schema_models import SchemaSnapshot
from .diagnostic_inputs import instant
from .inputs import CheckType, FindingsInput
from .results import DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics


def canonical_type(code: int | str) -> int | str:
    if isinstance(code, str) and code.isascii():
        name = code.lower()
        if name == "unused_index_new":
            return "unused_index"
        if name in get_args(CheckType):
            return name
    return code


def payload_status(value: str) -> str:
    if not value:
        return "absent"
    if len(value) > 65536:
        return "too_large"
    try:
        parsed = json.loads(value, parse_constant=reject_constant, parse_float=finite_float)
        return "null" if parsed is None else "json_available"
    except (ValueError, RecursionError):
        return "decode_error"


def schema_report(
    context: "Diagnostics",
    response: SchemaSnapshot,
    request: FindingsInput,
    result: DiagnosticResult,
) -> tuple[dict[str, Any], str | None]:
    if response.timestamp is None and response.items:
        raise APIError("invalid_source_data", "Schema findings have no completed snapshot time")
    observed = (
        instant(response.timestamp, source_utc=True) if response.timestamp is not None else None
    )
    if response.timestamp is not None and datetime.fromisoformat(response.timestamp).tzinfo is None:
        result.warn(
            "source_timezone_utc", "Naive schema snapshot time normalized as owner-confirmed UTC"
        )
    if request.check_type is not None and any(
        canonical_type(row.type_id) != request.check_type for row in response.items
    ):
        raise APIError("invalid_source_data", "Schema check filter does not match source")
    filtered = request.schema_name is not None or request.check_type is not None
    state = (
        "not_run"
        if observed is None
        else "findings_returned"
        if response.items
        else ("no_matches" if filtered else "no_findings_in_completed_run")
    )
    rows = []
    for index, check in enumerate(response.items):
        data_status = payload_status(check.data)
        source_type = check.type_id
        check_type = canonical_type(source_type)
        if check_type not in get_args(CheckType) or check.is_check not in {0, 1}:
            result.warn(
                "unknown_schema_check", "Unknown check type/flag retained without interpretation"
            )
        if data_status in {"decode_error", "too_large"}:
            result.warn("schema_decode_error", "Some schema payloads cannot be safely interpreted")
        elif data_status in {"absent", "null"}:
            result.warn("schema_detail_absent", "Some schema detail payloads are absent")
        if check.is_check == 0 and check.count_checks > 0:
            result.warn(
                "schema_flag_count_conflict", "Finding flag and count disagree; inspect source"
            )
        if index < request.schema_limit:
            row_data = {
                "server_id": check.server_id,
                "type": check_type,
                "is_check": check.is_check,
                "has_finding": check.is_check == 1 if check.is_check in {0, 1} else None,
                "count_checks": check.count_checks,
                "data_status": data_status,
                "details_omitted": True,
            }
            if check_type != source_type:
                row_data["source_type_id"] = source_type
            rows.append(row_data)
    if response.items:
        result.coverage.complete = False
        result.coverage.truncated_fields.append("reports.schema.detail_payloads")
        result.warn(
            "schema_details_omitted",
            "Schema counts/flags only; arbitrary JSON payloads omitted for privacy",
        )
    if len(response.items) > len(rows):
        result.warn(
            "schema_rows_limited", "Schema rows omitted; narrow filters or increase schema_limit"
        )
    if response.server_id is None:
        result.warn(
            "schema_scope_missing",
            "Snapshot parent identifier missing; row scope checked where present",
        )
        result.coverage.complete = False
    if observed is None:
        result.warn(
            "schema_snapshot_absent",
            "No completed schema check run; empty output does not mean healthy",
        )
        result.coverage.complete = False
    elif (context.now() - observed).total_seconds() > 900:
        result.warn("report_age_exceeds_15m", "Report is over 15 minutes old; assess its freshness")
    result.warn(
        "schema_snapshot_only",
        "Completed checks are not a full schema or an engine compatibility guarantee",
    )
    return {
        "server_id": response.server_id,
        "timestamp": observed.isoformat() if observed else None,
        "state": state,
        "filters": {"schema_name": request.schema_name, "type": request.check_type},
        "items": rows,
        "coverage": {
            "fetched": len(response.items),
            "returned": len(rows),
            "omitted": len(response.items) - len(rows),
            "complete": not response.items
            and observed is not None
            and response.server_id is not None,
        },
    }, observed.isoformat() if observed else None
