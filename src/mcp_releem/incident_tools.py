"""MCP adapters for stored incident evidence; no creation or execution tools."""

from collections.abc import Callable
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult, ToolAnnotations

from .core.diagnostics import Diagnostics
from .core.results import DiagnosticResult


def register(
    server: MCPServer[Any],
    active: Callable[[], Diagnostics],
    present: Callable[[DiagnosticResult], CallToolResult],
    annotations: ToolAnnotations,
) -> None:
    @server.tool(annotations=annotations)
    async def events(
        server_id: str,
        view: Literal["list", "detail"] = "list",
        event_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> CallToolResult:
        """Read inclusive incident timeline pages or minimized event detail; pages can shift."""
        args: dict[str, Any] = {"view": view}
        if view == "detail":
            args["event_id"] = event_id
        else:
            args.update(start_time=start_time, end_time=end_time, limit=limit, offset=offset)
        return present(await active().events(server_id, **args))

    @server.tool(annotations=annotations)
    async def deadlocks(
        server_id: str,
        view: Literal["list", "detail"] = "list",
        deadlock_id: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 20,
    ) -> CallToolResult:
        """Read stored deadlocks; duration is seconds, dumps and transaction SQL are omitted."""
        args: dict[str, Any] = {"view": view}
        if view == "detail":
            args["deadlock_id"] = deadlock_id
        else:
            args.update(start_time=start_time, end_time=end_time, limit=limit)
        return present(await active().deadlocks(server_id, **args))

    @server.tool(annotations=annotations)
    async def task_outcomes(
        server_id: str,
        view: Literal["list", "detail"] = "list",
        task_id: int | None = None,
        status: int | None = None,
        type_id: int | None = None,
        limit: int = 20,
    ) -> CallToolResult:
        """Read agent task states/report availability; never queue or retry agent work."""
        args: dict[str, Any] = {"view": view}
        if view == "detail":
            args["task_id"] = task_id
        else:
            args.update(status=status, type_id=type_id, limit=limit)
        return present(await active().task_outcomes(server_id, **args))

    @server.tool(annotations=annotations)
    async def captured_sessions(
        server_id: str,
        mode: Literal["latest", "window"] = "latest",
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 5,
    ) -> CallToolResult:
        """Read historical capture aggregates; operator permission required, never live sessions."""
        args: dict[str, Any] = {"mode": mode, "limit": limit}
        if mode == "window":
            args.update(start_time=start_time, end_time=end_time)
        return present(await active().captured_sessions(server_id, **args))
