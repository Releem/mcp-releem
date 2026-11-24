"""Stable diagnostic result contract and conservative output budgeting."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Warning(BaseModel):
    code: str
    message: str


class Failure(BaseModel):
    code: str
    message: str
    retryable: bool = False
    upstream_status: int | None = None
    next_action: str = "Check configuration, target identifiers and upstream availability"


class Evidence(BaseModel):
    operation_id: str
    fetched_at: str
    observed_at: str | None = None


class Coverage(BaseModel):
    requested: int = 0
    fetched: int = 0
    returned: int = 0
    omitted: int = 0
    complete: bool = True
    upstream_total: int | None = None
    next_offset: int | None = None
    snapshot_consistent: bool | None = None
    truncated_fields: list[str] = Field(default_factory=list)


class DiagnosticResult(BaseModel):
    schema_version: Literal["1"] = "1"
    status: Literal["ok", "partial", "no_data", "error"] = "ok"
    data: dict[str, Any] | None = None
    scope: dict[str, str] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    coverage: Coverage = Field(default_factory=Coverage)
    warnings: list[Warning] = Field(default_factory=list)
    redaction: dict[str, Any] = Field(default_factory=lambda: {"policy_version": "minimal-v1"})
    error: Failure | None = None

    def warn(self, code: str, message: str) -> None:
        if not any(item.code == code for item in self.warnings):
            self.warnings.append(Warning(code=code, message=message))


def fit(result: DiagnosticResult, budget: int) -> DiagnosticResult:
    """Clip rows first; metadata/warnings are never silently removed."""
    data = result.data or {}
    while len(result.model_dump_json().encode()) > budget:
        items = data.get("items")
        if isinstance(items, list) and items:
            items.pop()
            result.coverage.omitted += 1
            result.coverage.returned = len(items)
            result.coverage.complete = False
            result.coverage.next_offset = None
            if "items" not in result.coverage.truncated_fields:
                result.coverage.truncated_fields.append("items")
            result.warn("output_truncated", "Rows omitted; narrow filters or request one detail")
            if result.status == "ok":
                result.status = "partial"
            continue
        if _trim_configuration_row(data, result):
            continue
        return DiagnosticResult(
            status="error",
            scope=result.scope,
            coverage=Coverage(complete=False),
            error=Failure(
                code="result_too_large", message="Narrow the requested sections or filters"
            ),
            warnings=[
                Warning(code="output_not_returned", message="Result exceeded the output budget")
            ],
        )
    return result


def _trim_configuration_row(data: dict[str, Any], result: DiagnosticResult) -> bool:
    changes = data.get("configuration", {}).get("variable_changes", {})
    candidates = [(name, comparison) for name, comparison in changes.items() if comparison["items"]]
    if not candidates:
        return False
    name, comparison = max(candidates, key=lambda entry: len(entry[1]["items"]))
    comparison["items"].pop()
    comparison["omitted"] += 1
    comparison["status"] = "partial"
    path = f"configuration.variable_changes.{name}.items"
    if path not in result.coverage.truncated_fields:
        result.coverage.truncated_fields.append(path)
    result.coverage.complete = False
    result.status = "partial"
    result.warn("output_truncated", "Configuration change rows exceeded the output budget")
    return True
