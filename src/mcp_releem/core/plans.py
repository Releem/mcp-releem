"""Bounded extraction of existing JSON EXPLAIN facts; never reconstruct a plan."""

import json
import math
from typing import Any

from ..api.client import finite_float, reject_constant

NUMBERS = {
    "Plan Rows": "plan_rows",
    "Actual Rows": "actual_rows",
    "Total Cost": "total_cost",
    "Actual Total Time": "actual_total_time_ms",
    "rows_examined_per_scan": "rows_examined_per_scan",
    "rows_produced_per_join": "rows_produced_per_join",
    "filtered": "filtered_percent",
}
NODE_TYPES = {
    "Seq Scan",
    "Index Scan",
    "Index Only Scan",
    "Bitmap Heap Scan",
    "Bitmap Index Scan",
    "Nested Loop",
    "Hash Join",
    "Merge Join",
    "Aggregate",
    "Group",
    "Sort",
    "Limit",
    "Gather",
    "Gather Merge",
    "Hash",
    "Materialize",
    "Append",
    "Result",
    "CTE Scan",
    "Subquery Scan",
    "Values Scan",
    "WindowAgg",
    "Unique",
    "SetOp",
    "Merge Append",
}
ACCESS_TYPES = {
    "ALL",
    "index",
    "range",
    "ref",
    "eq_ref",
    "const",
    "system",
    "index_merge",
    "ref_or_null",
    "unique_subquery",
    "index_subquery",
    "fulltext",
}


def summarize_plan(text: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": bool(text and text.strip()),
        "format": None,
        "nodes": [],
        "details_omitted": False,
    }
    if not result["available"]:
        return result
    result["details_omitted"] = True
    if text is None or len(text) > 65536:
        result["format"] = "oversized"
        return result
    try:
        parsed = json.loads(text, parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, RecursionError):
        result["format"] = "text"
        return result
    result["format"] = "json"
    pending = [(parsed, 0)]
    visited = 0
    while pending and visited < 512 and len(result["nodes"]) < 32:
        value, depth = pending.pop()
        visited += 1
        if depth > 24:
            continue
        if isinstance(value, dict):
            node: dict[str, Any] = {}
            if isinstance(value.get("Node Type"), str) and value["Node Type"] in NODE_TYPES:
                node["node_type"] = value["Node Type"]
            if isinstance(value.get("access_type"), str) and value["access_type"] in ACCESS_TYPES:
                node["access_type"] = value["access_type"]
            for source, target in NUMBERS.items():
                number = value.get(source)
                if (
                    isinstance(number, (int, float))
                    and not isinstance(number, bool)
                    and (isinstance(number, int) or math.isfinite(number))
                ):
                    node[target] = number
            if node:
                result["nodes"].append(node)
            pending.extend(
                (child, depth + 1) for child in value.values() if isinstance(child, (dict, list))
            )
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in value if isinstance(child, (dict, list)))
    return result
