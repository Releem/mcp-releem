import asyncio

from hosted_helpers import KEY_A, HostedHarness, rpc


def test_slow_unauthenticated_bodies_do_not_take_customer_work_slots():
    async def run():
        h = HostedHarness()
        blocked = asyncio.Event()
        entered = 0

        async def receive():
            nonlocal entered
            entered += 1
            await blocked.wait()
            return {"type": "http.disconnect"}

        async def send(_):
            pass

        scope = {
            "type": "http",
            "path": "/mcp",
            "method": "POST",
            "query_string": b"",
            "headers": [
                (b"host", b"mcp.example.invalid"),
                (b"authorization", b"Bearer invented-key"),
            ],
        }
        tasks = [
            asyncio.create_task(
                h.app(
                    {
                        **scope,
                        "headers": [
                            (b"host", b"mcp.example.invalid"),
                            (b"authorization", f"Bearer invented-key-{i // 4}".encode()),
                        ],
                    },
                    receive,
                    send,
                )
            )
            for i in range(16)
        ]
        try:
            while entered < 16:
                await asyncio.sleep(0)
            async with h.client() as client:
                assert (await rpc(client)).status_code == 200
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(run())


def test_invalid_keys_do_not_charge_customer_quota():
    async def run():
        h = HostedHarness()
        h.app.limits.global_bucket.requests = 599
        async with h.client() as client:
            assert (await rpc(client, key="invented-key")).status_code == 401
            assert (await rpc(client)).status_code == 200

    asyncio.run(run())


def test_unknown_protocol_method_does_not_echo_caller_value(caplog):
    async def run():
        h = HostedHarness()
        async with h.client() as client:
            response = await rpc(client, KEY_A)
            assert KEY_A not in response.text
            assert KEY_A not in caplog.text

    asyncio.run(run())


def test_body_deadline_is_short_and_releases_stage(monkeypatch):
    from test_foundation import module

    monkeypatch.setattr(module("hosted.ingress"), "BODY_TIMEOUT", 0.01)

    async def run():
        h = HostedHarness()
        messages = []

        async def receive():
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "path": "/mcp",
            "method": "POST",
            "query_string": b"",
            "headers": [(b"host", b"mcp.example.invalid"), (b"authorization", b"Bearer invented")],
        }
        await h.app(scope, receive, send)
        assert messages[0]["status"] == 408
        assert h.app.body_stage.active == 0
        assert h.app.limits.global_bucket.active == 0
        assert not h.calls

    asyncio.run(run())
