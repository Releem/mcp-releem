"""Bounded process-local pilot admission control; fingerprints contain no raw keys."""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from .config import HostedSettings


@dataclass
class Bucket:
    start: float
    requests: int = 0
    active: int = 0


class Limits:
    def __init__(self, settings: HostedSettings) -> None:
        self.settings = settings
        self.salt = secrets.token_bytes(32)
        self.buckets: dict[str, Bucket] = {}
        self.global_bucket = Bucket(time.monotonic())

    def acquire(self, key: str) -> str | None:
        now = time.monotonic()
        fingerprint = hmac.new(self.salt, key.encode(), hashlib.sha256).hexdigest()
        self.buckets = {k: v for k, v in self.buckets.items() if v.active or now - v.start < 60}
        global_bucket = self.global_bucket
        if now - global_bucket.start >= 60:
            global_bucket.start, global_bucket.requests = now, 0
        bucket = self.buckets.get(fingerprint)
        if bucket is None:
            if len(self.buckets) >= 2048:
                return None
            bucket = self.buckets[fingerprint] = Bucket(now)
        if (
            global_bucket.active >= self.settings.max_concurrent_requests
            or global_bucket.requests >= 600
            or bucket.active >= self.settings.per_key_concurrency
            or bucket.requests >= self.settings.requests_per_minute
        ):
            return None
        global_bucket.active += 1
        global_bucket.requests += 1
        bucket.active += 1
        bucket.requests += 1
        return fingerprint

    def release(self, fingerprint: str) -> None:
        self.global_bucket.active -= 1
        self.buckets[fingerprint].active -= 1
