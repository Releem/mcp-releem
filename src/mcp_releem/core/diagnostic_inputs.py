"""Strict mode-specific diagnostic requests and explicit UTC windows."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from ..api.segments import segment
from .inputs import Input, Limit, ServerId

PositiveId = Annotated[int, Field(ge=1, le=99999999999999999999)]


def instant(value: str, *, source_utc: bool = False) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        if not source_utc:
            raise ValueError("Time must include an explicit timezone")
        parsed = parsed.replace(tzinfo=UTC)
    try:
        return parsed.astimezone(UTC)
    except OverflowError:
        raise ValueError("UTC time is outside the supported datetime range") from None


class ConfigurationInput(Input):
    server_id: ServerId
    view: Literal["history", "latest", "detail", "applied_changes"] = "history"
    configuration_status_id: PositiveId | None = None
    limit: Limit = 20

    @property
    def scan_limit(self) -> int:
        return self.limit if "limit" in self.model_fields_set else 10

    @model_validator(mode="after")
    def fields_for_view(self) -> Self:
        allowed = {"server_id", "view"} | (
            {"configuration_status_id"}
            if self.view == "detail"
            else {"limit"}
            if self.view in {"history", "applied_changes"}
            else set()
        )
        if self.model_fields_set - allowed:
            raise ValueError("Arguments do not apply to the configuration view")
        if self.view == "detail" and self.configuration_status_id is None:
            raise ValueError("Detail requires a configuration state ID")
        if self.view == "applied_changes" and self.scan_limit > 20:
            raise ValueError("Applied changes scans at most 20 configuration states")
        return self


class MetricInput(Input):
    server_id: ServerId
    view: Literal["catalog", "series", "compare"] = "catalog"
    limit: Limit = 20
    metric_name: str | None = None
    itemid: PositiveId | None = None
    metric_names: Annotated[list[str], Field(min_length=1, max_length=4)] | None = None
    start_time: str | None = None
    end_time: str | None = None
    baseline_start_time: str | None = None
    baseline_end_time: str | None = None
    interval: Annotated[str, Field(pattern=r"^[1-9][0-9]{0,6}[mhd]$")] | None = None
    aggregation: Literal["avg", "sum", "min", "max"] | None = None
    use_trends: bool = False

    @field_validator("metric_name")
    @classmethod
    def safe_name(cls, value: str | None) -> str | None:
        if value is not None:
            segment(value)
        return value

    @field_validator("metric_names")
    @classmethod
    def safe_names(cls, value: list[str] | None) -> list[str] | None:
        if value is not None:
            for name in value:
                segment(name)
            if len(set(value)) != len(value):
                raise ValueError("Duplicate metric names")
        return value

    @field_validator("start_time", "end_time", "baseline_start_time", "baseline_end_time")
    @classmethod
    def aware_time(cls, value: str | None) -> str | None:
        return instant(value).isoformat() if value is not None else None

    @model_validator(mode="after")
    def fields_for_view(self) -> Self:
        common = {"server_id", "view"}
        windows = {"start_time", "end_time"}
        allowed = {
            "catalog": {"limit"},
            "series": windows | {"metric_name", "itemid", "interval", "aggregation", "use_trends"},
            "compare": windows | {"metric_names", "baseline_start_time", "baseline_end_time"},
        }
        if self.model_fields_set - common - allowed[self.view]:
            raise ValueError("Arguments do not apply to the metric view")
        if self.view == "series":
            if (self.metric_name is None) == (self.itemid is None):
                raise ValueError("Select exactly one metric name or itemid")
            if self.aggregation and not (self.interval or self.use_trends):
                raise ValueError("Aggregation requires interval or trends")
        if self.view == "compare" and not self.metric_names:
            raise ValueError("Comparison requires one to four metric names")
        for start, end in [
            (self.start_time, self.end_time),
            (self.baseline_start_time, self.baseline_end_time),
        ]:
            if (start is None) != (end is None):
                raise ValueError("Both window boundaries are required")
            if start is not None and end is not None:
                span = instant(end) - instant(start)
                maximum = 366 if self.view == "compare" or self.use_trends else 31
                if not timedelta(0) < span <= timedelta(days=maximum):
                    raise ValueError("Window is reversed or exceeds the supported duration")
                if self.view == "compare" and self.baseline_start_time is None:
                    try:
                        instant(start) - span
                    except OverflowError:
                        raise ValueError("Previous comparison window is out of range") from None
        return self

    def window(self, now: datetime) -> tuple[datetime, datetime]:
        end = instant(self.end_time) if self.end_time else now.astimezone(UTC)
        start = instant(self.start_time) if self.start_time else end - timedelta(hours=1)
        return start, end
