"""Static diagnostic workflows never fetch evidence or enable operations."""

import asyncio

import pytest
from mcp.server import MCPServer
from pydantic import ValidationError
from test_foundation import module


def test_static_prompt_and_resource_discovery_and_rendering():
    workflows = module("workflows")

    async def run():
        server = MCPServer("workflow-tests")
        workflows.register(server)
        prompts = await server.list_prompts()
        assert {item.name for item in prompts} == {
            "why_database_slow",
            "investigate_queries",
            "explain_recommendation",
            "incident_changes",
        }
        assert await server.list_tools() == []
        for prompt in prompts:
            assert next(a for a in prompt.arguments if a.name == "server_id").required
            args = {"server_id": "101"}
            if prompt.name == "explain_recommendation":
                args["recommendation_id"] = "7"
            result = await server.get_prompt(prompt.name, args)
            text = result.messages[0].content.text
            assert "server_id=101" in text
            for term in ["untrusted", "observations", "hypotheses", "freshness", "coverage"]:
                assert term in text
            assert "No SQL execution" in text
            if prompt.name == "investigate_queries":
                assert "structuredContent.data.items" in text
                assert "show query beside query_id" in text
                assert "partial prefix" in text and "query_status" in text
                assert "schema_name and query_id" in text
            if prompt.name == "incident_changes":
                assert "applied_changes" in text and "rollback status" in text
            assert len(text) < 6500
        resources = await server.list_resources()
        assert [str(item.uri) for item in resources] == ["releem://reference"]
        content = list(await server.read_resource("releem://reference"))[0].content
        assert "0.1.0" in content
        for term in [
            "sum_time_sec",
            "avg_time_ms",
            "UTC",
            "sensitive_detail_disabled",
            "upstream_auth_failed",
            "model",
            "hourly",
            "configuration_status_id",
            "query_status=available",
            "applied_changes",
            "variable_changes.remaining",
            "budget_exhausted",
        ]:
            assert term in content
        assert content == list(await server.read_resource("releem://reference"))[0].content

    asyncio.run(run())


@pytest.mark.parametrize(
    "name,args",
    [
        ("why_database_slow", {}),
        ("why_database_slow", {"server_id": "01"}),
        ("why_database_slow", {"server_id": "101", "sql": "select 1"}),
        ("explain_recommendation", {"server_id": "101", "recommendation_id": "0"}),
        ("explain_recommendation", {"server_id": "101", "recommendation_id": 7}),
        ("incident_changes", {"server_id": "101", "start_time": "2026-11-01T00:00:00Z"}),
        (
            "incident_changes",
            {
                "server_id": "101",
                "start_time": "2026-11-01T00:00:00",
                "end_time": "2026-11-02T00:00:00",
            },
        ),
        (
            "incident_changes",
            {
                "server_id": "101",
                "start_time": "2026-11-02T00:00:00Z",
                "end_time": "2026-11-01T00:00:00Z",
            },
        ),
        (
            "incident_changes",
            {
                "server_id": "101",
                "start_time": "2026-11-01T00:00:00Z",
                "end_time": "2026-11-09T00:00:00Z",
            },
        ),
    ],
)
def test_prompt_inputs_reject_unbounded_or_injected_arguments(name, args):
    workflows = module("workflows")
    with pytest.raises(ValidationError):
        workflows.PROMPT_VALIDATORS[name].model_validate(args)


def test_incident_window_normalization_and_bounded_instructions():
    workflows = module("workflows")

    async def run():
        server = MCPServer("workflow-tests")
        workflows.register(server)
        result = await server.get_prompt(
            "incident_changes",
            {
                "server_id": "101",
                "start_time": "2026-11-01T03:00:00+03:00",
                "end_time": "2026-11-01T04:00:00+03:00",
            },
        )
        text = result.messages[0].content.text
        assert "2026-11-01T00:00:00+00:00" in text
        assert "offset" in text and "fetch" in text
        query = await server.get_prompt("investigate_queries", {"server_id": "101"})
        assert "up to three" in query.messages[0].content.text

    asyncio.run(run())


@pytest.mark.parametrize("end", ["2026-11-01T00:00:00Z", "2026-11-01T00:00:00.5Z"])
def test_incident_workflow_requires_nonempty_whole_second_window(end):
    workflows = module("workflows")
    with pytest.raises(ValidationError):
        workflows.PROMPT_VALIDATORS["incident_changes"].model_validate(
            {
                "server_id": "101",
                "start_time": "2026-11-01T00:00:00Z",
                "end_time": end,
            }
        )
