"""Public synthetic records for local release validation; never calls upstream."""

import time
from typing import Any

import httpx2

KEY_A = "synthetic-key-A"
KEY_B = "synthetic-key-B"


class SyntheticAPI:
    def __init__(self) -> None:
        self.revoked: set[str] = set()
        self.unavailable = False
        self.calls: list[tuple[str | None, str]] = []

    async def __call__(self, request: httpx2.Request) -> httpx2.Response:
        key = request.headers.get("Releem-Secret-Key")
        self.calls.append((key, request.url.path))
        if self.unavailable:
            return httpx2.Response(503)
        if key not in {KEY_A, KEY_B} or key in self.revoked:
            return httpx2.Response(401)
        sid = "101" if key == KEY_A else "202"
        server = {"id": sid, "server_name": "synthetic-db-" + sid, "status": "active"}
        rec: dict[str, Any] = {
            "id": 601 if sid == "101" else 602,
            "server_id": sid,
            "source_type": "configuration",
            "source_id": "501",
            "source_subtype": "memory",
            "title": "Review memory demand",
            "summary": "Compare measured demand before changing",
            "status": "done",
            "priority_score": 90.0,
            "type_id": 3,
            "category_id": 3,
        }
        paths: dict[str, Any] = {
            "/v1/servers": [server],
            f"/v1/servers/{sid}": server,
            f"/v1/servers/{sid}/details": {"id": sid, "health_checks": {}, "security_checks": {}},
            f"/v1/servers/{sid}/health-checks": {"timestamp": None, "checks": {}},
            f"/v1/servers/{sid}/security-checks": {
                "timestamp": int(time.time()),
                "checks": {
                    "accounts": {
                        "failed": True,
                        "description": "Synthetic account finding",
                        "value": None,
                        "title": "Account policy",
                        "short_description": None,
                        "severity": "warning",
                        "group": "security",
                        "learn_more_url": "https://example.invalid/private-reference",
                    }
                },
                "failed_checks": ["accounts"],
                "security_checks_score": 70.0,
            },
            f"/v1/servers/{sid}/recommendations": {
                "items": [rec],
                "total": 1,
                "limit": 20,
                "offset": 0,
            },
            f"/v1/servers/{sid}/recommendations/{rec['id']}": rec,
        }
        if request.url.path == f"/v1/servers/{sid}/query-analytics":
            # Fixed contract examples deliberately independent of production parsing.
            windows = {
                ("10m", None, None): ("2026-11-11T10:00:00", "2026-11-11T10:10:00"),
                ("7d", None, None): ("2026-11-04T10:00:00", "2026-11-11T10:00:00"),
                ("1d", "2026-11-11T10:00:00+00:00", "2026-11-11T10:10:00+00:00"): (
                    "2026-11-11T10:00:00",
                    "2026-11-11T10:10:00",
                ),
            }
            params = request.url.params
            if "period_days" in params:
                return httpx2.Response(400, json={"error": {"code": "invalid_period"}})
            window = windows.get(
                (params.get("period"), params.get("start_date"), params.get("end_date"))
            )
            if window is None:
                return httpx2.Response(400, json={"error": {"code": "invalid_time_range"}})
            return httpx2.Response(
                200, json={"start_time": window[0], "end_time": window[1], "items": []}
            )
        if request.url.path not in paths:
            return httpx2.Response(404)
        return httpx2.Response(200, json=paths[request.url.path])
