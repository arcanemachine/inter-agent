from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture
def fake_uv(tmp_path: Path) -> Path:
    uv = tmp_path / "uv"
    uv.write_text('#!/bin/sh\necho "$@"\n', encoding="utf-8")
    uv.chmod(0o755)
    return tmp_path


def _run_wrapper(
    repo_root: Path, fake_uv_dir: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    env = {"PATH": f"{fake_uv_dir}:{os.environ.get('PATH', '')}"}
    return subprocess.run(
        [str(repo_root / "inter-agent"), *args],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )


def test_help_shows_generic_and_harness_commands(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv)
    assert result.returncode == 0
    assert "Generic commands:" in result.stdout
    assert "Harness commands:" in result.stdout
    assert "start" in result.stdout
    assert "kick <name>" in result.stdout
    assert "pi send" in result.stdout
    assert "claude broadcast" in result.stdout


def test_unknown_command_exits_with_error(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "unknown")
    assert result.returncode == 2
    assert "Unknown command: unknown" in result.stderr


def test_start_delegates_to_inter_agent_server(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "start", "--idle-timeout", "60")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-server --idle-timeout 60"


def test_list_delegates_to_inter_agent_list(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "list")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-list"


def test_status_delegates_to_inter_agent_status(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "status", "--json")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-status --json"


def test_stop_delegates_to_inter_agent_shutdown(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "stop")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-shutdown"


def test_kick_delegates_to_inter_agent_kick(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "kick", "y")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-kick y"


def test_pi_send_delegates_to_pi_adapter(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "pi", "send", "b", "hello")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-pi send b hello"


def test_pi_broadcast_delegates_to_pi_adapter(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "pi", "broadcast", "hello all")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-pi broadcast hello all"


def test_claude_send_delegates_to_claude_adapter(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "claude", "send", "b", "hello")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-claude send b hello"


def test_claude_broadcast_delegates_to_claude_adapter(repo_root: Path, fake_uv: Path) -> None:
    result = _run_wrapper(repo_root, fake_uv, "claude", "broadcast", "hello all")
    assert result.returncode == 0
    assert result.stdout.strip() == "run inter-agent-claude broadcast hello all"
