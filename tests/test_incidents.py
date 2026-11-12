import asyncio
from datetime import UTC, datetime

import httpx2
import pytest
from test_foundation import module

WINDOW = {"start_time": "2026-11-10T16:00:00Z", "end_time": "2026-11-10T17:00:00Z"}


@pytest.fixture
def incident_records():
    event = dict(
        server_id=101,
        event_id="801",
        timestamp="2026-11-10T16:30:00",
        name="Configuration applied",
        uid=1234,
        event_type_id=1,
    )
    deadlock = dict(
        id=4,
        server_id=101,
        timestamp="2026-11-10T16:30:00Z",
        database="example_db",
        table="example_table",
        max_active_time=-1,
    )
    task = dict(
        id=401,
        server_id=101,
        status=4,
        type_id=6,
        status_time=None,
        exit_code=2,
        details={"password": "private-details"},
    )
    return {
        "/v1/servers/101/events": {"items": [event]},
        "/v1/servers/101/events/801": dict(
            event_id=801, timestamp=event["timestamp"], event_body={"password": "private-body"}
        ),
        "/v1/servers/101/deadlocks": {"items": [deadlock]},
        "/v1/servers/101/deadlocks/4": {
            **deadlock,
            "raw": "private-dump",
            "txn1": "private-sql",
            "txn2": None,
        },
        "/v1/servers/101/tasks": {"items": [task]},
        "/v1/servers/101/tasks/401": {
            **task,
            "output": "private-output",
            "error": "private-error",
            "report_time": None,
        },
        "/v1/servers/101/processlist": {
            "items": [
                dict(
                    server_id=101,
                    timestamp="2026-11-10T16:30:00Z",
                    processlist=[
                        {
                            "Id": 123,
                            "User": "private-user",
                            "Host": "192.0.2.8",
                            "Info": "select private-value",
                            "Command": "Query",
                            "Time": 12,
                        },
                        {"Command": "Sleep", "Time": 0},
                    ],
                )
            ]
        },
    }


def run_incident(records, name, *, sensitive=False, budget=24576, **arguments):
    config, api, core = module("config"), module("api.client"), module("core.diagnostics")
    calls = []

    def handler(request):
        calls.append(request)
        value = records[request.url.path]
        return value if isinstance(value, httpx2.Response) else httpx2.Response(200, json=value)

    async def run():
        settings = config.Settings.from_env(
            {
                "RELEEM_API_TOKEN": "synthetic-secret",
                "RELEEM_MCP_SENSITIVE_DETAILS": str(sensitive).lower(),
                "RELEEM_MCP_MAX_OUTPUT_BYTES": str(budget),
            }
        )
        async with api.ReleemClient(settings, transport=httpx2.MockTransport(handler)) as client:
            service = core.Diagnostics(client, now=lambda: datetime(2026, 11, 10, 17, tzinfo=UTC))
            return await getattr(service, name)("101", **arguments)

    return asyncio.run(run()), calls


def test_event_page_has_inclusive_utc_window_without_total_or_snapshot(incident_records):
    result, calls = run_incident(incident_records, "events", limit=1, **WINDOW)
    assert result.data["window_bounds"] == "[start_time,end_time]"
    assert result.data["items"][0]["timestamp"].endswith("+00:00")
    assert "uid" not in result.data["items"][0]
    assert result.coverage.next_offset == 1
    assert result.coverage.upstream_total is None
    assert result.coverage.snapshot_consistent is False
    assert not result.coverage.complete
    assert calls[0].url.params["start_time"].endswith("+00:00")


@pytest.mark.parametrize(
    "name,args",
    [
        ("events", dict(view="detail", event_id="801")),
        ("deadlocks", dict(view="detail", deadlock_id=4)),
        ("task_outcomes", dict(view="detail", task_id=401)),
        ("captured_sessions", {}),
    ],
)
def test_sensitive_incident_reads_require_operator_permission(incident_records, name, args):
    result, calls = run_incident(incident_records, name, **args)
    assert result.error.code == "sensitive_detail_disabled"
    assert not calls


@pytest.mark.parametrize(
    "name,args,key",
    [
        ("events", dict(view="detail", event_id="801"), "event"),
        ("deadlocks", dict(view="detail", deadlock_id=4), "deadlock"),
        ("task_outcomes", dict(view="detail", task_id=401), "task"),
    ],
)
def test_sensitive_detail_is_minimized_even_when_enabled(incident_records, name, args, key):
    result, calls = run_incident(incident_records, name, sensitive=True, **args)
    assert result.status == "partial"
    assert key in result.data
    assert "private-" not in result.model_dump_json()
    assert not result.coverage.complete
    assert all(call.method == "GET" for call in calls)


