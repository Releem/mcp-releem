"""Typed job inputs, independent of the MCP transport."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

ServerId = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,19}$")]
Limit = Annotated[int, Field(ge=1, le=100)]
Section = Literal["summary", "health", "security", "schema"]
CheckType = Literal[
    "missing_primary_key",
    "unused_index",
    "duplicate_index",
    "auto_increment",
    "collation",
    "character_set",
    "table_engine",
    "table_fragmentation",
]


def default_sections() -> list[Section]:
    return ["summary", "health", "security"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class InventoryInput(Input):
    hostname: list[Annotated[str, Field(min_length=1, max_length=253)]] | None = Field(
        default=None,
        min_length=1,
        max_length=8,
    )
    limit: Limit = 20


class FindingsInput(Input):
    server_id: ServerId
    sections: list[Section] = Field(
        default_factory=default_sections,
        min_length=1,
        max_length=4,
    )
    schema_name: Annotated[str, Field(min_length=1, max_length=256)] | None = None
    check_type: CheckType | None = None
    schema_limit: Limit = 20

    @model_validator(mode="after")
    def schema_filters(self) -> Self:
        if len(set(self.sections)) != len(self.sections):
            raise ValueError("Sections must be unique")
        if "schema" not in self.sections and self.model_fields_set & {
            "schema_name",
            "check_type",
            "schema_limit",
        }:
            raise ValueError("Schema filters require the schema section")
        return self


class RecommendationInput(Input):
    server_id: ServerId | None = None
    scope: Literal["server", "fleet"] = "server"
    view: Literal["list", "detail"] = "list"
    recommendation_id: Annotated[int, Field(ge=1)] | None = None
    type_id: Annotated[int, Field(ge=1, le=5)] | None = None
    category_id: Annotated[int, Field(ge=1, le=4)] | None = None
    source_type: (
        Literal["configuration", "query_optimization", "schema_check", "security_check", "deadlock"]
        | None
    ) = None
    status: Literal["new", "dismissed", "done", "outdated"] | None = None
    score_min: float | None = None
    score_max: float | None = None
    sort: Literal["priority_score_desc", "created_at_desc"] = "priority_score_desc"
    limit: Limit = 20
    offset: Annotated[int, Field(ge=0, le=10000)] = 0
    history_limit: Annotated[int, Field(ge=1, le=20)] = 10

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.scope == "server") != (self.server_id is not None):
            raise ValueError("Server scope requires server_id; explicit fleet scope forbids it")
        if self.scope == "fleet" and self.view != "list":
            raise ValueError("Fleet supports list reads only")
        if self.view != "detail" and "history_limit" in self.model_fields_set:
            raise ValueError("History limit applies only to detail")
        if (self.view == "detail") != (self.recommendation_id is not None):
            raise ValueError("detail requires recommendation_id; list forbids it")
        if self.view == "detail" and self.model_fields_set - {
            "server_id",
            "view",
            "recommendation_id",
            "scope",
            "history_limit",
        }:
            raise ValueError("Detail does not accept list filters")
        if self.score_min is not None and self.score_max is not None:
            if self.score_min > self.score_max:
                raise ValueError("score_min must not exceed score_max")
        return self
