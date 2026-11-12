import importlib.util
from pathlib import Path

import pytest


def validator():
    path = Path(__file__).parents[1] / "tools/release/security_report.py"
    spec = importlib.util.spec_from_file_location("security_report", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_python


def test_audit_requires_complete_coverage_and_no_findings():
    check = validator()
    inventory = [
        {"name": "example_lib", "version": "1.0", "license": "MIT", "notices": [{"text": "MIT"}]}
    ]
    report = {"dependencies": [{"name": "example-lib", "version": "1.0", "vulns": []}]}
    assert check(report, inventory)["audited_packages"] == 1
    for deps in [
        [],
        [{"name": "example-lib", "version": "1.0", "skip_reason": "unavailable"}],
        [{"name": "example-lib", "version": "1.0", "vulns": [{"id": "synthetic-CVE"}]}],
        [{"name": "example-lib", "version": "2.0", "vulns": []}],
    ]:
        with pytest.raises(ValueError):
            check({"dependencies": deps}, inventory)
