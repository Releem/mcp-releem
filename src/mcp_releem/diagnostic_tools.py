"""MCP presentation for configuration and metric read jobs."""

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
    async def configurations(
        server_id: str,
        view: Literal["history", "latest", "detail"] = "history",
        configuration_status_id: int | None = None,
        limit: int = 20,
    ) -> CallToolResult:
        """Read configuration states/history; detail uses state ID, values are privacy-minimized."""
        arguments: dict[str, Any] = {"view": view}
        if view == "detail":
            arguments["configuration_status_id"] = configuration_status_id
        elif view == "history":
            arguments["limit"] = limit
        return present(await active().configurations(server_id, **arguments))

    @server.tool(annotations=annotations)
    async def metrics(
        server_id: str,
        view: Literal["catalog", "series", "compare"] = "catalog",
        limit: int = 20,
        metric_name: str | None = None,
        itemid: int | None = None,
        metric_names: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        baseline_start_time: str | None = None,
        baseline_end_time: str | None = None,
        interval: str | None = None,
        aggregation: str | None = None,
        use_trends: bool = False,
    ) -> CallToolResult:
        """List metrics, read at most 500 samples, or compare up to four hourly trend summaries."""
        arguments: dict[str, Any] = {"view": view}
        if view == "catalog":
            arguments["limit"] = limit
        else:
            arguments.update(start_time=start_time, end_time=end_time)
            if view == "series":
                arguments.update(
                    metric_name=metric_name,
                    itemid=itemid,
                    interval=interval,
                    aggregation=aggregation,
                    use_trends=use_trends,
                )
            else:
                arguments.update(
                    metric_names=metric_names,
                    baseline_start_time=baseline_start_time,
                    baseline_end_time=baseline_end_time,
                )
        return present(await active().metrics(server_id, **arguments))
