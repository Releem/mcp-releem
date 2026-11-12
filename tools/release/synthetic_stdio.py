"""Installed core with an in-memory API fixture; never opens a network connection."""

import asyncio

import httpx2
from synthetic_api import KEY_A, SyntheticAPI

from mcp_releem.api.client import ReleemClient
from mcp_releem.config import Settings
from mcp_releem.core.diagnostics import Diagnostics
from mcp_releem.server import build_server

api = SyntheticAPI()


async def respond(request: httpx2.Request) -> httpx2.Response:
    if request.url.params.get("hostname") == "cancel":
        await asyncio.sleep(30)
    return await api(request)


def main() -> None:
    settings = Settings.from_env({"RELEEM_API_TOKEN": KEY_A})
    client = ReleemClient(settings, transport=httpx2.MockTransport(respond))
    build_server(settings, service=Diagnostics(client)).run(transport="stdio")


if __name__ == "__main__":
    main()
