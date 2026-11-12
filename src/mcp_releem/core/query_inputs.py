"""Bounded query jobs; SQL submission is not an input capability."""

from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from ..api.segments import segment
from .inputs import Input, Limit, ServerId
from .query_windows import normalize_period, query_time, validate_bounds

Text = Annotated[str, Field(min_length=1, max_length=256)]
QueryView = Literal["analytics", "proposals", "optimizations", "optimization"]


class QueryInput(Input):
    server_id: ServerId
    view: QueryView = "analytics"
    period_days: Literal[1, 7, 14, 30, 60, 90] | None = None
    period: Annotated[str, Field(max_length=16)] | None = None
    end_date: Annotated[str, Field(max_length=64)] | None = None
    start_date: Annotated[str, Field(max_length=64)] | None = None
    timezone: Literal["UTC"] = "UTC"
    sort_by: Literal["sum_time_perc_first", "calls", "avg_time_ms", "sum_time_perc_total"] = (
        "sum_time_perc_total"
    )
    order: Literal["asc", "desc"] = "desc"
    schema_name: Text | None = None
    query_filter: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    query_id: Text | None = None
    optimization_id: Annotated[int, Field(ge=1)] | None = None
    limit: Limit = 20

    @field_validator("period_days", mode="before")
    @classmethod
    def integer_period(cls, value: object) -> object:
        if value is not None and type(value) is not int:
            raise ValueError("period_days must be an integer day count")
        return value

    @field_validator("schema_name", "query_id")
    @classmethod
    def safe_segment(cls, value: str | None) -> str | None:
        if value is not None:
            segment(value)
        return value

    @field_validator("start_date", "end_date")
    @classmethod
    def explicit_start(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = query_time(value)
        return parsed.isoformat()

    @model_validator(mode="after")
    def fields_for_view(self) -> Self:
        common = {"server_id", "view"}
        allowed = {
            "analytics": {
                "period_days",
                "period",
                "end_date",
                "start_date",
                "timezone",
                "sort_by",
                "order",
                "schema_name",
                "query_filter",
                "limit",
            },
            "proposals": {"schema_name", "query_id", "limit"},
            "optimizations": {"schema_name", "limit"},
            "optimization": {"optimization_id"},
        }
        if self.model_fields_set - common - allowed[self.view]:
            raise ValueError("Arguments do not apply to the selected query view")
        if self.view == "proposals" and (self.schema_name is None or self.query_id is None):
            raise ValueError("Proposals require schema_name and query_id")
        if self.view == "optimization" and self.optimization_id is None:
            raise ValueError("Optimization detail requires optimization_id")
        if self.view == "analytics":
            normalize_period(self.period, self.period_days)
            validate_bounds(self.start_date, self.end_date)
        return self
