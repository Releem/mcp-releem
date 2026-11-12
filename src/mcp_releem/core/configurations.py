"""Read configuration states without passing arbitrary configuration values to models."""

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ..api.client import APIError
from .diagnostic_inputs import ConfigurationInput
from .results import Coverage, DiagnosticResult

if TYPE_CHECKING:
    from .diagnostics import Diagnostics


class ConfigurationDiagnostics:
    def __init__(self, context: "Diagnostics") -> None:
        self.context = context

    async def read(self, server_id: str, **arguments: Any) -> DiagnosticResult:
        try:
            request = ConfigurationInput(server_id=server_id, **arguments)
            operation = "configuration" if request.view == "detail" else "configurations"
            params: dict[str, Any] = {"server_id": server_id}
            if request.view == "detail":
                params["configuration_status_id"] = request.configuration_status_id
            elif request.view == "latest":
                params["latest"] = True
            else:
                params["limit"] = request.limit
            response = await self.context.client.read(operation, **params)
            result = DiagnosticResult(
                scope={"server_id": server_id}, evidence=[self.context.evidence(operation)]
            )
            if request.view == "detail":
                if response.configuration_status_id != request.configuration_status_id:
                    raise APIError(
                        "invalid_source_data", "Configuration state does not match target"
                    )
                row = response.model_dump(exclude={"variables"})
                row["variables_count"] = len(response.variables)
                result.data = {"configuration": row, "period_bounds": "[start,end)"}
                result.coverage = Coverage(requested=1, fetched=1, returned=1, complete=False)
                result.warn(
                    "configuration_values_omitted",
                    "Variable values, source text and untyped metrics omitted for privacy",
                )
                result.coverage.truncated_fields = ["configuration_values", "evaluation_metrics"]
                result.status = "partial"
                if response.history is None:
                    result.warn(
                        "analysis_absent", "No configuration analysis snapshot is available"
                    )
            else:
                cap = 1 if request.view == "latest" else request.limit
                rows = response.items[:cap]
                result.data = {"items": [row.model_dump() for row in rows]}
                result.coverage = Coverage(
                    requested=cap,
                    fetched=len(response.items),
                    returned=len(rows),
                    omitted=max(0, len(response.items) - len(rows)),
                    complete=False,
                )
                result.status = "partial" if rows else "no_data"
                result.warn(
                    "retrieval_limited",
                    "List is bounded and has no total/cursor; omitted history cannot be ruled out",
                )
            result.warn(
                "configuration_state_only",
                "State records do not establish effective database settings or causation",
            )
            return self.context.finish(result)
        except (APIError, ValidationError) as exc:
            return self.context.error(exc)
