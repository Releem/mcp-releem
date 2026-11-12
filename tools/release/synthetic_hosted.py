"""Loopback-only hosted fixture with synthetic accounts; not a deployment entrypoint."""

import argparse
import logging
from typing import Any

import httpx2
import uvicorn
from synthetic_api import SyntheticAPI

from mcp_releem.hosted.app import create_hosted_app
from mcp_releem.hosted.config import HostedSettings

PUBLIC_URL = "https://mcp.example.invalid/mcp"


def fixture(api: SyntheticAPI | None = None) -> Any:
    settings = HostedSettings.from_env(
        {
            "RELEEM_MCP_PROFILE": "hosted",
            "RELEEM_MCP_PUBLIC_URL": PUBLIC_URL,
            "RELEEM_MCP_REQUESTS_PER_MINUTE": "600",
        }
    )
    return create_hosted_app(settings, transport=httpx2.MockTransport(api or SyntheticAPI()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--container",
        action="store_true",
        help="Bind inside a Docker container with loopback-only published port",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    uvicorn.run(
        fixture(),
        host="0.0.0.0" if args.container else "127.0.0.1",  # noqa: S104 -- explicit Docker fixture
        port=args.port,
        proxy_headers=False,
        access_log=False,
        log_level="warning",
    )
