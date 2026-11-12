"""Synthetic package archives must fail closed before a release receipt exists."""

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

TOOL = Path(__file__).parents[1] / "tools/release/artifacts.py"


def auditor():
    spec = importlib.util.spec_from_file_location("release_artifacts", TOOL)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def package(tmp_path, kind="wheel", extra=None, version="0.1.0", missing=None):
    entries = {
        "mcp_releem/__init__.py": f'__version__ = "{version}"\n',
        "mcp_releem/__main__.py": "from .cli import main\n",
        "mcp_releem/cli.py": "def main(): pass\n",
        "mcp_releem/server.py": "# synthetic\n",
        "mcp_releem/api/client.py": "# synthetic\n",
        "mcp_releem/core/diagnostics.py": "# synthetic\n",
        **{
            f"mcp_releem/hosted/{name}.py": "# synthetic\n"
            for name in ("app", "config", "context", "limits", "ingress", "health")
        },
    }
    entries.pop(missing, None)
    entries.update(extra or {})
    if kind == "wheel":
        entries["mcp_releem-0.1.0.dist-info/METADATA"] = "Name: mcp-releem\nVersion: 0.1.0\n"
        path = tmp_path / "mcp_releem-0.1.0-py3-none-any.whl"
        with zipfile.ZipFile(path, "w") as archive:
            for name, body in entries.items():
                archive.writestr(name, body)
    else:
        path = tmp_path / "mcp_releem-0.1.0.tar.gz"
        entries = {"src/" + k: v for k, v in entries.items()}
        entries["PKG-INFO"] = "Name: mcp-releem\nVersion: 0.1.0\n"
        with tarfile.open(path, "w:gz") as archive:
            for name, body in entries.items():
                data = body.encode()
                info = tarfile.TarInfo("mcp_releem-0.1.0/" + name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    return path


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_valid_synthetic_archives(tmp_path, kind):
    auditor().audit_archive(package(tmp_path, kind), "0.1.0")


@pytest.mark.parametrize(
    "name",
    [
        ".env",
        ".agent/CONTINUITY.md",
        ".git/config",
        "backup/key",
        "dbharness/execute.py",
        "../escape",
        "credentials.json",
        ".aws/config",
        ".ssh/id_rsa",
        "secrets/key",
        "private.pem",
    ],
)
@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_rejects_private_and_legacy_paths(tmp_path, kind, name):
    with pytest.raises(ValueError):
        auditor().audit_archive(package(tmp_path, kind, {name: "synthetic"}), "0.1.0")


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_rejects_disagreeing_version(tmp_path, kind):
    with pytest.raises(ValueError, match="version"):
        auditor().audit_archive(package(tmp_path, kind, version="9.9.9"), "0.1.0")


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
@pytest.mark.parametrize(
    "missing",
    [
        "api/client.py",
        "hosted/app.py",
        "hosted/config.py",
        "hosted/context.py",
        "hosted/limits.py",
        "hosted/ingress.py",
        "hosted/health.py",
    ],
)
def test_rejects_missing_core_module(tmp_path, kind, missing):
    with pytest.raises(ValueError, match="missing"):
        auditor().audit_archive(package(tmp_path, kind, missing="mcp_releem/" + missing), "0.1.0")


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_rejects_legacy_code_content(tmp_path, kind):
    with pytest.raises(ValueError, match="legacy"):
        auditor().audit_archive(
            package(tmp_path, kind, {"mcp_releem/legacy.py": "import dbharness"}), "0.1.0"
        )


def test_failed_audit_never_creates_receipt(tmp_path, monkeypatch):
    import sys

    package(tmp_path, extra={".env": "synthetic"})
    package(tmp_path, "sdist")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "artifacts",
            str(tmp_path),
            "--version",
            "0.1.0",
            "--revision",
            "synthetic",
            "--dirty",
            "true",
            "--lock-hash",
            "synthetic",
        ],
    )
    with pytest.raises(ValueError):
        auditor().main()
    assert not (tmp_path / "verification.json").exists()


def test_receipt_records_both_delivery_images(tmp_path, monkeypatch):
    import json
    import sys

    package(tmp_path)
    package(tmp_path, "sdist")
    for name, identifier in [
        ("image-inspect.json", "sha256:local"),
        ("hosted-image-inspect.json", "sha256:hosted"),
    ]:
        (tmp_path / name).write_text(
            json.dumps([{"Id": identifier, "Os": "linux", "Architecture": "arm64"}])
        )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "artifacts",
            str(tmp_path),
            "--version",
            "0.1.0",
            "--revision",
            "synthetic",
            "--dirty",
            "true",
            "--lock-hash",
            "synthetic",
        ],
    )
    auditor().main()
    receipt = json.loads((tmp_path / "verification.json").read_text())
    assert receipt["image_id"] == "sha256:local"
    assert receipt["hosted_image_id"] == "sha256:hosted"
    assert receipt["hosted_architecture"] == "arm64"
    assert "verification.json" in (tmp_path / "SHA256SUMS").read_text()


@pytest.mark.parametrize(
    "report",
    [
        {"status": "failed", "image_id": "sha256:hosted"},
        {"status": "passed", "image_id": "sha256:other"},
    ],
)
def test_stale_or_mismatched_security_report_cannot_pass(tmp_path, monkeypatch, report):
    import json
    import sys

    package(tmp_path)
    package(tmp_path, "sdist")
    for name, identifier in [
        ("image-inspect.json", "sha256:local"),
        ("hosted-image-inspect.json", "sha256:hosted"),
    ]:
        (tmp_path / name).write_text(
            json.dumps([{"Id": identifier, "Os": "linux", "Architecture": "arm64"}])
        )
    (tmp_path / "security-report.json").write_text(json.dumps(report))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "artifacts",
            str(tmp_path),
            "--version",
            "0.1.0",
            "--revision",
            "synthetic",
            "--dirty",
            "true",
            "--lock-hash",
            "synthetic",
        ],
    )
    with pytest.raises(ValueError):
        auditor().main()
    assert not (tmp_path / "verification.json").exists()
