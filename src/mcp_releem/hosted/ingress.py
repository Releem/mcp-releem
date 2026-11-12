"""Separate bounded unauthenticated stages from customer work admission."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from starlette.types import Receive

BODY_TIMEOUT = 3
AUTH_TIMEOUT = 5


class BoundaryError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


class Stage:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.active = 0

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        if self.active >= self.maximum:
            raise BoundaryError(429, "authentication_stage_busy")
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1


async def read_body(receive: Receive, stage: Stage, maximum: int) -> bytes | None:
    async with stage.slot():
        try:
            async with asyncio.timeout(BODY_TIMEOUT):
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return None
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > maximum:
                        raise BoundaryError(413, "request_too_large")
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        return bytes(body)
        except TimeoutError:
            raise BoundaryError(408, "request_body_deadline_exceeded") from None
