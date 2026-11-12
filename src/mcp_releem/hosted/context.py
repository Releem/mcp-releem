"""Task-local diagnostics: never shared across requests."""

from contextvars import ContextVar

from ..core.diagnostics import Diagnostics

service_context: ContextVar[Diagnostics | None] = ContextVar("releem_diagnostics", default=None)


def current_service() -> Diagnostics:
    service = service_context.get()
    if service is None:
        raise RuntimeError("Authenticated request context is missing")
    return service
