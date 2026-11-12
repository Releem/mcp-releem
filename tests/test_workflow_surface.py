import asyncio

import httpx2
import pytest
from mcp import Client
from mcp.shared.exceptions import MCPError
from test_foundation import module


def test_product_exposes_static_workflows_without_upstream_reads():
    config, api, core, surface = (
        module("config"),
        module("api.client"),
        module("core.diagnostics"),
        module("server"),
    )
    calls = []

    def handler(request):
        calls.append(request)
        raise AssertionError("Static workflow must not access API")

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        async with api.ReleemClient(settings, transport=httpx2.MockTransport(handler)) as c:
            async with Client(surface.build_server(settings, service=core.Diagnostics(c))) as mcp:
                prompts = (await mcp.list_prompts()).prompts
                assert {p.name for p in prompts} == {
                    "why_database_slow",
                    "investigate_queries",
                    "explain_recommendation",
                    "incident_changes",
                }
                prompt = await mcp.get_prompt("why_database_slow", {"server_id": "101"})
                assert "server_id=101" in prompt.messages[0].content.text
                resources = (await mcp.list_resources()).resources
                assert [str(r.uri) for r in resources] == ["releem://reference"]
                reference = await mcp.read_resource("releem://reference")
                assert "hourly averages" in reference.contents[0].text
                assert "synthetic-secret" not in str(reference)
                assert calls == []

    asyncio.run(run())


def test_prompt_validation_and_unknown_names_are_sanitized(caplog):
    config, surface = module("config"), module("server")
    server = surface.build_server(
        config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
    )

    async def run():
        for name, args in [
            ("synthetic-secret", {}),
            ("why_database_slow", {"server_id": "synthetic-secret"}),
            ("why_database_slow", {"server_id": "101", "private": "synthetic-secret"}),
            (
                "incident_changes",
                {
                    "server_id": "101",
                    "start_time": "0001-01-01T00:00:00+01:00",
                    "end_time": "2026-11-10T00:00:00Z",
                },
            ),
        ]:
            with pytest.raises(MCPError) as error:
                await server.get_prompt(name, args)
            assert "synthetic-secret" not in str(error.value)
            assert error.value.error.code == -32602

    asyncio.run(run())
    assert "synthetic-secret" not in caplog.text
