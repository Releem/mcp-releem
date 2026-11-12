import asyncio

import httpx2
import pytest
from mcp import Client
from test_diagnostics import run_with
from test_foundation import module


@pytest.fixture
def fleet_records(records):
    records["/v1/servers/recommendations"] = records["/v1/servers/101/recommendations"]
    return records


def test_fleet_is_explicit_and_checks_accessible_server_inventory(fleet_records):
    result, calls = run_with(fleet_records, lambda s: s.recommendations(scope="fleet", limit=1))
    assert result.data["items"][0]["server_id"] == "101"
    assert result.scope == {"selection": "fleet"}
    assert [c.url.path for c in calls] == ["/v1/servers", "/v1/servers/recommendations"]
    assert calls[1].url.params["limit"] == "1"
    assert len(result.evidence) == 2
    assert result.evidence[-1].operation_id == "O01"
    assert "active_servers_only" in {w.code for w in result.warnings}


def test_fleet_refuses_foreign_server_rows_without_leaking_totals(fleet_records):
    fleet_records["/v1/servers/recommendations"]["items"][0]["server_id"] = "202"
    result, _ = run_with(fleet_records, lambda s: s.recommendations(scope="fleet"))
    assert result.error.code == "invalid_source_data"
    assert result.data is None
    assert result.coverage.upstream_total is None


def test_inventory_failure_stops_fleet_request(fleet_records):
    fleet_records["/v1/servers"] = httpx2.Response(403)
    result, calls = run_with(fleet_records, lambda s: s.recommendations(scope="fleet"))
    assert result.error.code == "forbidden"
    assert len(calls) == 1


def test_list_dates_are_utc_normalized_and_invalid_times_are_rejected(fleet_records):
    row = fleet_records["/v1/servers/recommendations"]["items"][0]
    row["created_at"] = "2026-11-10T17:00:00"
    result, _ = run_with(fleet_records, lambda s: s.recommendations(scope="fleet"))
    assert result.data["items"][0]["created_at"].endswith("+00:00")
    assert "source_timezone_utc" in {w.code for w in result.warnings}
    row["updated_at"] = "bad"
    result, _ = run_with(fleet_records, lambda s: s.recommendations(scope="fleet"))
    assert result.error.code == "invalid_source_data"


@pytest.mark.parametrize(
    "args",
    [
        {},
        dict(scope="fleet", server_id="101"),
        dict(scope="fleet", view="detail", recommendation_id=601),
    ],
)
def test_ambiguous_or_inapplicable_scope_never_reads_api(fleet_records, args):
    result, calls = run_with(fleet_records, lambda s: s.recommendations(**args))
    assert result.error.code == "invalid_arguments"
    assert not calls


def test_fleet_dispatch_uses_same_typed_scope_contract(fleet_records):
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
                lambda req: httpx2.Response(200, json=fleet_records[req.url.path])
            ),
        ) as c:
            async with Client(surface.build_server(settings, service=core.Diagnostics(c))) as mcp:
                result = await mcp.call_tool("recommendations", {"scope": "fleet", "limit": 1})
                assert not result.is_error
                assert result.structured_content["scope"]["selection"] == "fleet"
                invalid = await mcp.call_tool("recommendations", {})
                assert invalid.is_error

    asyncio.run(run())
