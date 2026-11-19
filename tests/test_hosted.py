import asyncio

import pytest
from hosted_helpers import KEY_A, KEY_B, HostedHarness, rpc
from test_foundation import module


def test_hosted_config_has_no_global_credential_fallback():
    settings = module("hosted.config").HostedSettings
    env = {
        "RELEEM_MCP_PROFILE": "hosted",
        "RELEEM_MCP_PUBLIC_URL": "https://mcp.example.invalid/mcp",
    }
    assert settings.from_env(env).redacted()["profile"] == "hosted"
    assert settings.from_env(env).base_url == "https://api2.releem.com"
    previous = "https://api2.dev.releem.com"
    assert settings.from_env({**env, "RELEEM_API_BASE_URL": previous}).base_url == previous
    for change in [
        {"RELEEM_API_TOKEN": KEY_A},
        {"RELEEM_SECRET_KEY": KEY_A},
        {"RELEEM_API_TOKEN_FILE": "/private/token"},
        {"RELEEM_MCP_PUBLIC_URL": "http://evil.invalid/mcp"},
        {"RELEEM_MCP_PUBLIC_URL": "https://user:pass@evil.invalid/mcp"},
        {"RELEEM_MCP_PUBLIC_URL": "https://mcp.example.invalid/other"},
        {"RELEEM_MCP_PROFILE": "local"},
        {"RELEEM_MCP_READ_ONLY": "false"},
        {"RELEEM_MCP_UNRECOGNIZED": "x"},
    ]:
        with pytest.raises(ValueError):
            settings.from_env({**env, **change})


def test_missing_invalid_and_revoked_keys_never_reach_mcp():
    async def run():
        h = HostedHarness()
        async with h.client() as client:
            for key in [None, "bad key", "invalid"]:
                r = await rpc(client, key=key)
                assert r.status_code == 401
                assert "tools" not in r.text
            good = await rpc(client)
            assert good.status_code == 200 and len(good.json()["result"]["tools"]) == 10
            h.revoked.add(KEY_A)
            revoked = await rpc(client)
            assert revoked.status_code == 401
            assert KEY_A not in revoked.text

    asyncio.run(run())


def test_hosted_requests_cannot_cross_credentials_or_authorized_server_scope():
    async def run():
        h = HostedHarness()
        async with h.client() as client:
            a, b = await asyncio.gather(
                *(
                    rpc(
                        client,
                        "tools/call",
                        {"name": "servers", "arguments": {"limit": 1}},
                        key=key,
                    )
                    for key in [KEY_A, KEY_B]
                )
            )
            typed = a.json()["result"]["structuredContent"]["data"]["items"][0]
            legacy = b.json()["result"]["structuredContent"]["data"]["items"][0]
            assert typed["id"] == "101" and typed["instance_type"] == {
                "id": "1",
                "name": "On-premise",
            }
            assert legacy["id"] == "202" and legacy["instance_type"] == "1"
            denied = await rpc(
                client,
                "tools/call",
                {
                    "name": "server_findings",
                    "arguments": {"server_id": "202", "sections": ["summary"]},
                },
            )
            assert denied.json()["result"]["isError"] is True
            assert "customer-202" not in denied.text
            assert not any(
                key == KEY_A and path.startswith("/v1/servers/202") for key, path in h.calls
            )
            assert KEY_A not in a.text and KEY_B not in b.text

    asyncio.run(run())


def test_all_protected_methods_authenticate_and_static_outputs_do_not_grant_access():
    async def run():
        h = HostedHarness()
        async with h.client() as client:
            for method, params in [
                ("prompts/list", {}),
                ("prompts/get", {"name": "why_database_slow", "arguments": {"server_id": "101"}}),
                ("resources/read", {"uri": "releem://reference"}),
            ]:
                assert (await rpc(client, method, params, key=None)).status_code == 401
                assert (await rpc(client, method, params)).status_code == 200
            denied = await rpc(client, "tools/call", {"name": "execute_change", "arguments": {}})
            assert denied.json()["result"]["isError"] is True
            invalid = await rpc(
                client, "tools/call", {"name": "servers", "arguments": {"bad": KEY_A}}
            )
            assert KEY_A not in invalid.text
            health = await client.get("/healthz")
            assert health.status_code == 200 and "servers" not in health.text

    asyncio.run(run())


def test_host_origin_session_and_body_boundaries_fail_closed():
    async def run():
        h = HostedHarness()
        async with h.client() as client:
            for headers in [
                {"Host": "evil.invalid"},
                {"Origin": "https://evil.invalid"},
                {"Mcp-Session-Id": "customer-B"},
            ]:
                response = await rpc(client, **headers)
                assert response.status_code in {400, 403}
            assert not h.calls
            oversized = await client.post(
                "/mcp", content=b"x" * 262145, headers={"Authorization": "Bearer " + KEY_A}
            )
            assert oversized.status_code == 413
            assert not h.calls

    asyncio.run(run())


@pytest.mark.parametrize("status,expected", [(403, 403), (429, 429), (500, 503)])
def test_validation_outages_are_not_authorized(status, expected):
    async def run():
        h = HostedHarness()
        h.failure = status
        async with h.client() as client:
            response = await rpc(client)
            assert response.status_code == expected
            assert KEY_A not in response.text

    asyncio.run(run())


def test_per_key_rate_and_global_concurrency_are_bounded():
    async def run():
        h = HostedHarness(RELEEM_MCP_REQUESTS_PER_MINUTE="1")
        async with h.client() as client:
            assert (await rpc(client)).status_code == 200
            assert (await rpc(client)).status_code == 429
            assert (await rpc(client, key=KEY_B)).status_code == 200
        h = HostedHarness(
            RELEEM_MCP_MAX_CONCURRENT_REQUESTS="1", RELEEM_MCP_PER_KEY_CONCURRENCY="1"
        )
        async with h.client() as client:
            slot = h.app.limits.acquire(KEY_A)
            assert slot is not None
            assert (await rpc(client, key=KEY_B)).status_code == 429
            h.app.limits.release(slot)
            h.block = asyncio.Event()
            pending = asyncio.create_task(rpc(client))
            while not h.calls or h.app.auth_stage.active == 0:
                await asyncio.sleep(0)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            h.block = None
            assert (await rpc(client, key=KEY_B)).status_code == 200

    asyncio.run(run())


def test_unknown_resource_never_echoes_or_logs_caller_values(caplog):
    async def run():
        h = HostedHarness()
        async with h.client() as client:
            response = await rpc(client, "resources/read", {"uri": "releem://" + KEY_A})
            assert KEY_A not in response.text
            assert KEY_A not in caplog.text

    asyncio.run(run())


def test_chunked_body_limit_precedes_upstream_authentication():
    async def run():
        h = HostedHarness()

        async def body():
            yield b"x" * 200000
            yield b"x" * 100000

        async with h.client() as client:
            response = await client.post(
                "/mcp", content=body(), headers={"Authorization": "Bearer " + KEY_A}
            )
            assert response.status_code == 413
            assert not h.calls

    asyncio.run(run())


def test_extreme_content_length_does_not_escape_boundary():
    async def run():
        h = HostedHarness()
        async with h.client() as client:
            response = await rpc(client, **{"Content-Length": "9" * 4301})
            assert response.status_code == 413
            assert not h.calls

    asyncio.run(run())
