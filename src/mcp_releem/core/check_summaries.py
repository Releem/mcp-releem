"""Classify all-check detail snapshots without exposing arbitrary source values."""

from ..api.models import Details
from .results import DiagnosticResult


def apply_summary(result: DiagnosticResult, details: Details) -> None:
    assert result.data is not None
    failed: dict[str, list[str] | None] = {}
    unknown: dict[str, list[str] | None] = {}
    for section, checks in (
        ("health", details.health_checks),
        ("security", details.security_checks),
    ):
        failed_keys: list[str] = []
        unknown_keys: list[str] = []
        failed[section] = None if checks is None else failed_keys
        unknown[section] = None if checks is None else unknown_keys
        if not checks:
            result.warn(
                "check_summary_unavailable",
                "Missing or empty check snapshots do not establish health",
            )
            result.coverage.complete = False
            if checks is None:
                result.warn("failed_summary_unavailable", "A check summary is missing")
            continue
        for key, value in checks.items():
            status = value.get("failed") if isinstance(value, dict) else None
            if status is True:
                failed_keys.append(key)
            elif status is not False:
                unknown_keys.append(key)
                result.coverage.complete = False
                result.warn("unknown_check_results", "Some checks have no explicit boolean result")
                if not isinstance(value, dict) or status is not None:
                    result.warn(
                        "check_summary_source_shape", "Some check entries use an unrecognized shape"
                    )
    result.data["failed_summary"] = {
        **failed,
        "unknown": [
            item if isinstance(item, (str, int)) else "[unrecognized entry omitted]"
            for item in details.security_checks_unknown
        ],
        "decode_error": details.security_checks_decode_error,
    }
    result.data["unknown_summary"] = unknown
    result.warn(
        "check_summary_status_only",
        "Summaries classify explicit results; use full reports for values",
    )
    if details.security_checks_unknown:
        result.warn("unresolved_security_checks", "Security report contains unresolved entries")
        result.coverage.complete = False
    if details.security_checks_decode_error:
        result.warn("security_decode_error", "Security report could not be fully interpreted")
        result.coverage.complete = False
