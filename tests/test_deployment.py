"""Exercise deployment failure boundaries with a synthetic Docker command."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "ghcr.io/releem/releem-mcp-server@sha256:" + "a" * 64
OTHER_IMAGE = "ghcr.io/releem/releem-mcp-server@sha256:" + "b" * 64


def run_deploy(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["/bin/sh", str(ROOT / "deploy/activate.sh"), *args],
        env={**os.environ, "MCP_DEPLOY_ROOT": str(tmp_path / "host")},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def docker_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    log = tmp_path / "commands"
    docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$DEPLOY_TEST_LOG"\n'
        'if test "$1" = compose && test "$4" = --env-file && test "$8" = up; then\n'
        "    image=$(sed -n 's/^MCP_RELEEM_IMAGE=//p' \"$5\")\n"
        "    api=$(sed -n 's/^RELEEM_API_BASE_URL=//p' \"$5\")\n"
        '    printf "effective %s %s\\n" "${MCP_RELEEM_IMAGE-$image}" '
        '"${RELEEM_API_BASE_URL-$api}" >> "$DEPLOY_TEST_LOG"\n'
        "fi\n"
    )
    docker.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv("DEPLOY_TEST_LOG", str(log))
    return log


def test_dry_run_does_not_create_host_files(tmp_path: Path) -> None:
    result = run_deploy(tmp_path, "--dry-run", IMAGE, str(ROOT / "compose.yaml"))
    assert result.returncode == 0, result.stderr
    assert "mcp.releem.com" in result.stdout
    assert not (tmp_path / "host").exists()


def test_mutable_image_rejected_before_writes(tmp_path: Path) -> None:
    result = run_deploy(tmp_path, "--apply", "ghcr.io/releem/releem-mcp-server:latest", "x")
    assert result.returncode != 0
    assert "immutable" in result.stderr
    assert not (tmp_path / "host").exists()


def test_failed_activation_recovers_previous_release(tmp_path: Path) -> None:
    root = tmp_path / "host"
    previous = root / "releases/previous"
    previous.mkdir(parents=True)
    (root / ".managed-by-mcp-releem").touch()
    (previous / "compose.yaml").write_text("services: {}\n")
    (previous / "hosted.env").write_text(
        f"MCP_RELEEM_IMAGE={IMAGE}\nRELEEM_API_BASE_URL=https://api2.dev.releem.com\n"
    )
    (root / "current").symlink_to(previous)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$DEPLOY_TEST_LOG"\n'
        'case " $* " in *" up "*) case "$*" in *previous*) ;; *) exit 1;; esac;; esac\n'
    )
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    result = subprocess.run(  # noqa: S603
        ["/bin/sh", str(ROOT / "deploy/activate.sh"), "--apply", IMAGE, str(ROOT / "compose.yaml")],
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "MCP_DEPLOY_ROOT": str(root),
            "DEPLOY_TEST_LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert (root / "current").resolve() == previous
    assert "previous/compose.yaml up" in log.read_text()
    assert "Previous release recovered" in result.stderr


def test_public_failure_stops_first_release(tmp_path: Path) -> None:
    root = tmp_path / "host"
    release = root / "releases/first"
    release.mkdir(parents=True)
    (release / "compose.yaml").write_text("services: {}\n")
    (release / "hosted.env").write_text("MCP_RELEEM_IMAGE=old\n")
    (root / "current").symlink_to(release)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    log = tmp_path / "commands"
    docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$DEPLOY_TEST_LOG"\n')
    docker.chmod(0o755)
    result = subprocess.run(  # noqa: S603
        ["/bin/sh", str(ROOT / "deploy/recover.sh"), str(ROOT / "deploy/activate.sh")],
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "MCP_DEPLOY_ROOT": str(root),
            "DEPLOY_TEST_LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "stop mcp" in log.read_text()
    assert "First release stopped" in result.stdout


def recovery_state(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "host"
    previous = root / "releases/old"
    previous.mkdir(parents=True)
    current = root / "releases/new"
    current.mkdir()
    (root / ".managed-by-mcp-releem").touch()
    (previous / "compose.yaml").write_text("services: {}\n")
    (previous / "hosted.env").write_text(
        f"MCP_RELEEM_IMAGE={IMAGE}\n"
        "RELEEM_API_BASE_URL=https://api2.dev.releem.com\n"
        "RELEEM_MCP_PUBLIC_URL=https://mcp.releem.com/mcp\n"
        "RELEEM_MCP_REQUESTS_PER_MINUTE=30\n"
    )
    (root / "previous").symlink_to(previous)
    (root / "current").symlink_to(current)
    return root, previous, current


def test_public_recovery_restores_cached_image_and_upstream(
    tmp_path: Path, docker_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, previous, current = recovery_state(tmp_path)
    (root / "secrets").mkdir()
    (root / "secrets/tunnel-token").write_text("synthetic-token")
    monkeypatch.setenv("MCP_RELEEM_IMAGE", OTHER_IMAGE)
    monkeypatch.setenv("RELEEM_API_BASE_URL", "https://api2.releem.com")
    result = subprocess.run(  # noqa: S603
        ["/bin/sh", str(ROOT / "deploy/recover.sh"), str(ROOT / "deploy/activate.sh")],
        env={**os.environ, "MCP_DEPLOY_ROOT": str(root)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    commands = docker_env.read_text().splitlines()
    assert not any(command.startswith("pull ") for command in commands)
    assert f"image inspect {IMAGE}" in commands
    assert [command.rsplit(" ", 1)[-1] for command in commands if " up " in command] == ["mcp"]
    assert f"effective {IMAGE} https://api2.dev.releem.com" in commands
    assert (root / "previous").resolve() == current
    assert (root / "current/compose.yaml").read_text() == (previous / "compose.yaml").read_text()
    assert (root / "current/hosted.env").read_text() == (
        (previous / "hosted.env").read_text() + "COMPOSE_PROFILES=tunnel\n"
    )


@pytest.mark.parametrize(
    "invalid",
    [
        "missing-env",
        "foreign-env",
        "foreign-compose",
        "foreign-release",
        "image",
        "duplicate-image",
        "missing-origin",
        "duplicate-origin",
        "multiline-shadow",
    ],
)
def test_recovery_rejects_inconsistent_saved_release(
    tmp_path: Path, docker_env: Path, invalid: str
) -> None:
    root, previous, current = recovery_state(tmp_path)
    saved_env = previous / "hosted.env"
    compose = previous / "compose.yaml"
    image = IMAGE
    if invalid == "missing-env":
        saved_env.unlink()
    elif invalid == "foreign-env":
        (current / "hosted.env").write_text(saved_env.read_text())
        saved_env = current / "hosted.env"
    elif invalid == "foreign-compose":
        compose = ROOT / "compose.yaml"
    elif invalid == "foreign-release":
        external = tmp_path / "external"
        previous.rename(external)
        (root / "previous").unlink()
        (root / "previous").symlink_to(external)
        previous = external
        saved_env = previous / "hosted.env"
        compose = previous / "compose.yaml"
    elif invalid == "image":
        image = OTHER_IMAGE
    elif invalid == "duplicate-image":
        with saved_env.open("a") as target:
            target.write(f"export MCP_RELEEM_IMAGE = {OTHER_IMAGE}\n")
    elif invalid == "missing-origin":
        saved_env.write_text(f"MCP_RELEEM_IMAGE={IMAGE}\n")
    elif invalid == "duplicate-origin":
        with saved_env.open("a") as target:
            target.write("export RELEEM_API_BASE_URL = https://api2.releem.com\n")
    elif invalid == "multiline-shadow":
        saved_env.write_text(
            "OTHER_SETTING='first line\n"
            f"MCP_RELEEM_IMAGE={IMAGE}\n"
            "RELEEM_API_BASE_URL=https://api2.dev.releem.com\n"
            "last line'\n"
        )
    result = run_deploy(tmp_path, "--apply", image, str(compose), str(saved_env))
    assert result.returncode != 0
    assert (root / "current").resolve() == current
    assert (root / "previous").resolve() == previous
    assert sorted(path.name for path in (root / "releases").iterdir()) == (
        ["new"] if invalid == "foreign-release" else ["new", "old"]
    )
    assert not (root / "deploy.lock").exists()
    assert not docker_env.exists() or docker_env.read_text().splitlines() == ["compose version"]


def test_fresh_release_uses_production_origin(tmp_path: Path, docker_env: Path) -> None:
    result = run_deploy(tmp_path, "--apply", IMAGE, str(ROOT / "compose.yaml"))
    assert result.returncode == 0, result.stderr
    assert (
        "RELEEM_API_BASE_URL=https://api2.releem.com\n"
        in (tmp_path / "host/current/hosted.env").read_text()
    )
    assert f"effective {IMAGE} https://api2.releem.com" in docker_env.read_text().splitlines()


def test_application_update_preserves_tunnel_profile_and_targets_only_mcp(tmp_path: Path) -> None:
    root = tmp_path / "host"
    (root / "secrets").mkdir(parents=True)
    (root / ".managed-by-mcp-releem").touch()
    (root / "secrets/tunnel-token").write_text("synthetic-token")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    log = tmp_path / "commands"
    docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$DEPLOY_TEST_LOG"\n')
    docker.chmod(0o755)
    result = subprocess.run(  # noqa: S603
        ["/bin/sh", str(ROOT / "deploy/activate.sh"), "--apply", IMAGE, str(ROOT / "compose.yaml")],
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "MCP_DEPLOY_ROOT": str(root),
            "DEPLOY_TEST_LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "COMPOSE_PROFILES=tunnel" in (root / "current/hosted.env").read_text()
    commands = [line for line in log.read_text().splitlines() if " up " in line]
    assert commands and all(command.endswith(" mcp") for command in commands)
