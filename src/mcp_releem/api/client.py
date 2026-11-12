"""Bounded asynchronous reads; credentials never leave the configured API origin."""

import asyncio
import json
import math
import ssl
from types import TracebackType
from typing import Any, Self

import httpx2
from pydantic import ValidationError

from ..config import Settings
from .operations import APIError, prepare, validate

__all__ = ["APIError", "ReleemClient"]
MAX_BODY = 5 * 1024 * 1024
ERRORS = {
    400: ("upstream_request_rejected", "Releem rejected the requested read parameters"),
    401: ("upstream_auth_failed", "Releem rejected the credential; verify it outside the model"),
    403: ("forbidden", "The configured credential cannot access this resource"),
    404: ("not_found_or_inaccessible", "Resource is absent or inaccessible; verify its parent ID"),
    422: ("invalid_source_data", "Upstream rejected arguments or could not interpret source data"),
    429: ("rate_limited", "Releem rate limit reached; wait before another request"),
}
METRIC_ERRORS = {
    "trends_not_available": "No hourly trends available; explicitly choose a raw window instead",
    "invalid_time_range": "Use an increasing metric time window",
    "time_range_too_wide": "Shorten the metric window to the documented raw/trend limit",
    "invalid_interval": "Use a positive interval ending in m, h or d",
    "aggregation_requires_interval": "Use aggregation with an interval or hourly trends",
}

QUERY_ERRORS = {
    "invalid_period": "Use a positive query period with m/h/d units",
    "invalid_start_date": "Use an explicit UTC query start at whole-second precision",
    "invalid_end_date": "Use an explicit query end after start_date",
    "invalid_time_range": "Use an increasing query window within adapter bounds",
    "invalid_timezone": "Use the supported UTC timezone",
    "invalid_sort_by": "Choose a supported query ranking field",
    "invalid_order": "Choose asc or desc query order",
    "invalid_query_filter": "Use a valid bounded query filter",
}


def reject_constant(_: str) -> float:
    raise ValueError("Nonstandard JSON number")


def finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite JSON number")
    return number


class ReleemClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: Any = None,
        allowed_server_ids: frozenset[str] | None = None,
    ) -> None:
        self.settings = settings
        self._allowed_server_ids = allowed_server_ids
        self._slots = asyncio.Semaphore(4)
        self._http = httpx2.AsyncClient(
            base_url=settings.base_url,
            headers={"Releem-Secret-Key": settings.token.get_secret_value()},
            follow_redirects=False,
            timeout=httpx2.Timeout(10, connect=3),
            transport=transport,
            verify=ssl.create_default_context(cafile=settings.ca_bundle),
            proxy=settings.proxy.get_secret_value() if settings.proxy else None,
            trust_env=False,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def read(self, operation: str, **arguments: Any) -> Any:
        spec, path, query = prepare(operation, arguments)
        scope = self._allowed_server_ids
        if scope is not None and arguments.get("server_id") is not None:
            if str(arguments["server_id"]) not in scope:
                raise APIError("forbidden", "Server is outside the authorized inventory", 403)
        try:
            async with self._slots, self._http.stream("GET", path, params=query) as response:
                if 300 <= response.status_code < 400:
                    raise APIError(
                        "redirect_refused", "Upstream redirect refused to protect credentials"
                    )
                if response.status_code != 200:
                    code, message = ERRORS.get(
                        response.status_code, ("dependency_unavailable", "Releem request failed")
                    )
                    if response.status_code in {400, 422}:
                        body = await self._body(response, 16384)
                        try:
                            error = json.loads(body).get("error", {})
                            error_code = error.get("code")
                            if (
                                response.status_code == 400
                                and isinstance(error_code, str)
                                and (
                                    operation in {"metric_name", "metric_id", "metric_averages"}
                                    and error_code in METRIC_ERRORS
                                )
                            ):
                                code, message = error_code, METRIC_ERRORS[error_code]
                            elif (
                                response.status_code == 400
                                and operation == "query_analytics"
                                and isinstance(error_code, str)
                                and error_code in QUERY_ERRORS
                            ):
                                code, message = error_code, QUERY_ERRORS[error_code]
                            elif response.status_code == 422 and error_code == "validation_error":
                                code, message = (
                                    "invalid_arguments",
                                    "Upstream request validation failed",
                                )
                        except (ValueError, AttributeError):
                            pass  # A malformed error body retains the explicit upstream failure.
                    raise APIError(code, message, response.status_code)
                body = await self._body(response, MAX_BODY)
                payload = json.loads(body, parse_constant=reject_constant, parse_float=finite_float)
                parsed = validate(spec, payload, arguments.get("server_id"))
                if scope is not None and operation in {"servers", "fleet_recommendations"}:
                    rows = parsed if isinstance(parsed, list) else parsed.items
                    for row in rows:
                        parent = row.id if operation == "servers" else row.server_id
                        if str(parent) not in scope:
                            raise APIError("forbidden", "Source exceeds authorized inventory", 403)
                child = arguments.get("recommendation_id", arguments.get("optimization_id"))
                if child is not None and parsed.id != child:
                    raise APIError(
                        "invalid_source_data", "Upstream source child does not match request"
                    )
                if operation in {"query_analytics", "query_proposals", "optimizations"}:
                    for record in parsed.items:
                        for key in ("schema_name", "query_id"):
                            target = arguments.get(key)
                            if target is not None and getattr(record, key, None) != target:
                                raise APIError(
                                    "invalid_source_data",
                                    "Upstream source query scope does not match request",
                                )
                return parsed
        except httpx2.TimeoutException:
            raise APIError("timeout", "Releem read timed out; narrow the request") from None
        except httpx2.HTTPError:
            raise APIError(
                "dependency_unavailable", "Unable to read Releem; check CA/proxy/network"
            ) from None
        except (ValueError, ValidationError, RecursionError):
            raise APIError(
                "invalid_source_data", "Upstream source does not match the expected shape"
            ) from None

    async def _body(self, response: httpx2.Response, maximum: int) -> bytes:
        body = bytearray()
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > maximum:
                raise APIError("response_too_large", "Narrow the upstream request")
            body.extend(chunk)
        return bytes(body)
