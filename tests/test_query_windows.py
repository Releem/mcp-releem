"""Current query period contract and legacy MCP alias regressions."""

import pytest
from pydantic import ValidationError

from mcp_releem.core.diagnostic_inputs import instant
from mcp_releem.core.queries import QueryDiagnostics
from mcp_releem.core.query_inputs import QueryInput
from mcp_releem.core.query_windows import check_window


@pytest.mark.parametrize(
    ("arguments", "period"),
    [
        ({}, "1d"),
        ({"period_days": 7}, "7d"),
        ({"period": "10m"}, "10m"),
        ({"period": "2h"}, "2h"),
        ({"period": "7"}, "7d"),
    ],
)
def test_outbound_period(arguments, period):
    request = QueryInput(server_id="101", **arguments)
    params = QueryDiagnostics(None).parameters(request)
    assert params["period"] == period
    assert "period_days" not in params


@pytest.mark.parametrize(
    "arguments",
    [
        {"period": "0"},
        {"period": "01d"},
        {"period": "-1h"},
        {"period": "1w"},
        {"period": True},
        {"period": 1},
        {"period": "91d"},
        {"period": "99999999999999999d"},
        {"period_days": True},
        {"period_days": 7.0},
        {"period": "1d", "period_days": 1},
        {"end_date": "2026-11-11T00:00:00Z"},
        {"start_date": "2026-11-11T00:00:00"},
        {"start_date": "2026-11-11T00:00:00.1Z"},
        {"start_date": "2026-11-11T00:00:00Z", "end_date": "2026-11-11T00:00:00Z"},
        {"start_date": "2026-11-11T00:00:00Z", "end_date": "2027-11-11T00:00:00Z"},
        {"view": "optimizations", "period": "1d"},
    ],
)
def test_invalid_window_input(arguments):
    with pytest.raises(ValidationError):
        QueryInput(server_id="101", **arguments)


def test_explicit_end_overrides_valid_period():
    request = QueryInput(
        server_id="101",
        period="7d",
        start_date="2026-11-11T03:00:00+03:00",
        end_date="2026-11-11T00:10:00Z",
    )
    check_window(request, instant("2026-11-11T00:00:00Z"), instant("2026-11-11T00:10:00Z"))
    with pytest.raises(ValueError):
        check_window(request, instant("2026-11-11T00:00:00Z"), instant("2026-11-11T00:11:00Z"))


def test_rolling_duration_must_match_without_clock_assumption():
    request = QueryInput(server_id="101", period="10m")
    check_window(request, instant("2020-01-01T00:00:00Z"), instant("2020-01-01T00:10:00Z"))
    with pytest.raises(ValueError):
        check_window(request, instant("2020-01-01T00:00:00Z"), instant("2020-01-02T00:00:00Z"))


@pytest.mark.parametrize(
    "code",
    [
        "invalid_period",
        "invalid_start_date",
        "invalid_end_date",
        "invalid_time_range",
        "invalid_timezone",
        "invalid_sort_by",
        "invalid_order",
        "invalid_query_filter",
    ],
)
def test_query_errors_are_fixed_and_private(code):
    import asyncio

    import httpx2

    from mcp_releem.api.client import APIError, ReleemClient
    from mcp_releem.config import Settings

    async def run():
        settings = Settings.from_env({"RELEEM_API_TOKEN": "synthetic-secret"})
        transport = httpx2.MockTransport(
            lambda _: httpx2.Response(400, json={"error": {"code": code, "message": "private SQL"}})
        )
        async with ReleemClient(settings, transport=transport) as client:
            with pytest.raises(APIError) as caught:
                await client.read("query_analytics", server_id="101", period="1d")
            assert caught.value.code == code
            assert "private SQL" not in str(caught.value)

    asyncio.run(run())


def test_window_mismatch_is_sanitized_error(query_records):
    from test_diagnostics import run_with

    result, _ = run_with(query_records, lambda service: service.query_evidence("101", period="7d"))
    assert result.status == "error"
    assert result.error.code == "invalid_source_data"
    assert result.data is None
    assert "private" not in result.model_dump_json()


def test_end_override_warning(query_records):
    from test_diagnostics import run_with

    result, _ = run_with(
        query_records,
        lambda service: service.query_evidence(
            "101", period="7d", start_date="2026-11-09T00:00:00Z", end_date="2026-11-10T00:00:00Z"
        ),
    )
    assert result.status == "ok"
    assert "period_overridden" in {warning.code for warning in result.warnings}


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-11T00:00:00+00:60",
        "2026-11-11T00:00:00.0000001Z",
        "2026-11-11T00:00:00+01:00:01",
        "2026-11-11T00:00Z",
    ],
)
def test_dates_reject_lossy_or_nonstandard_offsets(value):
    with pytest.raises(ValidationError):
        QueryInput(server_id="101", start_date=value)
    with pytest.raises(ValidationError):
        QueryInput(server_id="101", start_date="2026-11-10T00:00:00Z", end_date=value)


def test_source_subsecond_is_not_silently_truncated(query_records):
    from test_diagnostics import run_with

    query_records["/v1/servers/101/query-analytics"]["start_time"] = "2026-11-09T00:00:00.0000001"
    result, _ = run_with(query_records, lambda service: service.query_evidence("101"))
    assert result.status == "error"
    assert result.error.code == "invalid_source_data"
