import asyncio
import importlib
import json

import httpx2
import pytest


def module(name):
    try:
        return importlib.import_module("mcp_releem." + name)
    except ModuleNotFoundError:
        pytest.fail(f"Missing implementation: {name}")


def test_configuration_requires_secret_without_echoing_it(tmp_path):
    config = module("config")
    with pytest.raises(ValueError, match="token"):
        config.Settings.from_env({})
    settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
    assert settings.base_url == "https://api2.dev.releem.com"
    assert "synthetic-secret" not in repr(settings)
    assert "synthetic-secret" not in json.dumps(settings.redacted())
    path = tmp_path / "token"
    path.write_text("synthetic-secret\n")
    assert config.Settings.from_env({"RELEEM_API_TOKEN_FILE": str(path)}).token.get_secret_value()
    for env in [
        {"RELEEM_API_TOKEN": "a", "RELEEM_API_TOKEN_FILE": str(path)},
        {"RELEEM_API_TOKEN": "a", "RELEEM_MCP_READ_ONLY": "false"},
        {"RELEEM_API_TOKEN": "a", "RELEEM_API_BASE_URL": "https://user:pass@example.com"},
        {"RELEEM_API_TOKEN": "a", "RELEEM_API_BASE_URL": "http://example.com"},
        {"RELEEM_API_TOKEN": "a", "RELEEM_MCP_PROFILE": "hosted"},
        {"RELEEM_API_TOKEN": "a", "RELEEM_MCP_UNKNOWN": "x"},
    ]:
        with pytest.raises(ValueError):
            config.Settings.from_env(env)


def test_api_allowlist_parameters_and_sanitized_errors():
    config = module("config")
    api = module("api.client")
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["Releem-Secret-Key"] == "synthetic-secret"
        return httpx2.Response(401, json={"error": {"message": "synthetic-secret"}})

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        async with api.ReleemClient(settings, transport=httpx2.MockTransport(handler)) as client:
            for operation, params in [
                ("tasks_create", {"server_id": "101"}),
                ("server", {"server_id": "../202"}),
                ("server", {"server_id": "00101"}),
                ("recommendations", {"server_id": "101", "type": 1}),
            ]:
                with pytest.raises(api.APIError):
                    await client.read(operation, **params)
            assert calls == []
            with pytest.raises(api.APIError) as error:
                await client.read("server", server_id="101")
            assert error.value.code == "upstream_auth_failed"
            assert "synthetic-secret" not in str(error.value)
            assert len(calls) == 1

    asyncio.run(run())


@pytest.mark.parametrize("payload", [{"not": "a list"}, [{"id": "202"}]])
def test_server_ownership_and_invalid_shapes(payload):
    config = module("config")
    api = module("api.client")

    async def run():
        async with api.ReleemClient(
            config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"}),
            transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=payload)),
        ) as client:
            with pytest.raises(api.APIError, match="source"):
                await client.read("server", server_id="101")

    asyncio.run(run())


def test_response_body_limit_and_redirect_refusal():
    config = module("config")
    api = module("api.client")

    async def run():
        for response, code in [
            (httpx2.Response(200, content=b"x" * (5 * 1024 * 1024 + 1)), "response_too_large"),
            (
                httpx2.Response(302, headers={"Location": "https://foreign.example"}),
                "redirect_refused",
            ),
            (httpx2.Response(200, content=b"not json"), "invalid_source_data"),
        ]:
            async with api.ReleemClient(
                config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"}),
                transport=httpx2.MockTransport(lambda _, value=response: value),
            ) as client:
                with pytest.raises(api.APIError) as error:
                    await client.read("server", server_id="101")
                assert error.value.code == code

    asyncio.run(run())


def test_wrong_child_id_and_422_validation_are_not_success():
    config = module("config")
    api = module("api.client")
    model = {
        "id": 602,
        "server_id": "101",
        "source_type": "configuration",
        "source_id": "1",
        "source_subtype": "example",
        "title": "Example",
        "summary": "Example",
        "status": "new",
    }

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        for response, code in [
            (httpx2.Response(200, json=model), "invalid_source_data"),
            (
                httpx2.Response(422, json={"error": {"code": "validation_error"}}),
                "invalid_arguments",
            ),
        ]:
            async with api.ReleemClient(
                settings,
                transport=httpx2.MockTransport(lambda _, value=response: value),
            ) as client:
                with pytest.raises(api.APIError) as error:
                    await client.read("recommendation", server_id="101", recommendation_id=601)
                assert error.value.code == code

    asyncio.run(run())


def test_concurrency_is_bounded_and_cancellation_releases_capacity():
    config = module("config")
    api = module("api.client")

    async def run():
        active = 0
        peak = 0

        async def handler(_):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0.01)
                return httpx2.Response(200, json={"id": "101"})
            finally:
                active -= 1

        async with api.ReleemClient(
            config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"}),
            transport=httpx2.MockTransport(handler),
        ) as client:
            await asyncio.gather(*(client.read("server", server_id="101") for _ in range(12)))
            assert peak <= 4
            pending = [
                asyncio.create_task(client.read("server", server_id="101")) for _ in range(4)
            ]
            await asyncio.sleep(0)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            result = await asyncio.wait_for(client.read("server", server_id="101"), 1)
            assert result.id == "101"

    asyncio.run(run())


@pytest.mark.parametrize("number", [b"NaN", b"Infinity", b"1e999"])
def test_nonstandard_json_numbers_are_rejected(number):
    config = module("config")
    api = module("api.client")

    async def run():
        async with api.ReleemClient(
            config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"}),
            transport=httpx2.MockTransport(
                lambda _: httpx2.Response(
                    200,
                    content=b'{"id":"101","releem_score":' + number + b"}",
                )
            ),
        ) as client:
            with pytest.raises(api.APIError, match="source"):
                await client.read("server", server_id="101")

    asyncio.run(run())


@pytest.mark.parametrize(
    "instance_type",
    [
        "1",
        None,
        {"id": "1", "name": "On-premise"},
        {"id": 101, "name": None},
        {"id": "999", "opaque": {"token": "synthetic-secret"}},
    ],
)
def test_inventory_preserves_instance_type_code_objects(instance_type):
    models = module("api.models")
    server = models.Server.model_validate({"id": "101", "instance_type": instance_type})
    expected = instance_type
    if isinstance(instance_type, dict):
        expected = {"id": instance_type["id"], "name": instance_type.get("name")}
    assert server.model_dump()["instance_type"] == expected


@pytest.mark.parametrize(
    "instance_type", [{}, {"id": True}, {"id": 1.5}, {"id": None}, {"id": "1", "name": []}, []]
)
def test_inventory_rejects_malformed_instance_type_code_objects(instance_type):
    models = module("api.models")
    with pytest.raises(ValueError):
        models.Server.model_validate({"id": "101", "instance_type": instance_type})
