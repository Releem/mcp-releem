import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tools/release/synthetic_stdio.py"
# Contract checks must tolerate CPU contention on shared self-hosted runners.
READ_TIMEOUT_SECONDS = 15


@pytest.fixture
def journey(monkeypatch):
    monkeypatch.syspath_prepend(str(FIXTURE.parent))
    return importlib.import_module("local_journey")


async def exercise(target, mode, server_id, journey):
    async with Client(target, mode=mode, read_timeout_seconds=READ_TIMEOUT_SECONDS) as client:
        tools = await client.list_tools()
        assert len(tools.tools) == 10
        assert len((await client.list_prompts()).prompts) == 4
        prompt = await client.get_prompt("why_database_slow", {"server_id": server_id})
        assert f"server_id={server_id}" in prompt.messages[0].content.text
        reference = await client.read_resource("releem://reference")
        assert "hourly averages" in reference.contents[0].text
        result = await client.call_tool("servers", {"limit": 1})
        assert result.structured_content["data"]["items"][0]["id"] == server_id
        assert not result.is_error
        advertised = next(tool for tool in tools.tools if tool.name == "query_evidence")
        assert "period" in advertised.input_schema["properties"]
        assert "end_date" in advertised.input_schema["properties"]
        await journey.check_ranked_queries(client, server_id)
        await journey.check_configuration_changes(client, server_id)
        empty = await client.call_tool("query_evidence", {"server_id": server_id, "period_days": 7})
        assert not empty.is_error and empty.structured_content["status"] == "no_data"
        assert empty.structured_content["data"]["items"] == []
        assert empty.structured_content["data"]["window_bounds"] == "[start_time,end_time)"
        denied = await client.call_tool("execute_change", {})
        assert denied.is_error
        assert denied.structured_content["error"]["code"] == "operation_denied"
        invalid = await client.call_tool("servers", {"hostname": ["synthetic-secret"] * 20})
        assert invalid.is_error
        assert "synthetic-secret" not in invalid.model_dump_json()


@pytest.mark.parametrize("mode", ["legacy", "2026-07-28"])
@pytest.mark.parametrize("server_id", ["101", "202"])
def test_stdio(mode, server_id, journey):
    asyncio.run(
        exercise(
            StdioServerParameters(
                command=sys.executable,
                args=[str(FIXTURE), "--account", server_id],
                env={"PYTHONPATH": str(ROOT / "src")},
            ),
            mode,
            server_id,
            journey,
        )
    )


def test_authenticated_http_journey(journey):
    report = asyncio.run(journey.exercise())
    assert report["protocol_modes"] == ["legacy", "2026-07-28"]
    assert report["two_account_isolation"] is True
    assert report["normalized_queries"] is True
    assert report["configuration_changes"] is True
    assert report["revocation"] is True
    assert report["missing_evidence_visible"] is True
    assert report["recommendation_workflow"] is True


@pytest.mark.parametrize("mode", ["legacy", "2026-07-28"])
def test_actual_cli_discovery_without_api_calls(mode):
    async def run():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_releem"],
            env={
                "RELEEM_API_TOKEN": "synthetic-secret",
                "PYTHONPATH": str(ROOT / "src"),
            },
        )
        async with Client(
            parameters, mode=mode, read_timeout_seconds=READ_TIMEOUT_SECONDS
        ) as client:
            assert len((await client.list_tools()).tools) == 10
            result = await client.call_tool("execute_change", {})
            assert result.is_error
            invalid = await client.call_tool("server_findings", {"server_id": "bad-id"})
            assert invalid.is_error
            assert "synthetic-secret" not in invalid.model_dump_json()

    asyncio.run(run())
