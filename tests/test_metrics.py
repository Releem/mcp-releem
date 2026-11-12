import asyncio

import httpx2
import pytest
from test_diagnostics import run_with
from test_foundation import module

WINDOW = {"start_time": "2026-11-10T16:00:00Z", "end_time": "2026-11-10T17:00:00Z"}


@pytest.fixture
def metrics():
    return {
        "/v1/servers/101/metrics": {
            "metrics": [
                dict(
                    itemid=7,
                    name="Questions",
                    units="q/s",
                    value_type=0,
                    description="Statement rate",
                )
            ]
        },
        "/v1/servers/101/metrics/byName/Questions": {
            "metric_name": "Questions",
            "data": [{"timestamp": "2026-11-10T16:30:00Z", "value": 0}],
            "total_points": 1,
        },
        "/v1/servers/101/metrics/byId/7": {
            "metric_name": "Questions",
            "data": [],
            "total_points": 0,
        },
    }


def test_series_retains_units_zero_and_effective_window(metrics):
    result, calls = run_with(
        metrics, lambda s: s.metrics("101", view="series", metric_name="Questions", **WINDOW)
    )
    assert result.status == "ok"
    assert result.data["series"][0]["value"] == 0
    assert result.data["metric"]["units"] == "q/s"
    assert len(calls) == 2
    assert calls[1].url.params["start_time"].endswith("+00:00")
    assert result.coverage.returned == 1


def test_series_by_id_empty_and_default_window(metrics):
    result, calls = run_with(metrics, lambda s: s.metrics("101", view="series", itemid=7))
    assert result.status == "no_data"
    assert calls[1].url.params["start_time"] == "2026-11-10T17:00:00+00:00"
    assert calls[1].url.params["end_time"] == "2026-11-10T18:00:00+00:00"


@pytest.mark.parametrize(
    "args",
    [
        dict(view="series"),
        dict(view="series", itemid=7, metric_name="Questions"),
        dict(view="series", metric_name="../Questions"),
        dict(view="series", itemid=7, aggregation="avg"),
        dict(view="series", itemid=7, interval="0m"),
        dict(view="series", itemid=7, start_time="2026-11-10T00:00:00"),
        dict(
            view="series",
            itemid=7,
            start_time="2026-01-01T00:00:00Z",
            end_time="2026-03-01T00:00:00Z",
        ),
        dict(view="compare"),
        dict(view="catalog", itemid=7),
    ],
)
def test_metric_invalid_input_never_calls_api(metrics, args):
    result, calls = run_with(metrics, lambda s: s.metrics("101", **args))
    assert result.error.code == "invalid_arguments"
    assert not calls


@pytest.mark.parametrize(
    "change",
    [
        dict(metric_name="Other"),
        dict(total_points=3),
        dict(data=[dict(timestamp="bad", value=1)], total_points=1),
        dict(data=[dict(timestamp="2026-11-09T00:00:00Z", value=1)], total_points=1),
    ],
)
def test_metric_series_rejects_inconsistent_evidence(metrics, change):
    metrics["/v1/servers/101/metrics/byName/Questions"].update(change)
    result, _ = run_with(
        metrics, lambda s: s.metrics("101", view="series", metric_name="Questions", **WINDOW)
    )
    assert result.error.code == "invalid_source_data"


def test_large_series_is_rejected_without_silent_sampling(metrics):
    row = metrics["/v1/servers/101/metrics/byName/Questions"]
    row["data"] *= 501
    row["total_points"] = 501
    result, _ = run_with(
        metrics, lambda s: s.metrics("101", view="series", metric_name="Questions", **WINDOW)
    )
    assert result.error.code == "result_too_large"
    assert result.data is None


def test_trends_failure_is_not_retried_as_raw(metrics):
    metrics["/v1/servers/101/metrics/byName/Questions"] = httpx2.Response(
        400, json={"error": {"code": "trends_not_available", "message": "synthetic-secret"}}
    )
    result, calls = run_with(
        metrics,
        lambda s: s.metrics(
            "101",
            view="series",
            metric_name="Questions",
            use_trends=True,
            aggregation="avg",
            **WINDOW,
        ),
    )
    assert result.status == "error"
    assert result.error.code == "trends_not_available"
    assert "synthetic-secret" not in result.model_dump_json()
    assert len(calls) == 2


