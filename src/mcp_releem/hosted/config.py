"""Hosted configuration contains no customer credential."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from pydantic import SecretStr

from ..config import Settings


@dataclass(frozen=True)
class HostedSettings:
    public_url: str
    base_url: str
    ca_bundle: str | None
    proxy: SecretStr | None
    max_output_bytes: int
    sensitive_details: bool
    bind_host: str = "127.0.0.1"
    port: int = 8000
    requests_per_minute: int = 60
    max_concurrent_requests: int = 16
    per_key_concurrency: int = 4

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "HostedSettings":
        values = dict(os.environ if env is None else env)
        if values.get("RELEEM_MCP_PROFILE") != "hosted":
            raise ValueError("HTTP requires the hosted profile")
        if any(
            k in values for k in ("RELEEM_API_TOKEN", "RELEEM_SECRET_KEY", "RELEEM_API_TOKEN_FILE")
        ):
            raise ValueError("Hosted profile forbids global customer credentials")
        public = values.pop("RELEEM_MCP_PUBLIC_URL", "")
        parsed = urlsplit(public)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path != "/mcp"
            or parsed.query
            or parsed.fragment
            or parsed.port == 0
        ):
            raise ValueError("Configure the public HTTPS /mcp URL")
        host = values.pop("RELEEM_MCP_BIND_HOST", "127.0.0.1")
        if host not in {"127.0.0.1", "0.0.0.0", "::1"}:  # noqa: S104 -- explicit admin setting
            raise ValueError("Unsupported bind address")
        limits = {}
        for name, default, maximum in [
            ("PORT", 8000, 65535),
            ("REQUESTS_PER_MINUTE", 60, 600),
            ("MAX_CONCURRENT_REQUESTS", 16, 128),
            ("PER_KEY_CONCURRENCY", 4, 16),
        ]:
            number = int(values.pop("RELEEM_MCP_" + name, str(default)))
            if not 1 <= number <= maximum:
                raise ValueError("Hosted limit outside supported bounds")
            limits[name.lower()] = number
        if values.get("RELEEM_API_ALLOW_PRIVATE", "false").lower() != "false":
            raise ValueError("Hosted private upstream origins are unsupported")
        values["RELEEM_MCP_PROFILE"] = "local"
        values["RELEEM_API_TOKEN"] = "configuration-validation-only"  # noqa: S105
        common = Settings.from_env(values)
        return cls(
            public,
            common.base_url,
            common.ca_bundle,
            common.proxy,
            common.max_output_bytes,
            common.sensitive_details,
            host,
            **limits,
        )

    def for_key(self, key: str) -> Settings:
        return Settings(
            SecretStr(key),
            self.base_url,
            self.ca_bundle,
            self.proxy,
            self.max_output_bytes,
            self.sensitive_details,
        )

    def redacted(self) -> dict[str, object]:
        return {
            "profile": "hosted",
            "transport": "streamable-http",
            "read_only": True,
            "public_url": self.public_url,
            "base_url": self.base_url,
            "global_customer_credential": False,
            "sensitive_details": self.sensitive_details,
        }
