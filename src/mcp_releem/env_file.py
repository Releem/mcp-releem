"""Explicit dotenv parsing without interpolation, execution or secret diagnostics."""

import os
from collections.abc import Mapping
from io import StringIO
from pathlib import Path

from dotenv.parser import parse_stream


def read_env_file(path: str, env: Mapping[str, str] | None = None) -> dict[str, str]:
    try:
        with Path(path).open("rb") as source:
            body = source.read(65537)
        if len(body) > 65536:
            raise ValueError("Environment file exceeds the size limit")
        bindings = list(parse_stream(StringIO(body.decode("utf-8"))))
    except (OSError, UnicodeError):
        raise ValueError("Cannot read environment file; verify its path and permissions") from None
    if any(binding.error for binding in bindings):
        raise ValueError("Environment file contains invalid syntax")
    values = {
        binding.key: binding.value
        for binding in bindings
        if binding.key is not None and binding.value is not None
    }
    return {**values, **(os.environ if env is None else env)}
