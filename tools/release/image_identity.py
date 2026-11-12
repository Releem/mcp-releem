"""Resolve a Docker image ID to its config through verified archive descriptors."""

import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path
from typing import Any


def config_identity(path: Path, identifier: str) -> str:
    def valid(value: str) -> str:
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", value):
            raise ValueError("Invalid image digest")
        return value

    with tarfile.open(path) as archive:
        names = [member.name for member in archive.getmembers()]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive members")

        def read(name: str) -> bytes:
            try:
                member = archive.getmember(name)
            except KeyError:
                raise ValueError("Image descriptor missing from archive") from None
            if not member.isfile() or member.size > 1024 * 1024:
                raise ValueError("Invalid image metadata member")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Unreadable image metadata")
            return stream.read()

        manifests = json.loads(read("manifest.json"))
        if len(manifests) != 1:
            raise ValueError("Require one runtime platform per image archive")
        config = read(manifests[0]["Config"])
        expected = "sha256:" + hashlib.sha256(config).hexdigest()
        visited: set[str] = set()

        def reachable(digest: str) -> bool:
            valid(digest)
            if digest == expected:
                return True
            if digest in visited or len(visited) >= 10:
                raise ValueError("Image descriptor graph exceeds bounds")
            visited.add(digest)
            body = read("blobs/sha256/" + digest[7:])
            if "sha256:" + hashlib.sha256(body).hexdigest() != digest:
                raise ValueError("Image descriptor digest mismatch")
            node: dict[str, Any] = json.loads(body)
            if "config" in node:
                return valid(node["config"]["digest"]) == expected
            return any(reachable(child["digest"]) for child in node.get("manifests", []))

        if not reachable(valid(identifier)):
            raise ValueError("Image ID does not reference archive runtime config")
        return expected


if __name__ == "__main__":
    print(config_identity(Path(sys.argv[1]), sys.argv[2]))
