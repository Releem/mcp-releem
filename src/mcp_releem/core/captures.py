"""Aggregate only recognized processlist facts, without identities or SQL."""

import json
import math
from typing import Any

COMMANDS = frozenset(
    {
        "Query",
        "Sleep",
        "Connect",
        "Daemon",
        "Binlog Dump",
        "Binlog Dump GTID",
        "Execute",
        "Prepare",
        "Quit",
        "Killed",
    }
)


def summarize_capture(payload: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "parse_status": "unavailable" if payload is None else "unrecognized",
        "session_count": None,
        "examined_sessions": 0,
        "commands": {},
        "unknown_commands": 0,
        "max_duration_seconds": None,
        "details_omitted": True,
    }
    if isinstance(payload, str) and len(payload) <= 65536:
        try:
            payload = json.loads(payload)
        except (ValueError, RecursionError):
            return result
    if not isinstance(payload, list):
        return result
    result.update(parse_status="decoded", session_count=len(payload))
    maximum: float | int | None = None
    for row in payload[:500]:
        if not isinstance(row, dict):
            result["parse_status"] = "partially_decoded"
            continue
        result["examined_sessions"] += 1
        command = row.get("Command", row.get("command"))
        if isinstance(command, str) and command in COMMANDS:
            result["commands"][command] = result["commands"].get(command, 0) + 1
        else:
            result["unknown_commands"] += 1
        duration = row.get("Time", row.get("time"))
        if (
            isinstance(duration, str)
            and duration.isascii()
            and duration.isdigit()
            and len(duration) < 20
        ):
            duration = int(duration)
        if (
            isinstance(duration, (int, float))
            and not isinstance(duration, bool)
            and math.isfinite(duration)
            and duration >= 0
        ):
            maximum = duration if maximum is None else max(maximum, duration)
    result["max_duration_seconds"] = maximum
    result["rows_omitted"] = max(0, len(payload) - 500)
    return result
