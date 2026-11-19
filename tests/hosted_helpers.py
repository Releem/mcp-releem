"""Synthetic ASGI hosted harness; never reaches Releem or a real key."""

import asyncio
from contextlib import asynccontextmanager

import httpx2
from test_foundation import module

KEY_A = "synthetic-key-A"
KEY_B = "synthetic-key-B"
PUBLIC_URL = "https://mcp.example.invalid/mcp"


class HostedHarness:
    def __init__(self, **env):
        self.calls = []
        self.revoked = set()
        self.failure = None
        self.block = None
        settings = module("hosted.config").HostedSettings.from_env(
            {"RELEEM_MCP_PROFILE": "hosted", "RELEEM_MCP_PUBLIC_URL": PUBLIC_URL, **env}
        )
        self.app = module("hosted.app").create_hosted_app(
            settings, transport=httpx2.MockTransport(self.handler)
        )

    async def handler(self, request):
        key = request.headers.get("Releem-Secret-Key")
        self.calls.append((key, request.url.path))
        assert "authorization" not in request.headers
        if self.block is not None:
            await self.block.wait()
        if self.failure:
            return httpx2.Response(self.failure)
        if key not in {KEY_A, KEY_B} or key in self.revoked:
            return httpx2.Response(401)
        await asyncio.sleep(0)
        sid = "101" if key == KEY_A else "202"
        if request.url.path == "/v1/servers":
            return httpx2.Response(
                200,
                json=[
                    {
                        "id": sid,
                        "server_name": "customer-" + sid,
                        "instance_type": {"id": "1", "name": "On-premise"} if key == KEY_A else "1",
                    }
                ],
            )
        if request.url.path == "/v1/servers/" + sid:
            return httpx2.Response(200, json={"id": sid, "server_name": "customer-" + sid})
        if request.url.path == f"/v1/servers/{sid}/details":
            return httpx2.Response(
                200, json={"id": sid, "health_checks": {}, "security_checks": {}}
            )
        return httpx2.Response(404)

    @asynccontextmanager
    async def client(self):
        async with self.app.inner.router.lifespan_context(self.app.inner):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=self.app), base_url="https://mcp.example.invalid"
            ) as client:
                yield client


async def rpc(client, method="tools/list", params=None, key=KEY_A, **headers):
    values = {
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
        **headers,
    }
    if key is not None:
        values["Authorization"] = "Bearer " + key
    return await client.post(
        "/mcp",
        headers=values,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )
