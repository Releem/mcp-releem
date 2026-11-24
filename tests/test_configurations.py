from copy import deepcopy

import pytest
from test_diagnostics import run_with


@pytest.fixture
def configurations():
    state = dict(
        configuration_status_id=5,
        configuration_id=3,
        server_id=101,
        timestamp=100,
        configuration_timestamp=90,
        applied_status=1,
        applied_timestamp=110,
        is_first=False,
        required_restart=None,
    )
    detail = {
        **state,
        "variables": [{"name": "password", "value": "private-value"}],
        "source_variables": "private-source",
        "period": {"start": 110, "end": None},
        "history": None,
        "configuration_metrics": {"password": "private-metric"},
    }
    return {
        "/v1/servers/101/configurations": {
            "items": [state, {**state, "configuration_status_id": 4, "applied_status": 3}]
        },
        "/v1/servers/101/configurations/5": detail,
    }


def test_configuration_history_preserves_states_and_caps(configurations):
    result, calls = run_with(configurations, lambda s: s.configurations("101", limit=1))
    assert result.status == "partial"
    assert calls[0].url.params["limit"] == "1"
    assert result.data["items"][0]["configuration_status_id"] == 5
    assert result.data["items"][0]["configuration_id"] == 3
    assert result.coverage.omitted == 1
    assert not result.coverage.complete


