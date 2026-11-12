"""Audit archives without extracting or executing their contents."""

import argparse
import ast
import email.parser
import hashlib
import json
import tarfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

REQUIRED = {
    "__init__.py",
    "__main__.py",
    "cli.py",
    "server.py",
    "api/client.py",
    "core/diagnostics.py",
    "hosted/app.py",
    "hosted/config.py",
    "hosted/context.py",
    "hosted/limits.py",
    "hosted/ingress.py",
    "hosted/health.py",
}
FORBIDDEN = {
    ".agent",
    ".git",
    ".venv",
    "backup",
    "backups",
    "dbharness",
    "credentials.json",
    ".aws",
    ".ssh",
    ".codex",
    "secrets",
    "id_rsa",
}


def check_path(name: str) -> None:
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or "\\" in name
        or any(
            part.lower() in FORBIDDEN
            or part == ".."
            or part.lower().startswith((".env", "mcp-releem-backup"))
            or part.lower().endswith((".pem", ".key"))
            for part in path.parts
        )
    ):
        raise ValueError("forbidden artifact path")


def module_version(content: str) -> str:
    for statement in ast.parse(content).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in statement.targets
        ):
            value = ast.literal_eval(statement.value)
            if isinstance(value, str):
                return value
    raise ValueError("missing module version")


def audit_archive(path: Path, version: str) -> None:
    entries: dict[str, bytes] = {}
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                check_path(member.filename)
                if member.file_size > 10_000_000:
                    raise ValueError("oversized artifact member")
                entries[member.filename] = archive.read(member)
        prefix = "mcp_releem/"
        metadata = [body for name, body in entries.items() if name.endswith(".dist-info/METADATA")]
    else:
        with tarfile.open(path, "r:gz") as archive:
            for tar_member in archive:
                check_path(tar_member.name)
                if tar_member.isdir():
                    continue
                if not tar_member.isfile() or tar_member.size > 10_000_000:
                    raise ValueError("unsupported artifact member")
                stream = archive.extractfile(tar_member)
                if stream is None:
                    raise ValueError("unreadable artifact member")
                name = tar_member.name.partition("/")[2]
                entries[name] = stream.read()
        prefix = "src/mcp_releem/"
        metadata = [body for name, body in entries.items() if name == "PKG-INFO"]
    if not all(prefix + name in entries for name in REQUIRED):
        raise ValueError("missing required module")
    if module_version(entries[prefix + "__init__.py"].decode()) != version:
        raise ValueError("module version mismatch")
    if len(metadata) != 1:
        raise ValueError("missing package metadata")
    parsed = email.parser.BytesParser().parsebytes(metadata[0])
    if parsed["Version"] != version or parsed["Name"] != "mcp-releem":
        raise ValueError("metadata version or name mismatch")
    for name, body in entries.items():
        if name.startswith(prefix) and name.endswith(".py") and b"dbharness" in body:
            raise ValueError("legacy harness content")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--dirty", choices=["true", "false"], required=True)
    parser.add_argument("--lock-hash", required=True)
    args = parser.parse_args()
    directory: Path = args.directory
    wheels = list(directory.glob("*.whl"))
    sdists = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("expected exactly one wheel and sdist")
    for artifact in wheels + sdists:
        audit_archive(artifact, args.version)
    image = json.loads((directory / "image-inspect.json").read_text())[0]
    hosted_inspect = directory / "hosted-image-inspect.json"
    hosted = json.loads(hosted_inspect.read_text())[0] if hosted_inspect.exists() else None
    files = sorted(p for p in directory.iterdir() if p.is_file())
    sums = {path.name: checksum(path) for path in files}
    receipt = {
        "status": "verified",
        "verified_at": datetime.now(UTC).isoformat(),
        "version": args.version,
        "source_revision": args.revision,
        "source_dirty": args.dirty == "true",
        "lock_sha256": args.lock_hash,
        "image_id": image["Id"],
        "os": image["Os"],
        "architecture": image["Architecture"],
        "delivery": "uncommitted developer preview" if args.dirty == "true" else "local candidate",
        "files": sums,
    }
    source_manifest = directory / "source-manifest.json"
    if source_manifest.exists():
        receipt["source_tree_sha256"] = json.loads(source_manifest.read_text())[
            "source_tree_sha256"
        ]
    security_report = directory / "security-report.json"
    receipt["security_audit"] = "not run"
    if security_report.exists():
        audit = json.loads(security_report.read_text())
        archive = directory / "hosted-image.tar"
        if (
            audit.get("status") != "passed"
            or hosted is None
            or audit.get("image_id") != hosted["Id"]
            or not archive.is_file()
            or audit.get("archive_sha256") != checksum(archive)
        ):
            raise ValueError("Security report is stale or does not match candidate")
        receipt["security_audit"] = "passed"
    if hosted is not None:
        receipt.update(
            {
                "hosted_image_id": hosted["Id"],
                "hosted_os": hosted["Os"],
                "hosted_architecture": hosted["Architecture"],
            }
        )
    receipt_path = directory / "verification.json"
    pending = directory / "verification.pending"
    with pending.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    sums[receipt_path.name] = checksum(pending)
    with (directory / "SHA256SUMS").open("x") as stream:
        stream.writelines(f"{digest}  {name}\n" for name, digest in sorted(sums.items()))
    pending.rename(receipt_path)


if __name__ == "__main__":
    main()
