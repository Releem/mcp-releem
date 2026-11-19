"""Selected upstream shapes; unknown fields never become public output automatically."""

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class UpstreamModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore", allow_inf_nan=False)


class CodeValue(UpstreamModel):
    id: int | str
    name: str | None = None


def _code_id(value: object) -> int | str:
    if type(value) is int:
        return value
    return CodeValue.model_validate(value).id


# These fields used scalar integers before the production API introduced CodeValue.
CodeId = Annotated[int | str, BeforeValidator(_code_id)]


class Server(UpstreamModel):
    id: str = Field(pattern=r"^[1-9][0-9]*$")
    server_name: str | None = None
    status: str | None = None
    mysql_version: str | None = None
    agent_version: str | None = None
    instance_type: str | CodeValue | None = None
    releem_score: float | None = None


class Details(UpstreamModel):
    id: str | None = None
    health_checks: dict[str, Any] | None = None
    security_checks: dict[str, Any] | None = None
    security_checks_unknown: list[Any] = Field(default_factory=list)
    security_checks_decode_error: str | None = None


class Check(UpstreamModel):
    failed: bool | None = None
    description: str | None = None
    value: Any = None
    title: str | None = None
    short_description: str | None = None
    learn_more_url: str | None = None
    severity: str | None = None
    group: str | None = None


class Report(UpstreamModel):
    timestamp: int | None = None
    checks: dict[str, Check] = Field(default_factory=dict)
    failed_checks: list[Any] = Field(default_factory=list)
    security_checks_score: float | None = None


class Recommendation(UpstreamModel):
    id: int
    server_id: str
    source_type: str
    source_id: str
    source_subtype: str
    title: str
    summary: str
    status: str
    source_record_id: str | None = None
    type_id: int | None = None
    category_id: int | None = None
    priority_score: float | None = None
    priority_label: str | None = None
    why_important_now: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RecommendationPage(UpstreamModel):
    items: list[Recommendation]
    total: int = Field(ge=0)
    limit: int | None = None
    offset: int = 0
