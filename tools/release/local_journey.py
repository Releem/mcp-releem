"""Real loopback TCP client journey against installed hosted core, synthetic API only."""

import asyncio
import json
import socket
from contextlib import asynccontextmanager
from typing import Any

import httpx2
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from synthetic_api import KEY_A, KEY_B, SyntheticAPI
from synthetic_hosted import fixture


async def check_ranked_queries(client: Client, server_id: str) -> None:
    expected = {
        "101": ("abc123", "SELECT * FROM example_orders WHERE id = ?"),
        "202": ("def456", "SELECT amount FROM example_payments WHERE account_id = ?"),
    }
    query = await client.call_tool("query_evidence", {"server_id": server_id, "period": "10m"})
    assert not query.is_error
    data = query.structured_content["data"]
    assert data["window_bounds"] == "[start_time,end_time)"
    ranked, raw_only = data["items"]
    assert (ranked["query_id"], ranked["query"]) == expected[server_id]
    assert ranked["query_status"] == "available" and ranked["sum_time_sec"] == 3
    assert raw_only["query_id"] == f"raw-{server_id}" and raw_only["calls"] == 2
    assert raw_only["query"] is None and raw_only["query_status"] == "unavailable"
    assert "raw-only-canary" not in query.model_dump_json()

    other_id = "202" if server_id == "101" else "101"
    denied = await client.call_tool("query_evidence", {"server_id": other_id, "period": "10m"})
    assert denied.is_error
    assert denied.structured_content["error"]["code"] in {"forbidden", "not_found_or_inaccessible"}
    for value in expected[other_id]:
        assert value not in query.model_dump_json() and value not in denied.model_dump_json()


@asynccontextmanager
async def listener(api: SyntheticAPI) -> Any:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(fixture(api), access_log=False, log_level="error"))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("Synthetic local listener exited")
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=5)
        sock.close()


async def exercise() -> dict[str, Any]:
    modes = ["legacy", "2026-07-28"]
    api = SyntheticAPI()
    async with listener(api) as url:
        for mode in modes:
            async with httpx2.AsyncClient(
                headers={"Host": "mcp.example.invalid", "Authorization": "Bearer " + KEY_A}
            ) as http:
                async with Client(
                    streamable_http_client(url, http_client=http), mode=mode
                ) as client:
                    assert len((await client.list_tools()).tools) == 10
                    assert len((await client.list_prompts()).prompts) == 4
                    assert (await client.read_resource("releem://reference")).contents
                    selected = await client.call_tool("servers", {"limit": 1})
                    assert selected.structured_content["data"]["items"][0]["id"] == "101"
                    findings = await client.call_tool("server_findings", {"server_id": "101"})
                    assert not findings.is_error
                    assert findings.structured_content["status"] == "partial"
                    assert findings.structured_content["warnings"]
                    await check_ranked_queries(client, "101")
                    for bounds in (
                        {"period_days": 7},
                        {"start_date": "2026-11-11T10:00:00Z", "end_date": "2026-11-11T10:10:00Z"},
                    ):
                        query = await client.call_tool(
                            "query_evidence", {"server_id": "101", **bounds}
                        )
                        assert not query.is_error, query.model_dump_json()
                        assert (
                            query.structured_content["data"]["window_bounds"]
                            == "[start_time,end_time)"
                        )
                        if "period_days" in bounds:
                            assert query.structured_content["status"] == "no_data"
                            assert query.structured_content["data"]["items"] == []
                    ambiguous = await client.call_tool(
                        "query_evidence", {"server_id": "101", "period": "1d", "period_days": 7}
                    )
                    assert ambiguous.is_error
                    assert "private-reference" not in findings.model_dump_json()
                    recs = await client.call_tool("recommendations", {"server_id": "101"})
                    assert not recs.is_error
                    detail = await client.call_tool(
                        "recommendations",
                        {"server_id": "101", "view": "detail", "recommendation_id": 601},
                    )
                    assert not detail.is_error
                    assert "workflow_status_only" in detail.model_dump_json()
                    prompt = await client.get_prompt(
                        "explain_recommendation", {"server_id": "101", "recommendation_id": "601"}
                    )
                    assert prompt.messages
                    denied = await client.call_tool("server_findings", {"server_id": "202"})
                    assert denied.is_error or denied.structured_content["status"] == "partial"
                    assert "synthetic-db-202" not in denied.model_dump_json()
                    assert not any(
                        key == KEY_A and "/servers/202" in path for key, path in api.calls
                    )
                    assert (await client.call_tool("execute_change", {})).is_error
            # Independent customer uses the same URL and a distinct per-request credential.
            async with httpx2.AsyncClient(
                headers={"Host": "mcp.example.invalid", "Authorization": "Bearer " + KEY_B}
            ) as http:
                async with Client(
                    streamable_http_client(url, http_client=http), mode=mode
                ) as client:
                    await check_ranked_queries(client, "202")
                    assert not any(
                        key == KEY_B and "/servers/101" in path for key, path in api.calls
                    )
            async with httpx2.AsyncClient(headers={"Host": "mcp.example.invalid"}) as http:

                async def rpc(key: str) -> httpx2.Response:
                    return await http.post(
                        url,
                        headers={
                            "Authorization": "Bearer " + key,
                            "Accept": "application/json, text/event-stream",
                            "MCP-Protocol-Version": "2025-11-25",
                        },
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {"name": "servers", "arguments": {}},
                        },
                    )

                b = await rpc(KEY_B)
                assert b.json()["result"]["structuredContent"]["data"]["items"][0]["id"] == "202"
                api.revoked.add(KEY_A)
                assert (await rpc(KEY_A)).status_code == 401
                assert (await rpc(KEY_B)).status_code == 200
                api.revoked.clear()
                assert (await rpc("invalid")).status_code == 401
                api.unavailable = True
                assert (await rpc(KEY_A)).status_code == 503
                api.unavailable = False
    return {
        "protocol_modes": modes,
        "two_account_isolation": True,
        "revocation": True,
        "missing_evidence_visible": True,
        "recommendation_workflow": True,
        "current_query_windows": True,
        "normalized_queries": True,
        "dependency_failure_visible": True,
        "data": "synthetic only",
        "transport": "loopback TCP",
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(exercise())))
