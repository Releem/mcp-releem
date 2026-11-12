"""Map only verified same-server evidence paths to typed reads; never fetch URLs."""

import re
from typing import Any, get_args
from urllib.parse import parse_qs, urlsplit

from ..api.recommendation_models import RecommendationDetail
from .inputs import CheckType


def evidence_reference(record: RecommendationDetail) -> dict[str, Any] | None:
    if record.evidence is None:
        return None
    href = record.evidence.href
    if len(href) > 2048 or any(ord(c) <= 32 for c in href) or "\\" in href or "%" in href:
        return None
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        return None
    prefix = f"/v1/servers/{record.server_id}/"
    if not parsed.path.startswith(prefix):
        return None
    path = parsed.path[len(prefix) :]
    patterns = {
        "configuration": (
            r"configurations/([1-9][0-9]{0,19})",
            "configurations",
            "configuration_status_id",
        ),
        "query_optimization": (
            r"query-optimizations/([1-9][0-9]{0,19})",
            "query_evidence",
            "optimization_id",
        ),
        "deadlock": (r"deadlocks/([1-9][0-9]{0,19})", "deadlocks", "deadlock_id"),
    }
    if record.source_type in patterns and not parsed.query:
        pattern, tool, key = patterns[record.source_type]
        match = re.fullmatch(pattern, path)
        if match:
            return {
                "tool": tool,
                "arguments": {
                    "server_id": record.server_id,
                    "view": "optimization" if tool == "query_evidence" else "detail",
                    key: int(match[1]),
                },
            }
    if record.source_type == "schema_check" and path == "schema-checks":
        try:
            query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        except ValueError:
            return None
        if set(query) == {"type"} and len(query["type"]) == 1:
            check_type = query["type"][0]
            if check_type == "UNUSED_INDEX_NEW":
                check_type = "unused_index"
            if check_type in get_args(CheckType):
                return {
                    "tool": "server_findings",
                    "arguments": {
                        "server_id": record.server_id,
                        "sections": ["schema"],
                        "check_type": check_type,
                    },
                }
    if record.source_type == "security_check" and path == "security-checks" and not parsed.query:
        return {
            "tool": "server_findings",
            "arguments": {"server_id": record.server_id, "sections": ["security"]},
        }
    return None
