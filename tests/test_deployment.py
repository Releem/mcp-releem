"""Exercise deployment failure boundaries with a synthetic Docker command."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "ghcr.io/releem/releem-mcp-server@sha256:" + "a" * 64


def run_deploy(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["/bin/sh", str(ROOT / "deploy/activate.sh"), *args],
        env={**os.environ, "MCP_DEPLOY_ROOT": str(tmp_path / "host")},
        capture_output=True,
        text=True,
        check=False,
    )


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
    (previous / "hosted.env").write_text("MCP_RELEEM_IMAGE=old\n")
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


def test_public_recovery_uses_cached_private_image(tmp_path: Path) -> None:
    root = tmp_path / "host"
    previous = root / "releases/old"
    previous.mkdir(parents=True)
    current = root / "releases/new"
    current.mkdir()
    (root / ".managed-by-mcp-releem").touch()
    (previous / "compose.yaml").write_text("services: {}\n")
    (previous / "hosted.env").write_text(f"MCP_RELEEM_IMAGE={IMAGE}\n")
    (root / "previous").symlink_to(previous)
    (root / "current").symlink_to(current)
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
    commands = log.read_text().splitlines()
    assert not any(command.startswith("pull ") for command in commands)
    assert (root / "current/hosted.env").read_text().find(IMAGE) >= 0


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
