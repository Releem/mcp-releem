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
        config_id = 501 if sid == "101" else 601
        state = {
            "server_id": int(sid),
            "configuration_status_id": config_id,
            "configuration_id": 401,
            "applied_status": {"id": 2, "name": "Partially applied"},
            "applied_timestamp": 1794481200,
            "timestamp": 1794481100,
            "configuration_timestamp": 1794481000,
            "is_first": False,
        }
        older = {**state, "configuration_status_id": config_id + 1, "applied_timestamp": 1794480000}
        detail = {
            **state,
            "variables_orig": {"max_connections": 100, "table_open_cache": 2000},
            "source_variables": {"max_connections": 150, "table_open_cache": 4000},
            "variables": [
                {"name": "max_connections", "value": "200"},
                {"name": "table_open_cache", "value": "4000"},
            ],
            "history": {
                "timestamp": 1794481100,
                "performance_score": 65,
                "config_recommendations": "synthetic-configuration-canary",
            },
        }
        open_rec = {
            **rec,
            "id": rec["id"] + 10,
            "source_id": str(config_id),
            "status": "new",
            "created_at": "2026-11-11T10:00:00Z",
        }
        configs_path = f"/v1/servers/{sid}/configurations"
        paths: dict[str, Any] = {
            "/v1/servers": [server],
            f"/v1/servers/{sid}": server,
            configs_path: {"items": [older, state]},
            f"{configs_path}/{config_id}": detail,
            f"{configs_path}/{config_id + 1}": {
                **detail,
                **older,
                "variables_orig": {"max_connections": 90},
                "source_variables": {"max_connections": 100},
                "variables": [{"name": "max_connections", "value": "100"}],
            },
            f"/v1/servers/{sid}/recommendations/{open_rec['id']}": {
                **open_rec,
                "evidence": {"href": f"{configs_path}/{config_id}"},
            },
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
        if (
            request.url.path == f"/v1/servers/{sid}/recommendations"
            and request.url.params.get("status") == "new"
        ):
            return httpx2.Response(
                200, json={"items": [open_rec], "total": 1, "limit": 20, "offset": 0}
            )
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
            items = []
            if window == windows[("10m", None, None)]:
                query_id, query = (
                    ("abc123", "SELECT * FROM example_orders WHERE id = ?")
                    if sid == "101"
                    else ("def456", "SELECT amount FROM example_payments WHERE account_id = ?")
                )
                items = [
                    {
                        "rid": f"run-{sid}",
                        "schema_name": "example",
                        "query_id": query_id,
                        "query": query,
                        "query_text": "SELECT 'raw-only-canary'",
                        "calls": 20,
                        "avg_time_ms": 150,
                        "sum_time_sec": 3,
                        "sum_time_perc_total": 25,
                    },
                    {
                        "rid": f"run-{sid}",
                        "schema_name": "example",
                        "query_id": f"raw-{sid}",
                        "query_text": "SELECT 'raw-only-canary'",
                        "calls": 2,
                    },
                ]
            return httpx2.Response(
                200, json={"start_time": window[0], "end_time": window[1], "items": items}
            )
        if request.url.path not in paths:
            return httpx2.Response(404)
        return httpx2.Response(200, json=paths[request.url.path])
