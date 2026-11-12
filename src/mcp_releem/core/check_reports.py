"""Full health/security report presentation, shared by finding sections."""

from typing import TYPE_CHECKING

from ..api.models import Report
from .results import DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics


def apply_report(context: "Diagnostics", result: DiagnosticResult, op: str, report: Report) -> None:
    assert result.data is not None
    safe = report.model_dump()
    safe["failed_checks"] = [
        item if isinstance(item, (str, int)) else "[unrecognized entry omitted]"
        for item in report.failed_checks
    ]
    for check in safe["checks"].values():
        check["documentation_reference_present"] = check.pop("learn_more_url") is not None
        if check["failed"] is None:
            result.coverage.complete = False
            result.warn("unknown_check_results", "Some checks have no explicit boolean result")
        if check["severity"] not in (None, "critical", "high", "moderate"):
            result.coverage.complete = False
            result.warn(
                "unknown_check_severity",
                "Unrecognized severity is upstream text, not a mapped rating",
            )
        if not isinstance(check["value"], (int, float, bool, type(None))):
            check["value"] = None
            result.coverage.complete = False
            result.redaction["omitted_check_values"] = (
                int(result.redaction.get("omitted_check_values", 0)) + 1
            )
            result.warn("check_value_omitted", "Nonscalar check values omitted by privacy policy")
    result.data["reports"][op] = safe
    if not report.checks:
        result.warn("report_checks_empty", "Empty checks do not establish health")
        result.coverage.complete = False
    if report.timestamp is None:
        result.warn("report_absent", "No report timestamp; empty checks do not establish health")
        result.coverage.complete = False
    elif (context.now().timestamp() - report.timestamp) > 900:
        result.warn("report_age_exceeds_15m", "Report is over 15 minutes old; assess its freshness")
    if report.failed_checks:
        known = set(report.checks)
        if any(not isinstance(item, str) or item not in known for item in report.failed_checks):
            result.warn("unresolved_security_checks", "Security report contains unresolved entries")
            result.coverage.complete = False
