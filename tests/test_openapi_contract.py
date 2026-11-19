"""Offline compatibility guard against the exact captured public contract."""

import hashlib
import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from mcp_releem.api.models import Check
from mcp_releem.api.operations import OPERATIONS, APIError, prepare, validate

CAPTURE = (
    Path(__file__).resolve().parents[1] / "tests/fixtures/openapi/releem-openapi-2026-11-11.json"
)
PRODUCTION_CAPTURE = CAPTURE.with_name("releem-openapi-production-2026-11-19.json")


@pytest.fixture(scope="module")
def contract():
    payload = CAPTURE.read_bytes()
    assert (
        hashlib.sha256(payload).hexdigest()
        == "a2474b68c2b32f589bd24c820ab0a80df9200e888476aee78cb3c590c6b19e40"
    )
    return json.loads(payload)


@pytest.fixture(scope="module")
def production_contract():
    payload = PRODUCTION_CAPTURE.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == (
        "9e514a03c100663799e6f6c86f443e8585b52bd74be8f5144a6ec5f4a1d364d4"
    )
    return json.loads(payload)


def normalize_path(path):
    return re.sub(r"\{[^}]+\}", "{}", path)


def test_closed_get_registry_uses_only_documented_routes_and_query_keys(contract):
    paths = {normalize_path(path): operations for path, operations in contract["paths"].items()}
    assert len(OPERATIONS) == 26
    for name, operation in OPERATIONS.items():
        route = paths[normalize_path(operation.path)]
        assert "get" in route, name
        parameters = route.get("parameters", []) + route["get"].get("parameters", [])
        query_keys = {parameter["name"] for parameter in parameters if parameter["in"] == "query"}
        assert operation.query_keys <= query_keys, name
    assert not any(operation.path == "/v1/checks" for operation in OPERATIONS.values())
    assert "period_days" not in OPERATIONS["query_analytics"].query_keys


def test_registered_requests_match_production_contract(contract, production_contract):
    def signature(document, path, query_keys):
        paths = {normalize_path(key): route for key, route in document["paths"].items()}
        route = paths[normalize_path(path)]
        get = route["get"]
        params = route.get("parameters", []) + get.get("parameters", [])
        consumed = {
            (p["in"], p["name"]): p
            for p in params
            if p["in"] == "path" or p["name"] in query_keys or p.get("required")
        }
        assert "200" in get["responses"]
        assert query_keys <= {name for location, name in consumed if location == "query"}
        return consumed, get.get("security", document.get("security"))

    assert (
        production_contract["components"]["securitySchemes"]
        == (contract["components"]["securitySchemes"])
    )
    for operation in OPERATIONS.values():
        baseline = signature(contract, operation.path, operation.query_keys)
        production = signature(production_contract, operation.path, operation.query_keys)
        assert production == baseline, operation.path


@pytest.mark.parametrize(
    "operation,path",
    [
        ("events_viewed", "/v1/servers/{id}/events/viewed"),
        ("deadlocks_viewed", "/v1/servers/{id}/deadlocks/viewed"),
    ],
)
def test_production_view_state_updates_remain_outside_registry(
    production_contract, operation, path
):
    assert set(production_contract["paths"][path]) == {"post"}
    assert all(normalize_path(spec.path) != normalize_path(path) for spec in OPERATIONS.values())
    with pytest.raises(APIError) as error:
        prepare(operation, {"server_id": "101"})
    assert error.value.code == "operation_denied"


