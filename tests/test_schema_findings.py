import asyncio

import httpx2
import pytest
from mcp import Client
from test_diagnostics import run_with
from test_foundation import module


@pytest.fixture
def schema_records(records):
    records["/v1/servers/101/schema-checks"] = {
        "server_id": 101,
        "timestamp": "2026-11-10T17:59:00",
        "items": [
            dict(
                server_id=101,
                is_check=1,
                type="unused_index",
                count_checks=2,
                data='{"password":"private-value","sql":"SELECT * FROM private_table"}',
            )
        ],
    }
    return records


def test_schema_findings_keep_counts_but_omit_arbitrary_payloads(schema_records):
    result, calls = run_with(schema_records, lambda s: s.findings("101", sections=["schema"]))
    assert result.status == "partial"
    report = result.data["reports"]["schema"]
    assert report["timestamp"] == "2026-11-10T17:59:00+00:00"
    assert report["items"][0]["count_checks"] == 2
    assert report["items"][0]["has_finding"] is True
    assert "private-" not in result.model_dump_json()
    assert "private_table" not in result.model_dump_json()
    assert result.evidence[0].operation_id == "O35"
    assert result.evidence[0].observed_at == report["timestamp"]
    assert "source_timezone_utc" in {w.code for w in result.warnings}
    assert len(calls) == 1


@pytest.mark.parametrize(
    "filtered,state", [(False, "no_findings_in_completed_run"), (True, "no_matches")]
)
def test_empty_completed_schema_run_has_filter_aware_meaning(schema_records, filtered, state):
    schema_records["/v1/servers/101/schema-checks"]["items"] = []
    args = {"schema_name": "example_db", "check_type": "unused_index"} if filtered else {}
    result, calls = run_with(
        schema_records, lambda s: s.findings("101", sections=["schema"], **args)
    )
    assert result.data["reports"]["schema"]["state"] == state
    assert "healthy" not in result.model_dump_json()
    if filtered:
        assert calls[0].url.params["type"] == "unused_index"
        assert "check_type" not in calls[0].url.params


def test_absent_schema_run_is_not_an_empty_healthy_snapshot(schema_records):
    schema_records["/v1/servers/101/schema-checks"].update(timestamp=None, items=[])
    result, _ = run_with(schema_records, lambda s: s.findings("101", sections=["schema"]))
    assert result.status == "partial"
    assert result.data["reports"]["schema"]["state"] == "not_run"
    assert not result.coverage.complete
    assert result.evidence[0].observed_at is None
    assert "schema_snapshot_absent" in {w.code for w in result.warnings}


@pytest.mark.parametrize(
    "change",
    [dict(server_id=202), dict(timestamp="invalid"), dict(timestamp=""), dict(timestamp=None)],
)
def test_schema_bad_parent_time_or_inconsistent_snapshot_is_component_failure(
    schema_records, change
):
    schema_records["/v1/servers/101/schema-checks"].update(change)
    result, _ = run_with(schema_records, lambda s: s.findings("101", sections=["schema"]))
    assert result.status == "error"
    assert result.data["component_errors"]["schema"]["code"] == "invalid_source_data"
    assert result.evidence == []


def test_schema_row_parent_and_partial_fetch_failure_visible(schema_records):
    schema_records["/v1/servers/101/schema-checks"]["items"][0]["server_id"] = 202
    result, _ = run_with(schema_records, lambda s: s.findings("101", sections=["health", "schema"]))
    assert result.status == "partial"
    assert result.data["component_errors"]["schema"]["code"] == "invalid_source_data"
    assert "health" in result.data["reports"]


def test_schema_decode_errors_unknown_flags_and_missing_scope_are_visible(schema_records):
    page = schema_records["/v1/servers/101/schema-checks"]
    page.update(server_id=None, timestamp="2026-11-09T00:00:00Z")
    page["items"][0].update(data="bad JSON", is_check=9, type="future_check")
    result, _ = run_with(schema_records, lambda s: s.findings("101", sections=["schema"]))
    row = result.data["reports"]["schema"]["items"][0]
    assert row["has_finding"] is None
    codes = {w.code for w in result.warnings}
    assert {
        "schema_decode_error",
        "unknown_schema_check",
        "schema_scope_missing",
        "report_age_exceeds_15m",
    } <= codes
    assert result.status == "partial"


def test_schema_row_limits_and_filter_mismatch_are_explicit(schema_records):
    schema_records["/v1/servers/101/schema-checks"]["items"] *= 3
    result, _ = run_with(
        schema_records, lambda s: s.findings("101", sections=["schema"], schema_limit=1)
    )
    report = result.data["reports"]["schema"]
    assert len(report["items"]) == 1
    assert report["coverage"]["omitted"] == 2
    assert not result.coverage.complete
    result, _ = run_with(
        schema_records, lambda s: s.findings("101", sections=["schema"], check_type="collation")
    )
    assert result.data["component_errors"]["schema"]["code"] == "invalid_source_data"


@pytest.mark.parametrize(
    "args",
    [
        dict(schema_name="example_db"),
        dict(sections=["schema"], check_type="UNUSED_INDEX_NEW"),
        dict(sections=["schema"], schema_limit=101),
        dict(sections=["schema"], schema_name=""),
        dict(sections=["schema", "schema"]),
    ],
)
def test_invalid_schema_arguments_never_call_api(schema_records, args):
    result, calls = run_with(schema_records, lambda s: s.findings("101", **args))
    assert result.error.code == "invalid_arguments"
    assert not calls


def test_schema_mcp_dispatch_supports_all_four_sections(schema_records):
    config, api, core, surface = (
        module("config"),
        module("api.client"),
        module("core.diagnostics"),
        module("server"),
    )

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        async with api.ReleemClient(
            settings,
            transport=httpx2.MockTransport(
                lambda req: httpx2.Response(200, json=schema_records[req.url.path])
            ),
        ) as c:
            async with Client(surface.build_server(settings, service=core.Diagnostics(c))) as mcp:
                result = await mcp.call_tool(
                    "server_findings",
                    dict(
                        server_id="101",
                        sections=["summary", "health", "security", "schema"],
                        check_type="unused_index",
                    ),
                )
                assert not result.is_error
                assert "schema" in result.structured_content["data"]["reports"]

    asyncio.run(run())
