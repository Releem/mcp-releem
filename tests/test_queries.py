import httpx2
import pytest
from test_diagnostics import run_with


def test_analytics_preserves_window_units_nulls_and_denominator(query_records):
    result, calls = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            schema_name="app db",
            start_date="2026-11-09T03:00:00+03:00",
        ),
    )
    assert result.status == "ok"
    assert result.data["window"] == {
        "start_time": "2026-11-09T00:00:00+00:00",
        "end_time": "2026-11-10T00:00:00+00:00",
    }
    assert calls[0].url.params["start_date"] == "2026-11-09T00:00:00+00:00"
    row = result.data["items"][0]
    assert row["avg_time_ms"] is None and row["sum_time_sec"] == 3
    assert result.data["percentage_denominator"] == "all_queries_matching_filters"
    assert "private_literal" not in result.model_dump_json()
    assert "secret SQL" not in result.model_dump_json()
    assert result.coverage.complete is False  # top query endpoint is capped, no upstream total


def test_proposals_use_scoped_encoded_path_and_only_existing_plan_facts(query_records):
    result, calls = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="proposals",
            schema_name="app db",
            query_id="abc123",
        ),
    )
    assert calls[0].url.raw_path.endswith(b"/app%20db/abc123/recommendations")
    summary = result.data["items"][0]["plan"]
    assert summary["available"] is True
    assert {"node_type": "Seq Scan", "plan_rows": 100} in summary["nodes"]
    assert "private@example.invalid" not in result.model_dump_json()
    assert "private SQL" not in result.model_dump_json()
    assert "CREATE INDEX" not in result.model_dump_json()


def test_optimization_status_is_not_invented_and_missing_plan_is_explicit(query_records):
    listed, _ = run_with(query_records, lambda s: s.query_evidence("101", view="optimizations"))
    row = listed.data["items"][0]
    assert row["status"] == 777 and row["status_label"] is None
    assert row["before_calls"] is None
    detail, _ = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="optimization",
            optimization_id=501,
        ),
    )
    assert detail.data["optimization"]["plan"]["available"] is False
    assert "plan_unavailable" in {w.code for w in detail.warnings}
    assert detail.data["optimization"]["timestamp_status_ms"] == 1794268800123


@pytest.mark.parametrize(
    "kwargs",
    [
        {"period_days": 2},
        {"start_date": "2026-11-10"},
        {"start_date": "2026-11-10T00:00:00"},
        {"view": "proposals", "schema_name": "..", "query_id": "abc123"},
        {"view": "proposals", "schema_name": "app", "query_id": "../../tasks"},
        {"view": "optimization"},
        {"view": "optimization", "optimization_id": 501, "limit": 20},
        {"view": "analytics", "query_id": "abc123"},
        {"timezone": "invalid"},
        {"view": "optimizations", "start_date": "2026-11-10T00:00:00Z"},
    ],
)
def test_query_invalid_inputs_make_no_requests(query_records, kwargs):
    result, calls = run_with(query_records, lambda s: s.query_evidence("101", **kwargs))
    assert result.status == "error" and result.error.code == "invalid_arguments"
    assert calls == []


def test_cross_parent_and_query_proposals_are_rejected(query_records):
    query_records["/v1/servers/101/query-optimizations/501"]["server_id"] = 202
    result, _ = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="optimization",
            optimization_id=501,
        ),
    )
    assert result.error.code == "invalid_source_data"
    query_records["/v1/servers/101/query-analytics/app db/abc123/recommendations"]["items"][0][
        "query_id"
    ] = "foreign"
    result, _ = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="proposals",
            schema_name="app db",
            query_id="abc123",
        ),
    )
    assert result.error.code == "invalid_source_data"


def test_text_plan_is_not_parsed_into_fabricated_facts(query_records):
    query_records["/v1/servers/101/query-optimizations/501"]["query_explain"] = (
        "EXPLAIN email='private@example.invalid'"
    )
    result, _ = run_with(
        query_records,
        lambda s: s.query_evidence(
            "101",
            view="optimization",
            optimization_id=501,
        ),
    )
    assert result.data["optimization"]["plan"] == {
        "available": True,
        "format": "text",
        "nodes": [],
        "details_omitted": True,
    }
    assert "plan_details_omitted" in {w.code for w in result.warnings}
    assert "private@example.invalid" not in result.model_dump_json()


def test_query_missing_data_and_failures_are_not_success(query_records):
    query_records["/v1/servers/101/query-analytics"]["items"] = []
    result, _ = run_with(query_records, lambda s: s.query_evidence("101"))
    assert result.status == "no_data"
    query_records["/v1/servers/101/query-analytics"] = httpx2.Response(503)
    result, _ = run_with(query_records, lambda s: s.query_evidence("101"))
    assert result.status == "error"
