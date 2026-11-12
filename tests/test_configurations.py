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
