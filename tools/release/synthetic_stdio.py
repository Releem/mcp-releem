"""Installed core with an in-memory API fixture; never opens a network connection."""

import argparse
import asyncio

import httpx2
from synthetic_api import KEY_A, KEY_B, SyntheticAPI

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", choices=("101", "202"), default="101")
    key = KEY_A if parser.parse_args().account == "101" else KEY_B
    settings = Settings.from_env({"RELEEM_API_TOKEN": key})
    client = ReleemClient(settings, transport=httpx2.MockTransport(respond))
    build_server(settings, service=Diagnostics(client)).run(transport="stdio")


if __name__ == "__main__":
    main()
