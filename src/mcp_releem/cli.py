"""Local stdio and authenticated shared HTTP CLI."""

import argparse
import json
import logging
import sys

from . import __version__
from .config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--check", action="store_true", help="Validate and print redacted settings; no network"
    )
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument(
        "--env-file", help="Explicit dotenv file; no interpolation or shell execution"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    try:
        if args.env_file:
            from .env_file import read_env_file

            values = read_env_file(args.env_file)
        else:
            values = None
        if args.transport == "streamable-http":
            from .hosted.config import HostedSettings

            hosted = HostedSettings.from_env(values)
            if args.check:
                print(json.dumps({"version": __version__, **hosted.redacted()}))
                return 0
            import uvicorn

            from .hosted.app import create_hosted_app

            uvicorn.run(
                create_hosted_app(hosted),
                host=hosted.bind_host,
                port=hosted.port,
                proxy_headers=False,
                access_log=False,
                log_level="warning",
            )
            return 0
        settings = Settings.from_env(values)
        if args.check:
            print(json.dumps({"version": __version__, **settings.redacted()}))
            return 0
        from .server import build_server

        build_server(settings).run(transport="stdio")
        return 0
    except (ValueError, OSError):
        print(
            "mcp-releem: invalid configuration; verify token source, API origin and local settings",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
