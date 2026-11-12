"""Encode a single upstream identifier without permitting path traversal."""

from urllib.parse import quote


def segment(value: str) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 256
        or value in {".", ".."}
        or any(c in value for c in ("/", "\\"))
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise ValueError("Identifier is not a safe path segment")
    return quote(value, safe="")
