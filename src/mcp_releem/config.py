"""Administrator-controlled settings. Never load credentials from tool arguments."""

import ipaddress
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr

DEFAULT_URL = "https://api2.releem.com"


@dataclass(frozen=True)
class Settings:
    token: SecretStr
    base_url: str = DEFAULT_URL
    ca_bundle: str | None = None
    proxy: SecretStr | None = None
    max_output_bytes: int = 24576
    sensitive_details: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        values = os.environ if env is None else env
        allowed = {
            "RELEEM_MCP_READ_ONLY",
            "RELEEM_MCP_PROFILE",
            "RELEEM_MCP_MAX_OUTPUT_BYTES",
            "RELEEM_MCP_SENSITIVE_DETAILS",
        }
        if any(k.startswith("RELEEM_MCP_") and k not in allowed for k in values):
            raise ValueError("Unknown RELEEM_MCP setting")
        if values.get("RELEEM_MCP_PROFILE", "local") != "local":
            raise ValueError("Only the local profile is implemented")
        if values.get("RELEEM_MCP_READ_ONLY", "true").lower() != "true":
            raise ValueError("This release supports read-only diagnostics only")
        sensitive = values.get("RELEEM_MCP_SENSITIVE_DETAILS", "false").lower()
        if sensitive not in {"true", "false"}:
            raise ValueError("Sensitive details must be true or false")
        token, token_file = values.get("RELEEM_API_TOKEN"), values.get("RELEEM_API_TOKEN_FILE")
        secret_key = values.get("RELEEM_SECRET_KEY")
        if sum(bool(value) for value in (token, token_file, secret_key)) != 1:
            raise ValueError("Configure exactly one token source: token, secret key or token file")
        token = token or secret_key
        if token_file:
            try:
                with Path(token_file).open("rb") as source:
                    token = source.read(65537).decode().strip()
            except (OSError, UnicodeError):
                raise ValueError("Cannot read token file; verify path and permissions") from None
        if not token or len(token) > 65536 or any(c.isspace() for c in token):
            raise ValueError("The token must be nonempty and contain no whitespace")
        url = values.get("RELEEM_API_BASE_URL", DEFAULT_URL)
        parsed = urlsplit(url)
        try:
            port = parsed.port
        except ValueError:
            raise ValueError("Invalid API URL port") from None
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
            or port == 0
        ):
            raise ValueError("API URL must be an HTTPS origin without credentials, path or query")
        host = parsed.hostname
        private = host == "localhost" or host.endswith((".localhost", ".local"))
        try:
            private = private or not ipaddress.ip_address(host).is_global
        except ValueError:
            pass  # Hostname resolution is performed by the HTTP stack, not settings parsing.
        if private and values.get("RELEEM_API_ALLOW_PRIVATE", "false").lower() != "true":
            raise ValueError(
                "Private API origins require administrator RELEEM_API_ALLOW_PRIVATE=true"
            )
        try:
            budget = int(values.get("RELEEM_MCP_MAX_OUTPUT_BYTES", "24576"))
        except ValueError:
            raise ValueError("Output budget must be an integer") from None
        if not 2048 <= budget <= 65536:
            raise ValueError("Output budget must be between 2048 and 65536 bytes")
        return cls(
            token=SecretStr(token),
            base_url=url.rstrip("/"),
            ca_bundle=values.get("RELEEM_API_CA_BUNDLE"),
            proxy=SecretStr(values["HTTPS_PROXY"]) if values.get("HTTPS_PROXY") else None,
            max_output_bytes=budget,
            sensitive_details=sensitive == "true",
        )

    def redacted(self) -> dict[str, object]:
        return {
            "profile": "local",
            "transport": "stdio",
            "read_only": True,
            "base_url": self.base_url,
            "token_configured": True,
            "custom_ca": bool(self.ca_bundle),
            "proxy_configured": self.proxy is not None,
            "max_output_bytes": self.max_output_bytes,
            "sensitive_details": self.sensitive_details,
        }
