import asyncio
import json
import os
import subprocess
import sys

import httpx2
from mcp import Client
from test_foundation import module


def test_ten_read_tools_structured_errors_and_output_schemas(records):
    config = module("config")
    api = module("api.client")
    core = module("core.diagnostics")
    surface = module("server")

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        async with api.ReleemClient(
            settings,
            transport=httpx2.MockTransport(
                lambda req: httpx2.Response(200, json=records[req.url.path]),
            ),
        ) as client:
            server = surface.build_server(settings, service=core.Diagnostics(client))
            async with Client(server) as mcp:
                listed = await mcp.list_tools()
                assert {tool.name for tool in listed.tools} == {
                    "servers",
                    "server_findings",
                    "recommendations",
                    "query_evidence",
                    "configurations",
                    "metrics",
                    "events",
                    "deadlocks",
                    "captured_sessions",
                    "task_outcomes",
                }
                assert all(tool.annotations.read_only_hint for tool in listed.tools)
                assert all(tool.output_schema for tool in listed.tools)
                inventory = next(t for t in listed.tools if t.name == "servers")
                assert inventory.input_schema["properties"]["limit"]["maximum"] == 100
                good = await mcp.call_tool("servers", {"limit": 1})
                assert not good.is_error
                assert good.structured_content["data"]["items"][0]["id"] == "101"
                for name, args in [
                    ("execute_change", {}),
                    ("recommendations", {"server_id": "synthetic-secret"}),
                    ("recommendations", {"server_id": "101", "unexpected": "synthetic-secret"}),
                ]:
                    result = await mcp.call_tool(name, args)
                    assert result.is_error
                    assert result.structured_content["status"] == "error"
                    assert "synthetic-secret" not in result.model_dump_json()
                    assert len(result.content[0].text) < 1000

    asyncio.run(run())


def test_cli_check_has_no_secret_output_and_rejects_http():
    module("cli")
    env = {**os.environ, "RELEEM_API_TOKEN": "synthetic-secret"}
    checked = subprocess.run(
        [sys.executable, "-m", "mcp_releem", "--check"],
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["read_only"] is True
    assert "synthetic-secret" not in checked.stdout + checked.stderr
    rejected = subprocess.run(
        [sys.executable, "-m", "mcp_releem", "--transport", "streamable-http"],
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert rejected.returncode != 0
    assert "synthetic-secret" not in rejected.stdout + rejected.stderr


def test_cli_missing_configuration_is_actionable():
    module("cli")
    env = {k: v for k, v in os.environ.items() if not k.startswith("RELEEM_")}
    result = subprocess.run(
        [sys.executable, "-m", "mcp_releem", "--check"],
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "token" in result.stderr.lower()


def test_query_tool_discovery_and_dispatch_use_the_same_typed_contract():
    config = module("config")
    api = module("api.client")
    core = module("core.diagnostics")
    surface = module("server")

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        async with api.ReleemClient(
            settings,
            transport=httpx2.MockTransport(
                lambda _: httpx2.Response(
                    200,
                    json={
                        "start_time": "2026-11-09T00:00:00",
                        "end_time": "2026-11-10T00:00:00",
                        "items": [],
                    },
                ),
            ),
        ) as client:
            async with Client(
                surface.build_server(settings, service=core.Diagnostics(client))
            ) as mcp:
                tools = (await mcp.list_tools()).tools
                assert "query_evidence" in {tool.name for tool in tools}
                result = await mcp.call_tool("query_evidence", {"server_id": "101"})
                assert not result.is_error
                assert result.structured_content["status"] == "no_data"
                invalid = await mcp.call_tool(
                    "query_evidence", {"server_id": "101", "query_text": "synthetic-secret"}
                )
                assert invalid.is_error
                assert "synthetic-secret" not in invalid.model_dump_json()

    asyncio.run(run())
