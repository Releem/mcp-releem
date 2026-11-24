import json

import httpx2
import pytest
from test_diagnostics import run_with
from test_foundation import module

ANALYTICS = "/v1/servers/101/query-analytics"


@pytest.mark.parametrize(
    "suffix",
    [
        "synthetic-secret",
        "-- comment",
        "/* comment */",
        "# comment",
        "\x00",
        "\u0085",
        "\ud800",
        "person@example.invalid",
        "192.0.2.1",
        "api_key=example",
        "Bearer example",
        "猫" * 5500,
    ],
)
def test_screen_full_query_before_returning_any_prefix(query_records, suffix):
    page = query_records[ANALYTICS]
    page["items"][0]["query"] = "SELECT private_canary FROM orders " + " " * 2050 + suffix
    # Escaped surrogate code points can occur in upstream JSON.
    query_records[ANALYTICS] = httpx2.Response(200, content=json.dumps(page).encode())
    result, _ = run_with(query_records, lambda s: s.query_evidence("101"))
    row = result.data["items"][0]
    assert row["query_status"] == "withheld" and row["query"] is None
    assert row["calls"] == 20 and row["query_id"] == "abc123"
    assert result.status == "partial" and result.coverage.omitted == 0
    assert "query_text_limited" in {warning.code for warning in result.warnings}
    assert "private_canary" not in result.model_dump_json()


def test_query_text_byte_budgets_keep_ranked_rows(query_records):
    items = query_records[ANALYTICS]["items"]
    prefix = "SELECT " + "a" * 2039
    sources = [prefix + "猫"] + ["a" * 2048] * 3 + ["abc", "é"]
    items[:] = [dict(items[0], query_id=str(i), query=sql) for i, sql in enumerate(sources)]
    result, _ = run_with(query_records, lambda s: s.query_evidence("101"))
    rows = result.data["items"]
    assert [row["query_id"] for row in rows] == [str(i) for i in range(len(sources))]
    assert [row["query"] for row in rows] == [prefix, *sources[1:4], None, "é"]
    assert [row["query_status"] for row in rows] == [
        "truncated",
        "available",
        "available",
        "available",
        "budget_exhausted",
        "available",
    ]
    assert sum(len((row["query"] or "").encode()) for row in rows) == 8192
    assert result.status == "partial" and result.coverage.omitted == 0


def test_envelope_budget_includes_normalized_queries(query_records):
    items = query_records[ANALYTICS]["items"]
    items[:] = [dict(items[0], query="SELECT " + "x" * 1000, query_id=str(i)) for i in range(4)]
    result, _ = run_with(query_records, lambda s: s.query_evidence("101"), budget=4096)
    assert len(result.model_dump_json().encode()) <= 4096
    assert result.status == "partial" and "items" in result.coverage.truncated_fields
    assert 0 < result.coverage.returned < 4
    assert result.coverage.returned + result.coverage.omitted == 4
    assert result.data["items"][0]["query"] == items[0]["query"]


def test_linked_proposal_omissions_remain_visible(query_records):
    item = {"rid": "run-1", "schema_name": "app db", "query_id": "abc123"}
    query_records["/v1/servers/101/query-optimizations/501"]["recommendations"] = [item] * 21
    result, _ = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="optimization",
            optimization_id=501,
        ),
    )
    assert result.coverage.complete is False
    assert result.coverage.omitted == 1
    assert result.status == "partial"


def test_malformed_plan_node_types_do_not_crash_or_leak_data():
    parser = module("core.plans").summarize_plan
    parsed = parser(json.dumps({"Node Type": {"password": "private-literal"}, "Plan Rows": 3}))
    assert parsed["available"] is True
    assert "private-literal" not in json.dumps(parsed)
    assert parsed["nodes"] == [{"plan_rows": 3}]


def test_query_read_rejects_boolean_period(query_records):
    result, calls = run_with(query_records, lambda s: s.query_evidence("101", period_days=True))
    assert result.status == "error"
    assert calls == []


def test_optimization_rejects_nested_foreign_query_evidence(query_records):
    query_records["/v1/servers/101/query-optimizations/501"]["recommendations"] = [
        {"rid": "run-1", "schema_name": "other-db", "query_id": "foreign-query"},
    ]
    result, _ = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="optimization",
            optimization_id=501,
        ),
    )
    assert result.status == "error"
    assert result.error.code == "invalid_source_data"


def test_plan_minimization_never_claims_complete_evidence(query_records):
    query_records["/v1/servers/101/query-optimizations/501"]["query_explain"] = "stored plan text"
    result, _ = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="optimization",
            optimization_id=501,
        ),
    )
    assert result.status == "partial"
    assert result.coverage.complete is False


@pytest.mark.parametrize("seconds", [1736937000, 0])
def test_optimization_returns_production_status_timestamp_in_seconds(query_records, seconds):
    for record in (
        query_records["/v1/servers/101/query-optimizations"]["items"][0],
        query_records["/v1/servers/101/query-optimizations/501"],
    ):
        record["timestamp_status"] = seconds
    query_records["/v1/servers/101/query-optimizations"]["items"][0]["status"] = {
        "id": "future",
        "name": "Untrusted status",
    }
    query_records["/v1/servers/101/query-optimizations/501"].update(
        status={"id": 5, "name": "Discovered"},
        error_apply_code={"id": 7, "name": "Untrusted error"},
    )
    listing, _ = run_with(query_records, lambda s: s.query_evidence("101", view="optimizations"))
    detail, _ = run_with(
        query_records, lambda s: s.query_evidence("101", view="optimization", optimization_id=501)
    )
    listed = listing.data["items"][0]
    saved = detail.data["optimization"]
    assert listed["status"] == "future" and listed["status_label"] is None
    assert saved["status"] == 5 and saved["status_label"] == "ready"
    for result, row in ((listing, listed), (detail, saved)):
        assert row["timestamp_status"] == seconds
        assert "timestamp_status_ms" not in row
        unavailable = "optimization_status_time_unavailable" in {w.code for w in result.warnings}
        assert unavailable == (seconds == 0)
    assert "Untrusted error" not in detail.model_dump_json()


@pytest.mark.parametrize(
    "timestamps",
    [
        {},
        {"timestamp_status": True},
        {"timestamp_status": None},
        {"timestamp_status": "1736937000"},
        {"timestamp_status_ms": 1736937000000},
    ],
)
def test_optimization_requires_integer_status_seconds(query_records, timestamps):
    record = query_records["/v1/servers/101/query-optimizations/501"]
    record.pop("timestamp_status")
    record.update(timestamps)
    result, _ = run_with(
        query_records, lambda s: s.query_evidence("101", view="optimization", optimization_id=501)
    )
    assert result.error.code == "invalid_source_data"


def test_optimization_ignores_legacy_field_when_production_field_is_present(query_records):
    record = query_records["/v1/servers/101/query-optimizations/501"]
    record["timestamp_status_ms"] = 1
    result, _ = run_with(
        query_records, lambda s: s.query_evidence("101", view="optimization", optimization_id=501)
    )
    row = result.data["optimization"]
    assert row["timestamp_status"] == record["timestamp_status"]
    assert "timestamp_status_ms" not in row
