"""Closed diagnostic operation registry. There is no generic URL/method interface."""

import re
from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter

from .diagnostic_models import (
    ConfigurationDetail,
    ConfigurationPage,
    MetricAverages,
    MetricCatalog,
    MetricSeries,
)
from .incident_models import (
    CapturePage,
    DeadlockDetail,
    DeadlockPage,
    EventDetail,
    EventPage,
    TaskDetail,
    TaskPage,
)
from .models import Details, RecommendationPage, Report, Server
from .query_models import AnalyticsPage, Optimization, OptimizationPage, ProposalPage
from .recommendation_models import RecommendationDetail
from .schema_models import SchemaSnapshot
from .segments import segment


class APIError(Exception):
    def __init__(self, code: str, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class Operation:
    path: str
    model: Any
    query_keys: frozenset[str] = frozenset()


OPERATIONS = {
    "fleet_recommendations": Operation(
        "/v1/servers/recommendations",
        RecommendationPage,
        frozenset(
            {
                "type_id",
                "category_id",
                "source_type",
                "status",
                "score_min",
                "score_max",
                "sort",
                "limit",
                "offset",
            }
        ),
    ),
    "schema": Operation(
        "/v1/servers/{server_id}/schema-checks", SchemaSnapshot, frozenset({"type", "schema_name"})
    ),
    "events": Operation(
        "/v1/servers/{server_id}/events",
        EventPage,
        frozenset({"start_time", "end_time", "limit", "offset"}),
    ),
    "event": Operation("/v1/servers/{server_id}/events/{event_id}", EventDetail),
    "deadlocks": Operation(
        "/v1/servers/{server_id}/deadlocks",
        DeadlockPage,
        frozenset({"start_time", "end_time", "limit"}),
    ),
    "deadlock": Operation("/v1/servers/{server_id}/deadlocks/{deadlock_id}", DeadlockDetail),
    "tasks": Operation(
        "/v1/servers/{server_id}/tasks", TaskPage, frozenset({"status", "type_id", "limit"})
    ),
    "task": Operation("/v1/servers/{server_id}/tasks/{task_id}", TaskDetail),
    "captures": Operation(
        "/v1/servers/{server_id}/processlist",
        CapturePage,
        frozenset({"start_time", "end_time", "limit"}),
    ),
    "configurations": Operation(
        "/v1/servers/{server_id}/configurations", ConfigurationPage, frozenset({"limit", "latest"})
    ),
    "configuration": Operation(
        "/v1/servers/{server_id}/configurations/{configuration_status_id}", ConfigurationDetail
    ),
    "metrics": Operation("/v1/servers/{server_id}/metrics", MetricCatalog),
    "metric_averages": Operation(
        "/v1/servers/{server_id}/metrics/averages",
        MetricAverages,
        frozenset({"start_time", "end_time"}),
    ),
    "metric_name": Operation(
        "/v1/servers/{server_id}/metrics/byName/{metric_name}",
        MetricSeries,
        frozenset({"start_time", "end_time", "interval", "aggregation", "use_trends"}),
    ),
    "metric_id": Operation(
        "/v1/servers/{server_id}/metrics/byId/{itemid}",
        MetricSeries,
        frozenset({"start_time", "end_time", "interval", "aggregation", "use_trends"}),
    ),
    "servers": Operation("/v1/servers", list[Server], frozenset({"hostname"})),
    "server": Operation("/v1/servers/{server_id}", Server),
    "details": Operation("/v1/servers/{server_id}/details", Details),
    "health": Operation("/v1/servers/{server_id}/health-checks", Report),
    "security": Operation("/v1/servers/{server_id}/security-checks", Report),
    "recommendations": Operation(
        "/v1/servers/{server_id}/recommendations",
        RecommendationPage,
        frozenset(
            {
                "type_id",
                "category_id",
                "source_type",
                "status",
                "score_min",
                "score_max",
                "sort",
                "limit",
                "offset",
            }
        ),
    ),
    "recommendation": Operation(
        "/v1/servers/{server_id}/recommendations/{recommendation_id}",
        RecommendationDetail,
    ),
    "query_analytics": Operation(
        "/v1/servers/{server_id}/query-analytics",
        AnalyticsPage,
        frozenset(
            {
                "period",
                "end_date",
                "start_date",
                "timezone",
                "sort_by",
                "order",
                "schema_name",
                "query_filter",
                "limit",
            }
        ),
    ),
    "query_proposals": Operation(
        "/v1/servers/{server_id}/query-analytics/{schema_name}/{query_id}/recommendations",
        ProposalPage,
    ),
    "optimizations": Operation(
        "/v1/servers/{server_id}/query-optimizations",
        OptimizationPage,
        frozenset({"schema_name", "limit"}),
    ),
    "optimization": Operation(
        "/v1/servers/{server_id}/query-optimizations/{optimization_id}",
        Optimization,
    ),
}


def prepare(operation: str, arguments: dict[str, Any]) -> tuple[Operation, str, dict[str, Any]]:
    if operation not in OPERATIONS:
        raise APIError("operation_denied", "Operation is not in the diagnostic read allowlist")
    spec = OPERATIONS[operation]
    path = spec.path
    arguments = arguments.copy()
    for key in re.findall(r"{(\w+)}", path):
        value = arguments.pop(key, None)
        if key in {"schema_name", "query_id", "metric_name"}:
            try:
                path = path.replace("{" + key + "}", segment(value))
            except (ValueError, TypeError):
                raise APIError("invalid_arguments", "Use a safe schema/query identifier") from None
            continue
        if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]{0,19}", str(value)):
            raise APIError("invalid_arguments", "Use an explicit canonical positive target ID")
        path = path.replace("{" + key + "}", str(value))
    if arguments.keys() - spec.query_keys:
        raise APIError("invalid_arguments", "Unsupported query arguments for this operation")
    return spec, path, {k: v for k, v in arguments.items() if v is not None}


def validate(spec: Operation, payload: Any, server_id: str | None) -> Any:
    parsed = TypeAdapter(spec.model).validate_python(payload)
    if server_id:
        parent = getattr(parsed, "server_id", None)
        if parent is not None and str(parent) != server_id:
            raise APIError("invalid_source_data", "Upstream snapshot target does not match request")
        records = getattr(parsed, "items", [parsed])
        for record in records:
            parent = getattr(record, "server_id", getattr(record, "id", None))
            if parent is not None and str(parent) != server_id:
                raise APIError(
                    "invalid_source_data", "Upstream source target does not match request"
                )
    return parsed
