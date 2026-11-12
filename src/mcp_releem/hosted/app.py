"""API-key authentication outside the stateless MCP transport."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit

from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from ..api.client import APIError, ReleemClient
from ..core.diagnostics import Diagnostics
from ..server import build_server
from .config import HostedSettings
from .context import current_service, service_context
from .ingress import AUTH_TIMEOUT, BoundaryError, Stage, read_body
from .limits import Limits

MAX_BODY = 262144


class HostedApp:
    def __init__(self, settings: HostedSettings, *, transport: Any = None) -> None:
        self.settings = settings
        self.transport = transport
        self.limits = Limits(settings)
        self.body_stage = Stage(32)
        self.auth_stage = Stage(8)
        # The outer boundary validates Host and Origin before authentication for every request.
        self.inner = build_server(service_provider=current_service).streamable_http_app(
            stateless_http=True,
            json_response=True,
            max_request_body_size=MAX_BODY,
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        public = urlsplit(settings.public_url)
        self.host = public.netloc.lower()
        self.origin = f"https://{self.host}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.inner(scope, receive, send)
            return

        async def reject(status: int, code: str) -> None:
            headers = {"Cache-Control": "no-store"}
            if status == 401:
                headers["WWW-Authenticate"] = 'Bearer realm="releem-api-key"'
            if status == 429:
                headers["Retry-After"] = "60"
            await JSONResponse({"error": code}, status_code=status, headers=headers)(
                scope, receive, send
            )

        headers: dict[bytes, list[bytes]] = {}
        for name, value in scope.get("headers", []):
            headers.setdefault(name.lower(), []).append(value)
        if headers.get(b"host") != [self.host.encode()]:
            await reject(400, "invalid_host")
            return
        if b"origin" in headers and headers[b"origin"] != [self.origin.encode()]:
            await reject(403, "origin_forbidden")
            return
        if scope["path"] == "/healthz" and scope["method"] in {"GET", "HEAD"}:
            await JSONResponse({"status": "alive"})(scope, receive, send)
            return
        if scope["path"] != "/mcp" or scope.get("query_string"):
            await reject(404, "unknown_endpoint")
            return
        if b"mcp-session-id" in headers:
            await reject(400, "sessions_unsupported")
            return
        lengths = headers.get(b"content-length", [])
        if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
            await reject(400, "invalid_content_length")
            return
        if lengths and (len(lengths[0]) > 7 or int(lengths[0]) > MAX_BODY):
            await reject(413, "request_too_large")
            return
        authorization = headers.get(b"authorization", [])
        match = (
            re.fullmatch(rb"(?i:Bearer) ([A-Za-z0-9._~+/-]{1,4096}=*)", authorization[0])
            if len(authorization) == 1 and len(authorization[0]) <= 4103
            else None
        )
        if match is None or len(match[1]) > 4096:
            await reject(401, "api_key_required")
            return
        key = match[1].decode("ascii")
        fingerprint: str | None = None
        started = False

        async def safe_send(message: Any) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message = {
                    **message,
                    "headers": [*message.get("headers", []), (b"cache-control", b"no-store")],
                }
            await send(message)

        try:
            async with asyncio.timeout(30):
                body = await read_body(receive, self.body_stage, MAX_BODY)
                if body is None:
                    return
                try:
                    payload = json.loads(body)
                except (ValueError, UnicodeError, RecursionError):
                    raise BoundaryError(400, "invalid_json") from None
                if (
                    not isinstance(payload, dict)
                    or not isinstance(payload.get("method"), str)
                    or payload.get("method")
                    not in {
                        "initialize",
                        "ping",
                        "notifications/initialized",
                        "notifications/cancelled",
                        "tools/list",
                        "tools/call",
                        "prompts/list",
                        "prompts/get",
                        "resources/list",
                        "resources/templates/list",
                        "resources/read",
                    }
                ):
                    raise BoundaryError(400, "unsupported_protocol_method")
                delivered = False

                async def buffered_receive() -> Any:
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body)}
                    return await receive()

                settings = self.settings.for_key(key)
                async with self.auth_stage.slot(), asyncio.timeout(AUTH_TIMEOUT):
                    async with ReleemClient(settings, transport=self.transport) as validator:
                        inventory = await validator.read("servers")
                        allowed = frozenset(str(row.id) for row in inventory)
                fingerprint = self.limits.acquire(key)
                if fingerprint is None:
                    raise BoundaryError(429, "request_limit_reached")
                async with ReleemClient(
                    settings, transport=self.transport, allowed_server_ids=allowed
                ) as client:
                    token = service_context.set(Diagnostics(client))
                    try:
                        clean_scope = {
                            **scope,
                            "headers": [
                                (k, v)
                                for k, v in scope["headers"]
                                if k.lower()
                                not in {b"authorization", b"cookie", b"releem-secret-key"}
                            ],
                        }
                        await self.inner(clean_scope, buffered_receive, safe_send)
                    finally:
                        service_context.reset(token)
        except BoundaryError as error:
            if not started:
                await reject(error.status, error.code)
        except APIError as error:
            if not started:
                status = error.status if error.status in {401, 403, 429} else 503
                await reject(
                    status, "upstream_auth_failed" if status == 401 else "upstream_unavailable"
                )
        except TimeoutError:
            if not started:
                await reject(504, "request_deadline_exceeded")
        except Exception:
            # Never expose framework exceptions or caller headers in production logs.
            if not started:
                await reject(500, "internal_error")
            else:
                raise RuntimeError("Hosted response failed after headers") from None
        finally:
            if fingerprint is not None:
                self.limits.release(fingerprint)


def create_hosted_app(settings: HostedSettings, *, transport: Any = None) -> HostedApp:
    return HostedApp(settings, transport=transport)
