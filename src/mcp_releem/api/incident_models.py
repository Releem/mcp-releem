"""Allowlisted stored-incident API records; private payloads never auto-propagate."""

from typing import Any

from pydantic import Field

from .models import UpstreamModel


class EventSummary(UpstreamModel):
    server_id: int
    event_id: str = Field(pattern=r"^[1-9][0-9]{0,19}$")
    timestamp: str
    name: str
    event_type_id: int
    event_type_name: str | None = None
    event_severity: int | None = None


class EventPage(UpstreamModel):
    items: list[EventSummary]


class EventDetail(UpstreamModel):
    event_id: int
    timestamp: str
    event_body: Any


class Deadlock(UpstreamModel):
    id: int
    server_id: int
    timestamp: str
    database: str
    table: str
    deadlock_type: int | None = None
    max_active_time: int | None = None


class DeadlockDetail(Deadlock):
    raw: str
    txn1: str | None = None
    txn2: str | None = None


class DeadlockPage(UpstreamModel):
    items: list[Deadlock]


class Task(UpstreamModel):
    id: int
    server_id: int
    type_id: int | None = None
    status: int
    exit_code: int | None = None
    status_time: str | None = None


class TaskDetail(Task):
    output: str | None = None
    error: str | None = None
    report_time: str | None = None


class TaskPage(UpstreamModel):
    items: list[Task]


class Capture(UpstreamModel):
    server_id: int
    timestamp: str
    processlist: Any


class CapturePage(UpstreamModel):
    items: list[Capture]
