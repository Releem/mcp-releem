"""Fail closed on incomplete Python audits, missing notices or image findings."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def canonical(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def validate_python(report: dict[str, Any], inventory: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {canonical(row["name"]): row["version"] for row in inventory}
    seen = {}
    skipped = []
    for row in report["dependencies"]:
        name = canonical(row["name"])
        if name == "mcp-releem":
            skipped.append({"name": name, "reason": "First-party source reviewed separately"})
            continue
        if row.get("skip_reason") or row.get("vulns") or "vulns" not in row:
            raise ValueError("Incomplete audit or dependency vulnerabilities")
        seen[name] = row["version"]
    if seen != expected:
        raise ValueError("Audit does not cover exact runtime inventory")
    if any(
        not (row.get("license") or row.get("license_classifiers")) or not row.get("notices")
        for row in inventory
    ):
        raise ValueError("License metadata/notices need manual review")
    return {
        "audited_packages": len(seen),
        "first_party_exclusions": skipped,
        "known_python_vulnerabilities": 0,
        "bundled_license_notices": True,
    }


def main() -> None:
    root = Path(sys.argv[1])
    result = validate_python(
        json.loads((root / "pip-audit.json").read_text()),
        json.loads((root / "licenses.json").read_text()),
    )
    image = json.loads((root / "trivy.json").read_text())
    if not image.get("Results") or not image.get("Metadata", {}).get("OS"):
        raise ValueError("Image scan did not establish OS coverage")
    identifier = (root / "scanned-image-id.txt").read_text().strip()
    config_identifier = (root / "scanned-config-id.txt").read_text().strip()
    if image.get("Metadata", {}).get("ImageID") != config_identifier:
        raise ValueError("Advisory report is for a different image")
    result["image_id"] = identifier
    result["config_image_id"] = config_identifier
    result["archive_sha256"] = (root / "scanned-archive-sha256.txt").read_text().strip()
    findings = [
        v
        for r in image["Results"]
        for v in r.get("Vulnerabilities", [])
        if v.get("Severity") in {"HIGH", "CRITICAL"}
    ]
    if findings:
        raise ValueError("High/critical image vulnerabilities require review")
    result.update(
        {
            "status": "passed",
            "scanned_at": datetime.now(UTC).isoformat(),
            "known_high_critical_image_vulnerabilities": 0,
            "scope": "known advisories; not proof of absence of vulnerabilities",
        }
    )
    (root / "security-report.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
