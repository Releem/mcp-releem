"""Synthetic nullable findings and all-check summaries for both engine families."""

import pytest
from pydantic import ValidationError
from test_diagnostics import run_with
from test_foundation import module


@pytest.mark.parametrize("entry", [{}, {"failed": None, "description": None}])
def test_nullable_check_model_accepts_absent_metadata(entry):
    check = module("api.models").Check.model_validate(entry)
    assert check.failed is None and check.description is None


@pytest.mark.parametrize(
    "field,value",
    [("failed", "true"), ("failed", 1), ("title", 7), ("description", []), ("severity", False)],
)
def test_check_model_rejects_malformed_types(field, value):
    with pytest.raises(ValidationError):
        module("api.models").Check.model_validate(
            {"failed": False, "description": "ok", field: value}
        )


@pytest.mark.parametrize("engine", ["mysql", "postgresql"])
def test_summary_only_classifies_explicit_true_without_fanout(records, engine):
    records["/v1/servers/101"]["mysql_version"] = engine
    records["/v1/servers/101/details"].update(
        health_checks={
            "pass": {"failed": False},
            "failure": {"failed": True},
            "null": {"failed": None},
            "absent": {},
            "malformed": {"failed": "true"},
            "legacy": 1,
            "null_entry": None,
        },
        security_checks={"account": {"failed": True, "value": None}},
        security_checks_unknown=["future"],
        security_checks_decode_error="bad shape",
    )
    result, calls = run_with(records, lambda s: s.findings("101", sections=["summary"]))
    assert len(calls) == 2
    assert result.data["failed_summary"]["health"] == ["failure"]
    assert result.data["failed_summary"]["security"] == ["account"]
    assert result.data["unknown_summary"]["health"] == [
        "null",
        "absent",
        "malformed",
        "legacy",
        "null_entry",
    ]
    assert result.data["failed_summary"]["unknown"] == ["future"]
    assert result.data["failed_summary"]["decode_error"] == "bad shape"
    assert result.status == "partial"
    codes = {w.code for w in result.warnings}
    assert {"unknown_check_results", "check_summary_source_shape", "security_decode_error"} <= codes
    assert "failed_summary_only" not in codes


@pytest.mark.parametrize("snapshot", [None, {}])
def test_missing_or_empty_summaries_cannot_establish_health(records, snapshot):
    records["/v1/servers/101/details"].update(
        health_checks=snapshot,
        security_checks=snapshot,
        security_checks_unknown=[],
        security_checks_decode_error=None,
    )
    result, _ = run_with(records, lambda s: s.findings("101", sections=["summary"]))
    assert result.status == "partial" and not result.coverage.complete
    assert "check_summary_unavailable" in {w.code for w in result.warnings}


def test_full_reports_preserve_order_metadata_and_known_null_failure(records):
    checks = {
        "account": {
            "failed": True,
            "value": None,
            "title": "Account synthetic-secret",
            "short_description": "password=hidden",
            "description": None,
            "learn_more_url": "https://private.invalid/token/hidden-link",
            "severity": "future user@example.invalid",
            "group": "Access",
            "private": "opaque-private",
        },
        "numeric": {"failed": False, "value": 3.5, "severity": "high"},
        "unknown": {},
    }
    records["/v1/servers/101/security-checks"] = {
        "timestamp": 1794333600,
        "checks": checks,
        "failed_checks": ["account"],
    }
    result, calls = run_with(records, lambda s: s.findings("101", sections=["security"]))
    assert len(calls) == 1
    presented = result.data["reports"]["security"]["checks"]
    assert list(presented) == ["account", "numeric", "unknown"]
    assert presented["account"]["failed"] is True and presented["account"]["value"] is None
    assert presented["account"]["documentation_reference_present"] is True
    assert presented["numeric"]["documentation_reference_present"] is False
    assert presented["numeric"]["value"] == 3.5
    assert presented["account"]["severity"].startswith("future ")
    raw = result.model_dump_json()
    assert all(
        text not in raw
        for text in [
            "learn_more_url",
            "hidden-link",
            "opaque-private",
            "synthetic-secret",
            "password=hidden",
            "user@example.invalid",
        ]
    )
    assert {"unknown_check_results", "unknown_check_severity"} <= {w.code for w in result.warnings}
    assert result.status == "partial"


def test_fresh_empty_full_report_stays_partial(records):
    records["/v1/servers/101/health-checks"] = {"timestamp": 1794333600, "checks": {}}
    result, _ = run_with(records, lambda s: s.findings("101", sections=["health"]))
    assert result.status == "partial"
    assert "report_checks_empty" in {w.code for w in result.warnings}


def test_known_fresh_failure_with_null_value_is_available(records):
    records["/v1/servers/101/security-checks"] = {
        "timestamp": 1794333600,
        "checks": {"account": {"failed": True, "value": None}},
        "failed_checks": ["account"],
    }
    result, _ = run_with(records, lambda s: s.findings("101", sections=["security"]))
    assert result.status == "ok"
    assert result.data["reports"]["security"]["checks"]["account"]["failed"] is True
    assert result.data["reports"]["security"]["checks"]["account"]["value"] is None


def test_malformed_full_result_remains_component_error(records):
    records["/v1/servers/101/security-checks"]["checks"]["accounts"]["failed"] = "true"
    result, _ = run_with(records, lambda s: s.findings("101", sections=["security", "health"]))
    assert result.status == "partial"
    assert result.data["component_errors"]["security"]["code"] == "invalid_source_data"
    assert "security" not in result.data["reports"]


def test_metadata_clipping_retains_missing_and_unknown_warnings(records):
    records["/v1/servers/101/health-checks"] = {
        "timestamp": None,
        "checks": {"unknown": {"title": "x" * 1000}},
    }
    result, _ = run_with(records, lambda s: s.findings("101", sections=["health"]))
    assert result.status == "partial"
    assert {"unknown_check_results", "report_absent", "text_truncated"} <= {
        w.code for w in result.warnings
    }
    assert len(result.data["reports"]["health"]["checks"]["unknown"]["title"]) < 600


def test_oversized_metadata_report_fails_explicitly_without_trimming_checks(records):
    records["/v1/servers/101/security-checks"] = {
        "timestamp": 1794333600,
        "checks": {f"account-{n}": {"failed": True, "title": "x" * 300} for n in range(30)},
    }
    result, _ = run_with(records, lambda s: s.findings("101", sections=["security"]), budget=4096)
    assert result.status == "error" and result.error.code == "result_too_large"
    assert result.data is None and not result.coverage.complete
