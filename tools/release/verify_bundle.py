"""Verify candidate checksums before installing or loading any artifact."""

import hashlib
import sys
from pathlib import Path


def verify(root: Path) -> int:
    entries = (root / "SHA256SUMS").read_text().splitlines()
    if not entries:
        raise ValueError("Missing checksum entries")
    seen = set()
    for row in entries:
        digest, name = row.split("  ", 1)
        if (
            Path(name).name != name
            or name in {".", ".."}
            or name in seen
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("Invalid checksum entry")
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or linked artifact")
        actual = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                actual.update(chunk)
        if actual.hexdigest() != digest:
            raise ValueError("Artifact checksum mismatch")
        seen.add(name)
    return len(seen)


if __name__ == "__main__":
    print(f"Verified {verify(Path(sys.argv[1]))} candidate checksums")
