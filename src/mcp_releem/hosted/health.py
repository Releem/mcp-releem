"""Local liveness probe, with no customer key or upstream request."""

import json
import sys
from http.client import HTTPConnection, HTTPException
from urllib.parse import urlsplit

from .config import HostedSettings


def check(settings: HostedSettings) -> int:
    connection = HTTPConnection("127.0.0.1", settings.port, timeout=2)
    try:
        connection.request(
            "GET",
            "/healthz",
            headers={
                "Host": urlsplit(settings.public_url).netloc,
            },
        )
        response = connection.getresponse()
        body = response.read(129)
        if response.status != 200 or len(body) > 128:
            return 1
        return 0 if json.loads(body) == {"status": "alive"} else 1
    except (OSError, HTTPException, ValueError, UnicodeError):
        return 1
    finally:
        connection.close()


def main() -> int:
    try:
        result = check(HostedSettings.from_env())
    except (ValueError, OSError):
        result = 1
    if result:
        print("mcp-releem: local liveness check failed", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
