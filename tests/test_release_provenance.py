import importlib.util
from pathlib import Path


def test_manifest_is_deterministic_sensitive_files_excluded_and_changes_detected(tmp_path):
    path = Path(__file__).parents[1] / "tools/release/provenance.py"
    spec = importlib.util.spec_from_file_location("release_provenance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in module.FILES:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic")
    source = tmp_path / "src/mcp_releem/core.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("VERSION=1")
    before = module.manifest(tmp_path)
    (tmp_path / ".env").write_text("never read")
    assert module.manifest(tmp_path) == before
    source.write_text("VERSION=2")
    assert module.manifest(tmp_path)["source_tree_sha256"] != before["source_tree_sha256"]
    source.unlink()
    source.symlink_to(tmp_path / ".env")
    import pytest

    with pytest.raises(ValueError):
        module.manifest(tmp_path)
