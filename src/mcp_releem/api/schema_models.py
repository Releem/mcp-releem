"""Completed schema-check snapshots; payload text remains private."""

from pydantic import Field

from .models import UpstreamModel


class SchemaCheck(UpstreamModel):
    server_id: int
    is_check: int
    type: str
    data: str
    count_checks: int = Field(ge=0)


class SchemaSnapshot(UpstreamModel):
    server_id: int | None = None
    timestamp: str | None = None
    items: list[SchemaCheck]
