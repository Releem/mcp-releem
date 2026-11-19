"""Completed schema-check snapshots; payload text remains private."""

from pydantic import Field

from .models import CodeValue, UpstreamModel


class SchemaCheck(UpstreamModel):
    server_id: int
    is_check: int
    type: str | CodeValue
    data: str
    count_checks: int = Field(ge=0)

    @property
    def type_id(self) -> int | str:
        return self.type.id if isinstance(self.type, CodeValue) else self.type


class SchemaSnapshot(UpstreamModel):
    server_id: int | None = None
    timestamp: str | None = None
    items: list[SchemaCheck]
