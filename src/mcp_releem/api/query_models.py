"""Query evidence models deliberately exclude SQL from serialization and repr."""

from typing import Self

from pydantic import Field, model_validator

from .models import CodeId, UpstreamModel


class QueryRecord(UpstreamModel):
    rid: str
    schema_name: str
    query_id: str
    query: str | None = Field(default=None, exclude=True, repr=False)
    calls: float | None = None
    avg_time_ms: float | None = None
    sum_time_sec: float | None = None
    sum_time_perc_total: float | None = None
    sum_time_perc_first: float | None = None


class AnalyticsPage(UpstreamModel):
    start_time: str
    end_time: str
    items: list[QueryRecord]


class Proposal(UpstreamModel):
    rid: str
    schema_name: str
    query_id: str
    title: str | None = None
    type: str | None = None
    impact_score: str | None = None
    aianalysis: bool | None = None
    timestamp: str | None = None
    explain: str | None = Field(default=None, exclude=True, repr=False)


class ProposalPage(UpstreamModel):
    items: list[Proposal]


class Optimization(UpstreamModel):
    id: int
    server_id: int
    status: CodeId
    timestamp_status: int
    schema_name: str | None = None
    query_id: str | None = None
    before_calls: int | None = None
    after_calls: int | None = None
    before_avg_time_ms: float | None = None
    after_avg_time_ms: float | None = None
    before_sum_time_ms: float | None = None
    after_sum_time_ms: float | None = None
    before_sum_time_perc_total: float | None = None
    after_sum_time_perc_total: float | None = None
    before_timestamp: int | None = None
    after_timestamp: int | None = None
    custom_query: bool | None = None
    task_id: int | None = None
    error_code: int | None = None
    error_message: str | None = Field(default=None, exclude=True, repr=False)
    query_explain: str | None = Field(default=None, exclude=True, repr=False)
    recommendations: list[Proposal] = Field(default_factory=list)

    @model_validator(mode="after")
    def proposals_match_query(self) -> Self:
        if any(
            item.schema_name != self.schema_name or item.query_id != self.query_id
            for item in self.recommendations
        ):
            raise ValueError("Linked proposals do not match the optimization query")
        return self


class OptimizationPage(UpstreamModel):
    items: list[Optimization]
