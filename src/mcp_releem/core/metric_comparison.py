"""Comparison of upstream hourly trend summaries, preserving missing evidence."""

import math
from datetime import datetime
from typing import Any

from ..api.client import APIError
from ..api.diagnostic_models import MetricAverages
from .diagnostic_inputs import instant
from .results import Coverage, DiagnosticResult


def validate_window(response: MetricAverages, start: datetime, end: datetime) -> None:
    if (
        instant(response.start_time, source_utc=True),
        instant(response.end_time, source_utc=True),
    ) != (start, end):
        raise APIError("invalid_source_data", "Upstream metric window does not match request")
    names = [row.name for row in response.metrics]
    ids = [row.itemid for row in response.metrics]
    if len(set(names)) != len(names) or len(set(ids)) != len(ids):
        raise APIError("invalid_source_data", "Upstream metric identities are ambiguous")


def comparison(
    current: MetricAverages,
    baseline: MetricAverages,
    names: list[str],
    server_id: str,
) -> DiagnosticResult:
    result = DiagnosticResult(scope={"server_id": server_id})
    left = {metric.name: metric for metric in current.metrics}
    right = {metric.name: metric for metric in baseline.metrics}
    rows: list[dict[str, Any]] = []
    for name in names:
        a, b = left.get(name), right.get(name)
        reason = None
        percent = None
        if a is None or b is None or a.avg is None or b.avg is None:
            reason = "missing_data"
        elif a.itemid != b.itemid:
            reason = "identity_mismatch"
        elif a.units != b.units:
            reason = "unit_mismatch"
        elif b.avg == 0:
            reason = "zero_baseline"
        else:
            percent = (a.avg - b.avg) / abs(b.avg) * 100
            if not math.isfinite(percent):
                percent, reason = None, "numeric_overflow"
        rows.append(
            {
                "metric_name": name,
                "current": a.model_dump() if a else None,
                "baseline": b.model_dump() if b else None,
                "percent_change": percent,
                "delta_unavailable_reason": reason,
            }
        )
        if reason:
            result.warn(reason, "A comparison delta is unavailable; inspect the retained evidence")
    result.data = {
        "items": rows,
        "current_window": {
            "start_time": instant(current.start_time, source_utc=True).isoformat(),
            "end_time": instant(current.end_time, source_utc=True).isoformat(),
        },
        "baseline_window": {
            "start_time": instant(baseline.start_time, source_utc=True).isoformat(),
            "end_time": instant(baseline.end_time, source_utc=True).isoformat(),
        },
        "aggregation_basis": "mean of hourly averages; min/max of hourly extremes, not raw samples",
        "window_bounds": "[start_time,end_time)",
    }
    result.coverage = Coverage(
        requested=len(names), fetched=len(rows), returned=len(rows), complete=not result.warnings
    )
    result.status = "partial" if result.warnings else "ok"
    result.warn(
        "sampling_caveat",
        "Hourly trend summaries may omit samples; comparison does not establish causation",
    )
    return result
