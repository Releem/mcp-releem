import asyncio

import httpx2
import pytest
from mcp import Client
from test_foundation import module
from test_incidents import WINDOW, incident_records, run_incident

__all__ = ["incident_records"]


@pytest.mark.parametrize("detail", [False, True])
def test_deadlock_view_state_failure_is_sanitized(incident_records, detail):
    path = "/v1/servers/101/deadlocks/4" if detail else "/v1/servers/101/deadlocks"
    incident_records[path] = httpx2.Response(
        503,
        json={"error": {"code": "deadlock_view_state_unavailable", "message": "private-error"}},
    )
    args = {"view": "detail", "deadlock_id": 4} if detail else WINDOW
    result, _ = run_incident(incident_records, "deadlocks", sensitive=True, **args)
    assert result.error.code == "dependency_unavailable"
    assert result.error.upstream_status == 503
    assert result.data is None
    assert "private-error" not in result.model_dump_json()


def test_event_duplicates_are_visible_and_next_offset_counts_source_rows(incident_records):
    incident_records["/v1/servers/101/events"]["items"] *= 2
    result, _ = run_incident(incident_records, "events", limit=2, **WINDOW)
    assert len(result.data["items"]) == 1
    assert result.coverage.omitted == 1
    assert result.coverage.next_offset == 2
    assert "duplicate_events" in {w.code for w in result.warnings}


def test_event_detail_preserves_uint64_as_a_string_for_mcp_clients(incident_records):
    value = "18446744073709551615"
    row = incident_records.pop("/v1/servers/101/events/801")
    row["event_id"] = int(value)
    incident_records["/v1/servers/101/events/" + value] = row
    result, _ = run_incident(
        incident_records, "events", sensitive=True, view="detail", event_id=value
    )
    assert result.data["event"]["event_id"] == value


def test_event_budget_does_not_leave_a_skipping_cursor(incident_records):
    row = incident_records["/v1/servers/101/events"]["items"][0]
    incident_records["/v1/servers/101/events"]["items"] = [
        {**row, "event_id": str(801 + i), "name": "a" * 400} for i in range(20)
    ]
    result, _ = run_incident(incident_records, "events", limit=20, budget=4096, **WINDOW)
    assert len(result.model_dump_json().encode()) <= 4096
    assert result.coverage.omitted > 0
    assert result.coverage.next_offset is None
    assert "output_truncated" in {w.code for w in result.warnings}


def test_capture_examination_is_bounded_and_commands_do_not_echo_injection(incident_records):
    row = incident_records["/v1/servers/101/processlist"]["items"][0]
    row["processlist"] = [{"Command": "private-instruction", "Time": 3}] * 501
    result, _ = run_incident(incident_records, "captured_sessions", sensitive=True)
    summary = result.data["items"][0]["session_summary"]
    assert summary["session_count"] == 501
    assert summary["examined_sessions"] == 500 and summary["rows_omitted"] == 1
    assert summary["unknown_commands"] == 500
    assert "private-instruction" not in result.model_dump_json()
    assert "capture_rows_limited" in {w.code for w in result.warnings}


def test_task_filters_and_invalid_source_time_are_not_silent(incident_records):
    result, calls = run_incident(incident_records, "task_outcomes", status=4, type_id=6)
    assert calls[0].url.params["status"] == "4"
    assert calls[0].url.params["type_id"] == "6"
    assert result.status == "partial"
    result, _ = run_incident(incident_records, "task_outcomes", status=1)
    assert result.error.code == "invalid_source_data"
    result, _ = run_incident(incident_records, "task_outcomes", type_id=3)
    assert result.error.code == "invalid_source_data"
    incident_records["/v1/servers/101/events"]["items"][0]["timestamp"] = "bad"
    result, _ = run_incident(incident_records, "events", **WINDOW)
    assert result.error.code == "invalid_source_data"


def test_mcp_incident_dispatch_uses_the_discovered_contract(incident_records):
    config, api, core, surface = (
        module("config"),
        module("api.client"),
        module("core.diagnostics"),
        module("server"),
    )
    calls = []

    def handler(req):
        calls.append(req)
        return httpx2.Response(200, json=incident_records[req.url.path])

    async def run():
        settings = config.Settings.from_env(
            {"RELEEM_API_TOKEN": "synthetic-secret", "RELEEM_MCP_SENSITIVE_DETAILS": "true"}
        )
        async with api.ReleemClient(settings, transport=httpx2.MockTransport(handler)) as c:
            service = core.Diagnostics(c)
            async with Client(surface.build_server(settings, service=service)) as mcp:
                for name, args in [
                    ("events", dict(view="detail", event_id="801")),
                    ("deadlocks", dict(view="detail", deadlock_id=4)),
                    ("task_outcomes", dict(view="detail", task_id=401)),
                    ("captured_sessions", dict(mode="latest")),
                ]:
                    result = await mcp.call_tool(name, {"server_id": "101", **args})
                    assert not result.is_error
                    assert "private-" not in result.model_dump_json()
                    if name == "task_outcomes":
                        row = result.structured_content["data"]["task"]
                        assert row["type"] == {"id": 6, "name": "apply_schema_changes"}
                        assert "type_id" not in row
                invalid = await mcp.call_tool(
                    "captured_sessions",
                    dict(
                        server_id="101",
                        mode="latest",
                        start_time=WINDOW["start_time"],
                        end_time=WINDOW["end_time"],
                    ),
                )
                assert invalid.is_error
                denied = await mcp.call_tool("create_task", dict(server_id="101", tasks_type_id=6))
                assert denied.is_error
                assert len(calls) == 4 and all(req.method == "GET" for req in calls)

    asyncio.run(run())
