import json

from test_diagnostics import run_with
from test_foundation import module


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
