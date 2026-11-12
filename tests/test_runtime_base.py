"""The lean container must retain every non-SQLite Python shared-library dependency."""

import importlib.util
from pathlib import Path

import pytest


def requirements(installed):
    path = Path(__file__).parents[1] / "tools/containers/runtime_base.py"
    spec = importlib.util.spec_from_file_location("runtime_base", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.requirements(installed)


def test_keep_required_libraries_and_drop_sqlite_only():
    installed = (
        "P:other\nD:unrelated\n\nP:.python-rundeps\n"
        "D:so:libssl.so.3 so:libsqlite3.so.0 so:libffi.so.8\n"
    )
    assert requirements(installed) == ["so:libssl.so.3", "so:libffi.so.8"]


@pytest.mark.parametrize(
    "installed",
    [
        "P:other\nD:so:libsqlite3.so.0\n",
        "P:.python-rundeps\nD:so:libssl.so.3\n",
        "P:.python-rundeps\n",
    ],
)
def test_unknown_base_dependency_layout_fails_closed(installed):
    with pytest.raises(ValueError):
        requirements(installed)
