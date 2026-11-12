import json
import os
import subprocess
import sys

import pytest
from test_foundation import module


def test_secret_key_alias_and_ambiguity():
    settings = module("config").Settings
    configured = settings.from_env({"RELEEM_SECRET_KEY": "synthetic-secret"})
    assert configured.token.get_secret_value() == "synthetic-secret"
    assert "synthetic-secret" not in repr(configured)
    for other in ("RELEEM_API_TOKEN", "RELEEM_API_TOKEN_FILE"):
        with pytest.raises(ValueError):
            settings.from_env({"RELEEM_SECRET_KEY": "synthetic-secret", other: "other"})


def test_explicit_env_file_no_interpolation_or_secret_output(tmp_path):
    path = tmp_path / "test.env"
    path.write_text("RELEEM_SECRET_KEY='synthetic-${HOME}-secret'\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("RELEEM_")}
    result = subprocess.run(  # noqa: S603 - fixed interpreter and temporary test file
        [sys.executable, "-m", "mcp_releem", "--env-file", str(path), "--check"],
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["token_configured"] is True
    assert "synthetic-" not in result.stdout + result.stderr
    loaded = module("env_file").read_env_file(str(path), {})
    assert loaded["RELEEM_SECRET_KEY"] == "synthetic-${HOME}-secret"  # noqa: S105 - synthetic credential
    missing = subprocess.run(
        [sys.executable, "-m", "mcp_releem", "--check"],
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
        cwd=tmp_path,
    )
    assert missing.returncode == 2


def test_env_file_rejects_malformed_and_oversized_files(tmp_path):
    loader = module("env_file").read_env_file
    path = tmp_path / "bad.env"
    for content in ["broken='unterminated", "x" * 65537]:
        path.write_text(content)
        with pytest.raises(ValueError):
            loader(str(path), {})
    with pytest.raises(ValueError):
        loader(str(tmp_path / "missing"), {})
