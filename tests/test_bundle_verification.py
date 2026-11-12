import hashlib
import importlib.util
from pathlib import Path

import pytest


def test_bundle_verification_detects_tampering_and_unsafe_paths(tmp_path):
    path = Path(__file__).parents[1] / "tools/release/verify_bundle.py"
    spec = importlib.util.spec_from_file_location("verify_bundle", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    content = b"synthetic artifact"
    (tmp_path / "image.tar").write_bytes(content)
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(hashlib.sha256(content).hexdigest() + "  image.tar\n")
    assert module.verify(tmp_path) == 1
    (tmp_path / "image.tar").write_bytes(b"changed")
    with pytest.raises(ValueError):
        module.verify(tmp_path)
    sums.write_text(hashlib.sha256(content).hexdigest() + "  ../outside\n")
    with pytest.raises(ValueError):
        module.verify(tmp_path)
