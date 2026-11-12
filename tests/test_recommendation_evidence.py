import pytest
from test_diagnostics import run_with


@pytest.fixture
def reviewed_records(records):
    record = records["/v1/servers/101/recommendations/601"]
    review = dict(
        id=501,
        priority_score=80.0,
        base_score=None,
        score_adjustment_applied=0.0,
        why_important_now="Measured demand",
        created_at="2026-11-10T17:00:00",
        review_details={"password": "private-details"},
        review_input_snapshot={"sql": "private-snapshot"},
    )
    event = dict(
        id=701,
        new_status="done",
        old_status="new",
        actor_type="user",
        actor_id="private-user",
        reason="private-reason",
        created_at="2026-11-10T17:30:00Z",
    )
    record.update(
        evidence={"href": "/v1/servers/101/configurations/5", "pointer": None},
        current_review=review,
        review_history=[review] * 3,
        status_history=[event] * 3,
    )
    return records


def test_detail_adds_bounded_reviews_statuses_and_safe_evidence_reference(reviewed_records):
    result, calls = run_with(
        reviewed_records,
        lambda s: s.recommendations("101", view="detail", recommendation_id=601, history_limit=1),
    )
    assert result.status == "partial"
    row = result.data["recommendation"]
    assert row["current_review"]["base_score"] is None
    assert row["current_review"]["score_adjustment_applied"] == 0
    assert row["current_review"]["created_at"].endswith("+00:00")
    assert len(row["review_history"]) == len(row["status_history"]) == 1
    assert row["history_coverage"]["review_history"]["omitted"] == 2
    assert row["evidence_reference"] == {
        "tool": "configurations",
        "arguments": {"server_id": "101", "view": "detail", "configuration_status_id": 5},
    }
    assert "private-" not in result.model_dump_json()
    assert "actor_id" not in row["status_history"][0]
    assert len(calls) == 1


@pytest.mark.parametrize(
    "source,href,tool",
    [
        ("query_optimization", "/v1/servers/101/query-optimizations/501", "query_evidence"),
        ("deadlock", "/v1/servers/101/deadlocks/4", "deadlocks"),
        ("schema_check", "/v1/servers/101/schema-checks?type=UNUSED_INDEX_NEW", "server_findings"),
        ("security_check", "/v1/servers/101/security-checks", "server_findings"),
    ],
)
def test_known_evidence_paths_map_to_typed_jobs_without_fetching(
    reviewed_records, source, href, tool
):
    record = reviewed_records["/v1/servers/101/recommendations/601"]
    record.update(source_type=source, evidence={"href": href, "pointer": "/checks/private-pointer"})
    result, calls = run_with(
        reviewed_records, lambda s: s.recommendations("101", view="detail", recommendation_id=601)
    )
    assert result.data["recommendation"]["evidence_reference"]["tool"] == tool
    assert "private-pointer" not in result.model_dump_json()
    assert len(calls) == 1


@pytest.mark.parametrize(
    "href",
    [
        "https://evil.invalid/leak",
        "//evil.invalid/leak",
        "/v1/servers/202/configurations/5",
        "/v1/servers/101/configurations/5?secret=private-value",
        "/v1/servers/101/configurations/%35",
        "/v1/servers/101/configurations/5#fragment",
    ],
)
def test_unsafe_or_foreign_evidence_links_are_rejected_as_references(reviewed_records, href):
    reviewed_records["/v1/servers/101/recommendations/601"]["evidence"] = {"href": href}
    result, calls = run_with(
        reviewed_records, lambda s: s.recommendations("101", view="detail", recommendation_id=601)
    )
    assert result.data["recommendation"]["evidence_reference"] is None
    assert "evidence_reference_rejected" in {w.code for w in result.warnings}
    assert "evil.invalid" not in result.model_dump_json()
    assert "private-value" not in result.model_dump_json()
    assert len(calls) == 1


def test_missing_history_differs_from_explicit_empty_history(reviewed_records):
    row = reviewed_records["/v1/servers/101/recommendations/601"]
    row.pop("review_history")
    row.update(current_review=None, status_history=[])
    result, _ = run_with(
        reviewed_records, lambda s: s.recommendations("101", view="detail", recommendation_id=601)
    )
    record = result.data["recommendation"]
    assert record["current_review"] is None
    assert record["history_coverage"]["review_history"]["available"] is False
    assert record["history_coverage"]["status_history"]["available"] is True
    assert record["review_history"] is None


def test_unknown_history_status_and_invalid_dates_stay_visible(reviewed_records):
    row = reviewed_records["/v1/servers/101/recommendations/601"]
    row["status_history"][0]["new_status"] = "future_status"
    result, _ = run_with(
        reviewed_records, lambda s: s.recommendations("101", view="detail", recommendation_id=601)
    )
    assert "unknown_recommendation_status" in {w.code for w in result.warnings}
    row["current_review"]["created_at"] = "bad"
    result, _ = run_with(
        reviewed_records, lambda s: s.recommendations("101", view="detail", recommendation_id=601)
    )
    assert result.error.code == "invalid_source_data"


def test_unknown_actor_category_and_omitted_pointer_stay_visible(reviewed_records):
    row = reviewed_records["/v1/servers/101/recommendations/601"]
    row["status_history"][0]["actor_type"] = "private-future-actor"
    row["evidence"]["pointer"] = "/private-pointer"
    result, _ = run_with(
        reviewed_records, lambda s: s.recommendations("101", view="detail", recommendation_id=601)
    )
    event = result.data["recommendation"]["status_history"][0]
    assert event["actor_type"] is None and event["actor_type_unknown"] is True
    assert "unknown_actor_type" in {w.code for w in result.warnings}
    assert "evidence_pointer_omitted" in {w.code for w in result.warnings}
    assert "private-" not in result.model_dump_json()


def test_malformed_schema_reference_keeps_other_detail_evidence(reviewed_records):
    row = reviewed_records["/v1/servers/101/recommendations/601"]
    row.update(source_type="schema_check", evidence={"href": "/v1/servers/101/schema-checks?type"})
    result, _ = run_with(
        reviewed_records, lambda s: s.recommendations("101", view="detail", recommendation_id=601)
    )
    assert result.status == "partial"
    assert result.data["recommendation"]["evidence_reference"] is None
    assert "evidence_reference_rejected" in {w.code for w in result.warnings}


@pytest.mark.parametrize(
    "args",
    [
        dict(history_limit=2),
        dict(view="detail", recommendation_id=601, history_limit=21),
        dict(view="detail", recommendation_id=601, limit=1),
    ],
)
def test_history_inputs_are_detail_only_and_bounded(reviewed_records, args):
    result, calls = run_with(reviewed_records, lambda s: s.recommendations("101", **args))
    assert result.error.code == "invalid_arguments"
    assert not calls