def production_examples():
    stamp = "2026-11-19T00:00:00Z"
    server = {"id": "101", "instance_type": {"id": "1", "name": "On-premise"}}
    checks = {"example": {"failed": False, "value": "95.5%"}}
    state = {
        "configuration_status_id": 5,
        "configuration_id": 3,
        "server_id": 101,
        "timestamp": 1736937000,
        "configuration_timestamp": 1736937000,
        "applied_status": {"id": 1, "name": "Applied"},
        "applied_timestamp": 1736937000,
        "is_first": False,
    }
    event = {
        "server_id": 101,
        "event_id": "18446744073709551615",
        "timestamp": stamp,
        "name": "Example event",
        "uid": 1,
        "event_type_id": 1,
        "event_type": {"id": 1},
        "event_severity": {"id": 2},
        "is_viewed": False,
    }
    deadlock = {
        "id": 4,
        "server_id": 101,
        "timestamp": stamp,
        "database": "example_db",
        "table": "example_table",
        "deadlock_type": {"id": 1},
        "is_viewed": False,
    }
    task = {"id": 401, "server_id": 101, "status": 1, "type": {"id": 3}}
    schema = {
        "server_id": 101,
        "is_check": 1,
        "type": {"id": "UNUSED_INDEX_NEW"},
        "count_checks": 1,
        "data": "null",
    }
    optimization = {
        "id": 501,
        "server_id": 101,
        "status": {"id": 5},
        "timestamp_status": 1736937000,
    }
    recommendation = {
        "id": 601,
        "server_id": "101",
        "source_type": "configuration",
        "source_id": "501",
        "source_subtype": "buffer_pool",
        "title": "Review buffer pool",
        "summary": "Example recommendation",
        "status": "new",
        "type_id": 3,
        "category_id": 3,
        "type": {"id": 3},
        "category": {"id": 3},
    }
    recommendation_page = {"items": [recommendation], "total": 1, "offset": 0}
    return {
        "servers": [server],
        "server": server,
        "details": {**server, "health_checks": checks, "security_checks": {}},
        "health": {"checks": checks, "timestamp": 1736937000},
        "configurations": {"items": [state]},
        "configuration": {**state, "variables": []},
        "events": {"items": [event]},
        "event": {
            "event_id": int(event["event_id"]),
            "timestamp": stamp,
            "event_body": {},
            "is_viewed": False,
        },
        "deadlocks": {"items": [deadlock]},
        "deadlock": {**deadlock, "raw": "Synthetic dump"},
        "tasks": {"items": [task]},
        "task": task,
        "schema": {"server_id": 101, "timestamp": stamp, "items": [schema]},
        "optimizations": {"items": [optimization]},
        "optimization": {**optimization, "error_apply_code": {"id": 1}},
        "recommendations": recommendation_page,
        "fleet_recommendations": recommendation_page,
        "recommendation": recommendation,
    }


@pytest.mark.parametrize("operation,payload", production_examples().items())
def test_production_examples_validate_as_documented_and_parse(
    production_contract, operation, payload
):
    spec = OPERATIONS[operation]
    path = next(
        key
        for key in production_contract["paths"]
        if normalize_path(key) == normalize_path(spec.path)
    )
    response = production_contract["paths"][path]["get"]["responses"]["200"]
    schema = response["content"]["application/json"]["schema"]
    Draft202012Validator({**schema, "components": production_contract["components"]}).validate(
        payload
    )
    server_id = None if operation in {"servers", "fleet_recommendations"} else "101"
    validate(spec, payload, server_id)


def test_contract_identity_and_deferred_catalog_remain_explicit(contract):
    assert contract["info"]["title"] == "Releem API"
    assert contract["info"]["version"] == "1.0.0"
    methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    assert sum(len(methods & route.keys()) for route in contract["paths"].values()) == 46
    assert "get" in contract["paths"]["/v1/checks"]


@pytest.mark.parametrize("name", ["checks", "tasks_create", "recommendation_update", "/v1/checks"])
def test_discovery_contract_does_not_grant_outbound_capabilities(name):
    with pytest.raises(APIError) as error:
        prepare(name, {})
    assert error.value.code == "operation_denied"


def test_arbitrary_method_cannot_be_injected():
    with pytest.raises(APIError) as error:
        prepare("servers", {"method": "POST"})
    assert error.value.code == "invalid_arguments"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"failed": None, "description": None},
        {"failed": True, "value": None, "title": "Account security", "severity": "critical"},
        {
            "failed": False,
            "title": None,
            "short_description": None,
            "learn_more_url": None,
            "group": None,
            "severity": None,
        },
    ],
)
def test_nullable_check_instances_match_named_schema_and_adapter(contract, payload):
    schema = contract["components"]["schemas"]["ServerHealthCheckResult"]
    Draft202012Validator(schema).validate(payload)
    check = Check.model_validate(payload)
    assert check.failed is payload.get("failed")


@pytest.mark.parametrize("payload", [{"failed": "false"}, {"description": 1}, {"severity": False}])
def test_check_schema_and_adapter_reject_malformed_types(contract, payload):
    schema = contract["components"]["schemas"]["ServerHealthCheckResult"]
    assert not Draft202012Validator(schema).is_valid(payload)
    with pytest.raises(ValidationError):
        Check.model_validate(payload)