@pytest.mark.parametrize(
    "baseline,units,reason",
    [
        (0, "q/s", "zero_baseline"),
        (None, "q/s", "missing_data"),
        (2, "ms", "unit_mismatch"),
        (2, "q/s", None),
    ],
)
def test_compare_hourly_trends_preserves_null_zero_and_units(baseline, units, reason):
    config, api, core = module("config"), module("api.client"), module("core.diagnostics")
    calls = []

    def handler(req):
        calls.append(req)
        current = req.url.params["start_time"].startswith("2026-11-10T16")
        return httpx2.Response(
            200,
            json={
                "start_time": req.url.params["start_time"],
                "end_time": req.url.params["end_time"],
                "metrics": [
                    dict(
                        itemid=7,
                        name="Questions",
                        units="q/s" if current else units,
                        avg=4 if current else baseline,
                        min=None,
                        max=None,
                    )
                ],
            },
        )

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        async with api.ReleemClient(settings, transport=httpx2.MockTransport(handler)) as client:
            return await core.Diagnostics(client).metrics(
                "101", view="compare", metric_names=["Questions"], **WINDOW
            )

    result = asyncio.run(run())
    row = result.data["items"][0]
    assert row["delta_unavailable_reason"] == reason
    assert row["percent_change"] == (100 if reason is None else None)
    assert "hourly" in result.data["aggregation_basis"]
    assert result.data["window_bounds"] == "[start_time,end_time)"
    assert result.data["baseline_window"]["end_time"] == result.data["current_window"]["start_time"]
    assert calls[1].url.params["start_time"].startswith("2026-11-10T15")


def test_series_budget_returns_error_instead_of_clipping_points(metrics):
    row = metrics["/v1/servers/101/metrics/byName/Questions"]
    row["data"] *= 100
    row["total_points"] = 100
    result, _ = run_with(
        metrics,
        lambda s: s.metrics("101", view="series", metric_name="Questions", **WINDOW),
        budget=4096,
    )
    assert result.error.code == "result_too_large"
    assert result.data is None
    assert len(result.model_dump_json().encode()) <= 4096


@pytest.mark.parametrize(
    "timestamp,interpreted_utc",
    [("2026-11-10T16:30:00", True), ("2026-11-10T19:30:00+03:00", False)],
)
def test_series_time_normalizes_to_utc_with_visible_source_semantics(
    metrics, timestamp, interpreted_utc
):
    row = metrics["/v1/servers/101/metrics/byName/Questions"]
    row["data"][0]["timestamp"] = timestamp
    result, _ = run_with(
        metrics, lambda s: s.metrics("101", view="series", metric_name="Questions", **WINDOW)
    )
    assert result.status == "ok"
    assert result.data["series"] == [{"timestamp": "2026-11-10T16:30:00+00:00", "value": 0}]
    warnings = [warning for warning in result.warnings if warning.code == "source_timezone_utc"]
    assert bool(warnings) == interpreted_utc
    if interpreted_utc:
        assert "UTC" in warnings[0].message


def test_missing_catalog_target_blocks_series_read(metrics):
    result, calls = run_with(metrics, lambda s: s.metrics("101", view="series", itemid=8))
    assert result.error.code == "metric_not_available"
    assert len(calls) == 1


def test_new_tools_dispatch_with_typed_inputs_and_never_accept_writes(metrics):
    from mcp import Client

    config, api, core, surface = (
        module("config"),
        module("api.client"),
        module("core.diagnostics"),
        module("server"),
    )
    calls = []

    def handler(req):
        calls.append(req)
        return httpx2.Response(
            200,
            json={"items": []}
            if req.url.path.endswith("/configurations")
            else metrics[req.url.path],
        )

    async def run():
        settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        async with api.ReleemClient(settings, transport=httpx2.MockTransport(handler)) as client:
            async with Client(
                surface.build_server(settings, service=core.Diagnostics(client))
            ) as mcp:
                for name, args in [
                    ("configurations", {"view": "latest"}),
                    ("metrics", {"view": "series", "itemid": 7}),
                ]:
                    result = await mcp.call_tool(name, {"server_id": "101", **args})
                    assert not result.is_error
                for name, args in [
                    ("configurations", {"apply": True}),
                    ("metrics", {"view": "catalog", "itemid": 7}),
                ]:
                    result = await mcp.call_tool(name, {"server_id": "101", **args})
                    assert result.is_error
                assert len(calls) == 3
                assert all(req.method == "GET" for req in calls)

    asyncio.run(run())


def test_extreme_offset_time_is_a_structured_input_error_without_api_calls():
    config, surface = module("config"), module("server")
    settings = config.Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})

    async def run():
        for value in ["0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"]:
            result = await surface.build_server(settings).call_tool(
                "metrics",
                {
                    "server_id": "101",
                    "view": "series",
                    "itemid": 7,
                    "start_time": value,
                    "end_time": "2026-11-10T17:00:00Z",
                },
            )
            assert result.structured_content["error"]["code"] == "invalid_arguments"

    asyncio.run(run())
