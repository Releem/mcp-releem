"""Defense in depth after field allowlisting; never claim SQL is anonymized."""

import re
from typing import Any

_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SECRET = re.compile(r"(?i)(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*[^\s,;]+")
_BEARER = re.compile(r"(?i)bearer\s+\S+")
_SQL = re.compile(
    r"(?i)\b(?:select|insert|update|delete|alter|create|drop|grant)\b.+\b(?:from|table|index|into|set|on)\b"
)


class Redactor:
    def __init__(self, secret: str) -> None:
        self.secret = secret
        self.changed = 0
        self.clipped = False

    def clean(self, value: Any) -> Any:
        if isinstance(value, str):
            text = value.replace(self.secret, "[redacted]")
            if _SQL.search(text):
                text = "[SQL-bearing text omitted]"
            for pattern in (_EMAIL, _IP, _SECRET, _BEARER):
                text = pattern.sub("[redacted]", text)
            if len(text) > 512:
                text = text[:512] + " [text truncated]"
                self.clipped = True
            self.changed += int(text != value)
            return text
        if isinstance(value, list):
            return [self.clean(item) for item in value]
        if isinstance(value, dict):
            return {self.clean(key): self.clean(item) for key, item in value.items()}
        return value
