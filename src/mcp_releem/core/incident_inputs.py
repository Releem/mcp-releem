"""Bounded historical-incident inputs; never accept execution parameters."""

from datetime import datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from .diagnostic_inputs import PositiveId, instant
from .inputs import Input, Limit, ServerId


class IncidentWindow(Input):
    server_id: ServerId
    start_time: str | None = None
    end_time: str | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def aware_time(cls, value: str | None) -> str | None:
        return instant(value).isoformat() if value is not None else None

    @model_validator(mode="after")
    def bounded_window(self) -> Self:
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("Provide both window boundaries")
        if self.start_time is not None and self.end_time is not None:
            start, end = instant(self.start_time), instant(self.end_time)
            maximum = 1 if isinstance(self, CaptureInput) else 7
            if not timedelta(0) <= end - start <= timedelta(days=maximum):
                raise ValueError("Window reversed or exceeds diagnostic duration limit")
            if isinstance(self, EventInput) and (start.microsecond or end.microsecond):
                raise ValueError("Event boundaries must have whole-second precision")
        return self

    def window(self, now: datetime) -> dict[str, str]:
        end = instant(self.end_time) if self.end_time else now.replace(microsecond=0)
        start = instant(self.start_time) if self.start_time else end - timedelta(hours=1)
        return {"start_time": start.isoformat(), "end_time": end.isoformat()}


class EventInput(IncidentWindow):
    view: Literal["list", "detail"] = "list"
    event_id: Annotated[str, Field(pattern=r"^[1-9][0-9]{0,19}$")] | None = None
    limit: Limit = 20
    offset: Annotated[int, Field(ge=0, le=10000)] = 0

    @model_validator(mode="after")
    def selected_view(self) -> Self:
        if (self.view == "detail") != (self.event_id is not None):
            raise ValueError("Detail requires event_id; list forbids it")
        if self.event_id is not None and int(self.event_id) > 18446744073709551615:
            raise ValueError("Event identifier must fit UInt64")
        if self.view == "detail" and self.model_fields_set - {"view", "server_id", "event_id"}:
            raise ValueError("Detail forbids list filters")
        return self


class DeadlockInput(IncidentWindow):
    view: Literal["list", "detail"] = "list"
    deadlock_id: PositiveId | None = None
    limit: Limit = 20

    @model_validator(mode="after")
    def selected_view(self) -> Self:
        if (self.view == "detail") != (self.deadlock_id is not None):
            raise ValueError("Detail requires deadlock_id; list forbids it")
        if self.view == "detail" and self.model_fields_set - {"view", "server_id", "deadlock_id"}:
            raise ValueError("Detail forbids list filters")
        return self


class CaptureInput(IncidentWindow):
    mode: Literal["latest", "window"] = "latest"
    limit: Annotated[int, Field(ge=1, le=20)] = 5

    @model_validator(mode="after")
    def selected_mode(self) -> Self:
        if (self.mode == "window") != (self.start_time is not None):
            raise ValueError("Window mode requires boundaries; latest forbids them")
        if self.mode == "latest" and self.model_fields_set & {"start_time", "end_time"}:
            raise ValueError("Latest forbids window fields")
        return self


class TaskInput(Input):
    server_id: ServerId
    view: Literal["list", "detail"] = "list"
    task_id: PositiveId | None = None
    limit: Limit = 20
    status: Annotated[int, Field(ge=0, le=2147483647)] | None = None
    type_id: Annotated[int, Field(ge=0, le=2147483647)] | None = None

    @model_validator(mode="after")
    def selected_view(self) -> Self:
        if (self.view == "detail") != (self.task_id is not None):
            raise ValueError("Detail requires task_id; list forbids it")
        if self.view == "detail" and self.model_fields_set - {"view", "server_id", "task_id"}:
            raise ValueError("Detail forbids list filters")
        return self
