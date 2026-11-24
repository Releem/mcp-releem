"""Present bounded excerpts of the API's normalized analytics queries."""

import re
from typing import Any

from ..api.query_models import QueryRecord
from .redaction import Redactor
from .results import DiagnosticResult

_SOURCE_BYTES = 16 * 1024
_EXCERPT_BYTES = 2048
_RESPONSE_TEXT_BYTES = 8192
_UNSAFE = re.compile(r"--|/\*|#|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]")


def _excerpt(source: str | None, redactor: Redactor, remaining: int) -> tuple[str | None, str]:
    if source is None:
        return None, "unavailable"
    if len(source) > _SOURCE_BYTES or _UNSAFE.search(source):
        return None, "withheld"
    encoded = source.encode("utf-8")
    if len(encoded) > _SOURCE_BYTES:
        return None, "withheld"
    if not source.strip():
        return None, "unavailable"
    if redactor.has_sensitive_text(source):
        return None, "withheld"
    # The source is valid UTF-8. A byte cut can split only the final character.
    prefix = encoded[:_EXCERPT_BYTES].decode("utf-8", errors="ignore")
    if len(prefix.encode("utf-8")) > remaining:
        return None, "budget_exhausted"
    return prefix, "truncated" if len(encoded) > _EXCERPT_BYTES else "available"


def add_normalized_queries(
    rows: list[dict[str, Any]],
    records: list[QueryRecord],
    redactor: Redactor,
    result: DiagnosticResult,
) -> None:
    remaining = _RESPONSE_TEXT_BYTES
    for row, record in zip(rows, records, strict=True):
        query, status = _excerpt(record.query, redactor, remaining)
        row.update(query=query, query_status=status)
        if query is not None:
            remaining -= len(query.encode("utf-8"))
        if status in {"truncated", "withheld", "budget_exhausted"}:
            redactor.changed += 1
            result.status = "partial"
            result.warn(
                "query_text_limited",
                "Some normalized queries were shortened or withheld. See each row's query_status.",
            )
