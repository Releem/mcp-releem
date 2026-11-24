"""Configuration and server-scoped metric response allowlists."""

from typing import Any

from pydantic import Field

from .models import CodeId, UpstreamModel


class Period(UpstreamModel):
    start: int
    end: int | None = None


class ConfigurationHistory(UpstreamModel):
    timestamp: int
    performance_score: int
    performance_score_group: str | None = None
    recommendations_changes: float | None = None
    config_recommendations: Any = Field(default=None, exclude=True, repr=False)

    @property
    def has_recommendation(self) -> bool:
        return isinstance(self.config_recommendations, str) and bool(
            self.config_recommendations.strip()
        )


class Variable(UpstreamModel):
    name: str
    value: str
    is_dynamic: int | None = None


class ConfigurationState(UpstreamModel):
    configuration_status_id: int
    configuration_id: int
    server_id: int
    timestamp: int
    configuration_timestamp: int | None = None
    applied_status: CodeId
    applied_timestamp: int
    is_first: bool
    required_restart: int | None = None
    recommendations_changes: float | None = None


class ConfigurationDetail(ConfigurationState):
    applied_status: CodeId = 0
    variables: list[Variable]
    variables_orig: Any = Field(default=None, exclude=True, repr=False)
    source_variables: Any = Field(default=None, exclude=True, repr=False)
    history: ConfigurationHistory | None = None
    period: Period | None = None
    rollback_timestamp: int | None = None


class ConfigurationPage(UpstreamModel):
    items: list[ConfigurationState]


class Metric(UpstreamModel):
    itemid: int = Field(ge=1)
    name: str
    units: str
    value_type: int
    description: str


class MetricCatalog(UpstreamModel):
    metrics: list[Metric]


class MetricAverage(UpstreamModel):
    itemid: int = Field(ge=1)
    name: str
    units: str
    avg: float | None = None
    min: float | None = None
    max: float | None = None


class MetricAverages(UpstreamModel):
    start_time: str
    end_time: str
    metrics: list[MetricAverage]


class Point(UpstreamModel):
    timestamp: str
    value: float | int


class MetricSeries(UpstreamModel):
    metric_name: str
    data: list[Point]
    total_points: int = Field(ge=0)