def test_event_missing_payload_is_error_not_empty_event(incident_records):
    incident_records["/v1/servers/101/events/801"] = httpx2.Response(404)
    result, _ = run_incident(
        incident_records, "events", sensitive=True, view="detail", event_id="801"
    )
    assert result.error.code == "not_found_or_inaccessible"
    assert "event_payload_may_be_absent" in {w.code for w in result.warnings}


def test_deadlock_unknown_duration_and_task_missing_report_visible(incident_records):
    result, _ = run_incident(incident_records, "deadlocks", **WINDOW)
    assert result.data["items"][0]["max_active_time"] == -1
    assert result.data["units"]["max_active_time"] == "s"
    result, _ = run_incident(
        incident_records, "deadlocks", sensitive=True, view="detail", deadlock_id=4
    )
    assert result.data["units"]["max_active_time"] == "s"
    result, _ = run_incident(
        incident_records, "task_outcomes", sensitive=True, view="detail", task_id=401
    )
    assert result.data["task"]["report_time"] is None
    assert result.data["task"]["error_available"] is True
    assert "final_report_absent" in {w.code for w in result.warnings}


def test_unknown_task_codes_are_not_fabricated_as_success(incident_records):
    task = incident_records["/v1/servers/101/tasks"]["items"][0]
    task.update(status=999, type_id=999, status_label="succeeded", type="apply_schema_changes")
    result, _ = run_incident(incident_records, "task_outcomes")
    row = result.data["items"][0]
    assert row["status"] == 999 and row["type_id"] == 999
    assert row["status_label"] is None and row["type"] is None
    assert "unknown_task_code" in {w.code for w in result.warnings}


def test_capture_is_historical_and_contains_only_aggregate_sessions(incident_records):
    result, calls = run_incident(incident_records, "captured_sessions", sensitive=True)
    assert result.data["live"] is False
    summary = result.data["items"][0]["session_summary"]
    assert summary["session_count"] == 2
    assert summary["commands"] == {"Query": 1, "Sleep": 1}
    assert summary["max_duration_seconds"] == 12
    assert "start_time" not in calls[0].url.params
    assert "private-" not in result.model_dump_json()
    assert "192.0.2.8" not in result.model_dump_json()


@pytest.mark.parametrize(
    "payload,parse_status", [(None, "unavailable"), ("not JSON", "unrecognized"), ("[]", "decoded")]
)
def test_capture_missing_or_text_payload_does_not_imply_health(
    incident_records, payload, parse_status
):
    incident_records["/v1/servers/101/processlist"]["items"][0]["processlist"] = payload
    result, _ = run_incident(incident_records, "captured_sessions", sensitive=True)
    assert result.data["items"][0]["session_summary"]["parse_status"] == parse_status
    assert result.status == "partial"


@pytest.mark.parametrize(
    "name,args",
    [
        ("events", dict(view="detail", event_id="18446744073709551616")),
        ("events", dict(view="detail", event_id="801", limit=1)),
        ("events", dict(start_time="2026-11-10T16:00:00")),
        ("events", dict(start_time="2026-10-01T00:00:00Z", end_time="2026-11-10T00:00:00Z")),
        ("events", dict(start_time="2026-11-10T16:00:00.123Z", end_time=WINDOW["end_time"])),
        ("deadlocks", dict(end_time=WINDOW["end_time"])),
        ("task_outcomes", dict(view="detail", task_id=401, status=4)),
        ("captured_sessions", dict(mode="window")),
        ("captured_sessions", dict(limit=21)),
        ("task_outcomes", dict(tasks_type_id=6)),
    ],
)
def test_incident_invalid_input_makes_no_api_request(incident_records, name, args):
    result, calls = run_incident(incident_records, name, sensitive=True, **args)
    assert result.error.code == "invalid_arguments"
    assert not calls


@pytest.mark.parametrize(
    "name,path,args,change",
    [
        ("events", "/events", WINDOW, {"server_id": 202}),
        ("events", "/events/801", dict(view="detail", event_id="801"), {"event_id": 802}),
        ("deadlocks", "/deadlocks/4", dict(view="detail", deadlock_id=4), {"id": 5}),
        ("task_outcomes", "/tasks/401", dict(view="detail", task_id=401), {"server_id": 202}),
        ("captured_sessions", "/processlist", {}, {"server_id": 202}),
    ],
)
def test_incident_parent_and_child_identity_is_enforced(incident_records, name, path, args, change):
    payload = incident_records["/v1/servers/101" + path]
    (payload["items"][0] if "items" in payload else payload).update(change)
    result, _ = run_incident(incident_records, name, sensitive=True, **args)
    assert result.error.code == "invalid_source_data"


def test_sensitive_setting_is_strict_and_redacted():
    config = module("config")
    for value in ["yes", "1", "invalid"]:
        with pytest.raises(ValueError):
            config.Settings.from_env(
                {"RELEEM_API_TOKEN": "synthetic-secret", "RELEEM_MCP_SENSITIVE_DETAILS": value}
            )
    assert (
        config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"}).sensitive_details
        is False
    )
