"""Hash explicit release inputs; never read credentials or the Git directory."""

import hashlib
import json
import sys
from pathlib import Path

FILES = (
    "Dockerfile",
    ".dockerignore",
    "compose.yaml",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "scripts/check-release.sh",
    "scripts/check-security.sh",
    "deploy/hosted.env.example",
    "deploy/activate.sh",
    "deploy/recover.sh",
    "deploy/bootstrap.sh",
    "deploy/ssh-deploy.sh",
    "deploy/start-tunnel.sh",
    "deploy/stack.sh",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy.yml",
    "tests/fixtures/openapi/releem-openapi-2026-11-10.json",
    "tests/fixtures/openapi/releem-openapi-2026-11-11.json",
    "tests/fixtures/openapi/releem-openapi-production-2026-11-19.json",
)
TREES = ("src/mcp_releem", "tests", "tools/release", "tools/containers")
SUFFIXES = {".py", ".sh"}


def manifest(root: Path) -> dict[str, object]:
    paths = {root / name for name in FILES}
    for tree in TREES:
        paths.update(p for p in (root / tree).rglob("*") if p.suffix in SUFFIXES)
    entries = {}
    for path in sorted(paths):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or linked release input")
        entries[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {
        "algorithm": "sha256",
        "source_tree_sha256": hashlib.sha256(encoded).hexdigest(),
        "files": entries,
    }


if __name__ == "__main__":
    print(json.dumps(manifest(Path(sys.argv[1])), sort_keys=True, indent=2))
