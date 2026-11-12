"""Bounded metric catalog, series and hourly-trend comparisons."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ..api.client import APIError
from ..api.diagnostic_models import MetricCatalog
from .diagnostic_inputs import MetricInput, instant
from .metric_comparison import comparison, validate_window
from .results import Coverage, DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics


class MetricDiagnostics:
    def __init__(self, context: "Diagnostics") -> None:
        self.context = context

    async def read(self, server_id: str, **arguments: Any) -> DiagnosticResult:
        try:
            request = MetricInput(server_id=server_id, **arguments)
            if request.view == "compare":
                result = await self.compare(request)
            else:
                catalog = await self.context.client.read("metrics", server_id=server_id)
                self.validate_catalog(catalog)
                if request.view == "catalog":
                    rows = catalog.metrics[: request.limit]
                    count = len(catalog.metrics)
                    result = DiagnosticResult(
                        scope={"server_id": server_id},
                        data={"items": [row.model_dump() for row in rows]},
                        status="partial" if count > len(rows) else "ok" if rows else "no_data",
                        coverage=Coverage(
                            requested=request.limit,
                            fetched=count,
                            returned=len(rows),
                            omitted=count - len(rows),
                            complete=count == len(rows),
                        ),
                    )
                    if count > len(rows):
                        result.warn(
                            "catalog_truncated", "Increase limit to retrieve more catalog rows"
                        )
                else:
                    result = await self.series(request, catalog)
                result.evidence.insert(0, self.context.evidence("metrics"))
            return self.context.finish(result)
        except (APIError, ValidationError) as exc:
            return self.context.error(exc)
        except (ValueError, OverflowError):
            return self.context.error(
                APIError("invalid_source_data", "Invalid upstream metric time")
            )

    @staticmethod
    def validate_catalog(catalog: MetricCatalog) -> None:
        names = [row.name for row in catalog.metrics]
        ids = [row.itemid for row in catalog.metrics]
        if len(set(names)) != len(names) or len(set(ids)) != len(ids):
            raise APIError("invalid_source_data", "Metric catalog identities are ambiguous")

    async def series(self, request: MetricInput, catalog: MetricCatalog) -> DiagnosticResult:
        matches = [
            row
            for row in catalog.metrics
            if (
                row.itemid == request.itemid
                if request.itemid is not None
                else row.name == request.metric_name
            )
        ]
        if len(matches) != 1:
            raise APIError("metric_not_available", "Select a metric from this server's catalog")
        metric = matches[0]
        start, end = request.window(self.context.now())
        operation = "metric_id" if request.itemid is not None else "metric_name"
        selector = (
            {"itemid": request.itemid}
            if request.itemid is not None
            else {"metric_name": request.metric_name}
        )
        response = await self.context.client.read(
            operation,
            server_id=request.server_id,
            **selector,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            interval=request.interval,
            aggregation=request.aggregation,
            use_trends=request.use_trends,
        )
        if response.metric_name != metric.name or response.total_points != len(response.data):
            raise APIError("invalid_source_data", "Metric identity or point count does not match")
        if len(response.data) > 500:
            raise APIError(
                "result_too_large", "Series exceeds 500 points; use interval or a shorter window"
            )
        points = []
        previous = None
        interpreted_utc = False
        for point in response.data:
            if datetime.fromisoformat(point.timestamp).tzinfo is None:
                interpreted_utc = True
            timestamp = instant(point.timestamp, source_utc=True)
            if not start <= timestamp <= end or previous is not None and timestamp < previous:
                raise APIError(
                    "invalid_source_data", "Metric samples fall outside window or time order"
                )
            previous = timestamp
            points.append({"timestamp": timestamp.isoformat(), "value": point.value})
        result = DiagnosticResult(
            scope={"server_id": request.server_id},
            status="ok" if points else "no_data",
            data={
                "metric": metric.model_dump(),
                "series": points,
                "window": {"start_time": start.isoformat(), "end_time": end.isoformat()},
                "window_bounds": "upstream boundary inclusion unspecified",
                "sampling": {
                    "use_trends": request.use_trends,
                    "interval": request.interval,
                    "aggregation": request.aggregation,
                    "upstream_default_aggregation": "UNCONFIRMED"
                    if request.aggregation is None
                    else None,
                },
            },
            coverage=Coverage(requested=500, fetched=len(points), returned=len(points)),
            evidence=[self.context.evidence(operation)],
        )
        result.warn(
            "sampling_caveat",
            "Returned samples may contain gaps; an empty series does not establish health",
        )
        if interpreted_utc:
            result.warn(
                "source_timezone_utc",
                "Samples without timezone offsets were interpreted as UTC per upstream semantics",
            )
        return result

    async def compare(self, request: MetricInput) -> DiagnosticResult:
        start, end = request.window(self.context.now())
        base_start = (
            instant(request.baseline_start_time)
            if request.baseline_start_time
            else start - (end - start)
        )
        base_end = instant(request.baseline_end_time) if request.baseline_end_time else start
        responses = []
        evidence = []
        for left, right in [(start, end), (base_start, base_end)]:
            response = await self.context.client.read(
                "metric_averages",
                server_id=request.server_id,
                start_time=left.isoformat(),
                end_time=right.isoformat(),
            )
            validate_window(response, left, right)
            responses.append(response)
            evidence.append(self.context.evidence("metric_averages"))
        assert request.metric_names is not None
        result = comparison(responses[0], responses[1], request.metric_names, request.server_id)
        result.evidence = evidence
        return result
