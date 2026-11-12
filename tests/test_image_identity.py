"""Bind scan identity to content-addressed Docker archive metadata."""

import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest


def checker():
    path = Path(__file__).parents[1] / "tools/release/image_identity.py"
    spec = importlib.util.spec_from_file_location("image_identity", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.config_identity


def archive(tmp_path: Path) -> tuple[Path, str, str]:
    config = b'{"architecture":"amd64"}'
    config_id = "sha256:" + hashlib.sha256(config).hexdigest()
    manifest = json.dumps({"config": {"digest": config_id}}).encode()
    manifest_id = "sha256:" + hashlib.sha256(manifest).hexdigest()
    index = json.dumps({"manifests": [{"digest": manifest_id}]}).encode()
    index_id = "sha256:" + hashlib.sha256(index).hexdigest()
    data = {
        "manifest.json": json.dumps([{"Config": "blobs/sha256/" + config_id[7:]}]).encode(),
        "blobs/sha256/" + config_id[7:]: config,
        "blobs/sha256/" + manifest_id[7:]: manifest,
        "blobs/sha256/" + index_id[7:]: index,
    }
    path = tmp_path / "image.tar"
    with tarfile.open(path, "w") as target:
        for name, body in data.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            target.addfile(info, io.BytesIO(body))
    return path, config_id, index_id


def test_legacy_config_and_oci_index_bind_to_same_config(tmp_path: Path) -> None:
    path, config_id, index_id = archive(tmp_path)
    check = checker()
    assert check(path, config_id) == config_id
    assert check(path, index_id) == config_id


def test_unrelated_image_id_fails_closed(tmp_path: Path) -> None:
    path, _, _ = archive(tmp_path)
    with pytest.raises(ValueError):
        checker()(path, "sha256:" + "a" * 64)