def test_configuration_detail_omits_unstructured_values(configurations):
    result, calls = run_with(
        configurations, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    assert calls[0].url.path.endswith("/configurations/5")
    row = result.data["configuration"]
    assert row["required_restart"] is None
    assert row["period"] == {"start": 110, "end": None}
    assert row["history"] is None
    assert result.status == "partial"
    assert "private-" not in result.model_dump_json()
    assert row["variables_count"] == 1


@pytest.mark.parametrize("change", [{"server_id": 202}, {"configuration_status_id": 6}])
def test_configuration_detail_rejects_wrong_identity(configurations, change):
    configurations["/v1/servers/101/configurations/5"].update(change)
    result, _ = run_with(
        configurations, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    assert result.error.code == "invalid_source_data"


@pytest.mark.parametrize(
    "args",
    [
        dict(view="detail"),
        dict(configuration_id=3),
        dict(view="detail", configuration_status_id=5, limit=1),
        dict(limit=101),
    ],
)
def test_configuration_invalid_inputs_do_not_call_api(configurations, args):
    result, calls = run_with(configurations, lambda s: s.configurations("101", **args))
    assert result.error.code == "invalid_arguments"
    assert not calls


def test_configuration_latest_and_empty_are_explicit(configurations):
    configurations = deepcopy(configurations)
    configurations["/v1/servers/101/configurations"] = {"items": []}
    result, calls = run_with(configurations, lambda s: s.configurations("101", view="latest"))
    assert result.status == "no_data"
    assert calls[0].url.params["latest"] == "true"
    assert "limit" not in calls[0].url.params


def test_latest_preserves_newest_state_even_for_older_logical_configuration(configurations):
    states = configurations["/v1/servers/101/configurations"]["items"]
    states[0].update(configuration_id=2, timestamp=200)
    states[1].update(configuration_id=9, timestamp=100)
    result, calls = run_with(configurations, lambda s: s.configurations("101", view="latest"))
    assert calls[0].url.params["latest"] == "true"
    assert result.data["items"][0]["configuration_id"] == 2
    assert result.data["items"][0]["configuration_status_id"] == 5
    assert any(w.code == "configuration_state_only" for w in result.warnings)


@pytest.mark.parametrize("view", ["history", "latest", "detail"])
@pytest.mark.parametrize("code", [1, "future"])
def test_configuration_retains_production_status_id(configurations, view, code):
    status = {"id": code, "name": "Upstream display name"}
    configurations["/v1/servers/101/configurations"]["items"][0]["applied_status"] = status
    configurations["/v1/servers/101/configurations/5"]["applied_status"] = status
    detail = {"configuration_status_id": 5} if view == "detail" else {}
    result, _ = run_with(configurations, lambda s: s.configurations("101", view=view, **detail))
    assert result.error is None
    row = result.data["configuration"] if detail else result.data["items"][0]
    assert row["applied_status"] == code
    assert "Upstream display name" not in result.model_dump_json()


@pytest.mark.parametrize("status,expected", [(None, 0), ({"name": "Missing ID"}, None)])
def test_configuration_detail_default_and_malformed_status(configurations, status, expected):
    source = configurations["/v1/servers/101/configurations/5"]
    source.pop("applied_status")
    if status is not None:
        source["applied_status"] = status
    result, _ = run_with(
        configurations, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    if expected is None:
        assert result.error.code == "invalid_source_data"
    else:
        assert result.data["configuration"]["applied_status"] == expected


@pytest.fixture
def tuning_states(configurations):
    detail = configurations["/v1/servers/101/configurations/5"]
    detail.update(
        applied_status={"id": 2, "name": "Partially applied"},
        variables_orig='{"MAX_CONNECTIONS":100,"table_open_cache":"2000",'
        '"innodb_buffer_pool_size":"1 GiB","performance_schema":"OFF","password":"111"}',
        source_variables={
            "max_connections": 150,
            "table_open_cache": 4000,
            "innodb_buffer_pool_size": 1073741824,
            "performance_schema": 0,
            "password": "222",
            "unrelated": "private-canary",
        },
        variables=[
            {"name": "max_connections", "value": "200"},
            {"name": "table_open_cache", "value": "4000"},
            {"name": "innodb_buffer_pool_size", "value": "1024M"},
            {"name": "performance_schema", "value": "0"},
            {"name": "password", "value": "333"},
        ],
        history={
            "timestamp": 90,
            "performance_score": 70,
            "config_recommendations": "private-recommendation",
        },
    )
    return configurations


def test_detail_shows_recorded_proposed_and_remaining_values(tuning_states):
    result, calls = run_with(
        tuning_states, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    assert len(calls) == 1
    data = result.data["configuration"]
    assert data["variables_count"] == 5
    changes = data["variable_changes"]
    for comparison, value in (("recorded", "150"), ("proposed", "200")):
        assert changes[comparison]["items"] == [
            {"name": "max_connections", "old_value": "100", "new_value": value},
            {"name": "table_open_cache", "old_value": "2000", "new_value": "4000"},
        ]
        assert changes[comparison]["omitted"] == 1
    assert changes["remaining"]["items"] == [
        {"name": "max_connections", "last_recorded_value": "150", "recommended_value": "200"}
    ]
    for private in ("private-", "password", "source_variables", "variables_orig", '"222"'):
        assert private not in str(result.data)


def test_applied_changes_uses_application_order_and_state_local_evidence(tuning_states):
    root = "/v1/servers/101/configurations"
    first = tuning_states[root + "/5"]
    first["variables"][-1]["value"] = "222"
    states = tuning_states[root]["items"]
    states[0].update(applied_status=2)
    states[1].update(applied_timestamp=150)
    tuning_states[root + "/4"] = {
        **first,
        "configuration_status_id": 4,
        "applied_status": 3,
        "applied_timestamp": 150,
        "rollback_timestamp": 190,
        "variables_orig": {"max_connections": "175"},
        "source_variables": {"max_connections": 200},
        "variables": [{"name": "max_connections", "value": "200"}],
    }
    result, calls = run_with(
        tuning_states, lambda s: s.configurations("101", view="applied_changes")
    )
    assert result.error is None
    assert [call.url.path for call in calls] == [root, root + "/5", root + "/4"]
    assert [
        (row["configuration_status_id"], row["name"], row["old_value"], row["new_value"])
        for row in result.data["items"]
    ] == [(4, "max_connections", "175", "200"), (5, "table_open_cache", "2000", "4000")]
    assert result.data["items"][0]["rollback_timestamp"] == 190
    assert result.data["scan"]["states_scanned"] == 2
    assert result.coverage.omitted == 1


@pytest.mark.parametrize("snapshot", [None, "invalid JSON", [], {}])
def test_remaining_values_require_a_stored_snapshot(tuning_states, snapshot):
    tuning_states["/v1/servers/101/configurations/5"]["source_variables"] = snapshot
    result, _ = run_with(
        tuning_states, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    remaining = result.data["configuration"]["variable_changes"]["remaining"]
    assert remaining["status"] == "unavailable"
    assert remaining["items"] == []


def test_duplicates_and_unsafe_values_leave_comparison_gaps(tuning_states):
    detail = tuning_states["/v1/servers/101/configurations/5"]
    detail["variables_orig"] = (
        '{"max_connections":"100","max_connections":"101","table_open_cache":1}'
    )
    detail["source_variables"]["table_open_cache"] = "private-path/path"
    result, _ = run_with(
        tuning_states, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    changes = result.data["configuration"]["variable_changes"]
    assert changes["recorded"]["uncompared"] >= 1
    assert changes["recorded"]["omitted"] == 1
    assert "private-path" not in result.model_dump_json()


def test_remaining_comparison_can_be_complete_without_an_original(tuning_states):
    state = tuning_states["/v1/servers/101/configurations/5"]
    state["variables_orig"] = None
    state["source_variables"] = {
        variable["name"]: variable["value"] for variable in state["variables"]
    }
    result, _ = run_with(
        tuning_states, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    changes = result.data["configuration"]["variable_changes"]
    assert changes["recorded"]["status"] == "unavailable"
    assert changes["remaining"] == {
        "status": "complete",
        "items": [],
        "uncompared": 0,
        "omitted": 0,
    }


def test_detail_budget_preserves_coverage(tuning_states):
    from mcp_releem.core.results import fit

    result, _ = run_with(
        tuning_states, lambda s: s.configurations("101", view="detail", configuration_status_id=5)
    )
    budget = len(result.model_dump_json().encode()) - 1
    trimmed = fit(result, budget)
    assert len(trimmed.model_dump_json().encode()) <= budget
    assert trimmed.data["configuration"]["configuration_status_id"] == 5
    changes = trimmed.data["configuration"]["variable_changes"]
    assert changes["recorded"]["status"] == "partial"
    assert changes["recorded"]["omitted"] > 1
    assert "configuration.variable_changes.recorded.items" in trimmed.coverage.truncated_fields


def test_applied_changes_discloses_missing_evidence_and_scan_limit(tuning_states):
    import httpx2

    root = "/v1/servers/101/configurations"
    detail = tuning_states[root + "/5"]
    detail["history"].pop("config_recommendations")
    tuning_states[root + "/4"] = httpx2.Response(404)
    tuning_states[root]["items"].append(
        {**tuning_states[root]["items"][0], "configuration_status_id": 3, "applied_status": 0}
    )
    result, calls = run_with(
        tuning_states, lambda s: s.configurations("101", view="applied_changes", limit=3)
    )
    assert result.status == "partial"
    assert result.data["items"] == []
    assert result.data["scan"]["states_with_insufficient_evidence"] == 2
    assert not result.coverage.complete
    assert len(calls) == 3 and calls[0].url.params["limit"] == "3"


def test_applied_changes_cannot_exceed_scan_bound(configurations):
    result, calls = run_with(
        configurations, lambda s: s.configurations("101", view="applied_changes", limit=21)
    )
    assert result.error.code == "invalid_arguments"
    assert calls == []
