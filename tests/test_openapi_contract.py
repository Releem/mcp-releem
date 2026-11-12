"""Offline compatibility guard against the exact captured public contract."""

import hashlib
import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from mcp_releem.api.models import Check
from mcp_releem.api.operations import OPERATIONS, APIError, prepare

CAPTURE = Path(__file__).resolve().parents[1] / "docs/plans/evidence/releem-openapi-2026-11-11.json"


@pytest.fixture(scope="module")
def contract():
    payload = CAPTURE.read_bytes()
    assert (
        hashlib.sha256(payload).hexdigest()
        == "a2474b68c2b32f589bd24c820ab0a80df9200e888476aee78cb3c590c6b19e40"
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
