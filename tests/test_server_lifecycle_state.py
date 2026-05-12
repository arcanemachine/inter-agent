from __future__ import annotations

import asyncio
import json
import os
import stat
from pathlib import Path

import pytest

import inter_agent.core.shared as shared
from inter_agent.core.server import run_server
from inter_agent.core.shared import (
    STATE_VERSION,
    ServerAlreadyRunningError,
    claim_server_state,
    identity_path,
    pid_path,
    write_server_identity,
)

HOST = "127.0.0.1"


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_write_server_identity_writes_complete_restrictive_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    identity = write_server_identity(HOST, unused_tcp_port)

    payload = json.loads(identity_path(unused_tcp_port).read_text(encoding="utf-8"))
    assert payload == {
        "state_version": STATE_VERSION,
        "pid": os.getpid(),
        "host": HOST,
        "port": unused_tcp_port,
        "started_at": identity.started_at,
    }
    assert pid_path(unused_tcp_port).read_text(encoding="utf-8") == f"{os.getpid()}\n"
    assert file_mode(tmp_path) == 0o700
    assert file_mode(identity_path(unused_tcp_port)) == 0o600
    assert file_mode(pid_path(unused_tcp_port)) == 0o600
    assert not list(tmp_path.glob("*.tmp"))


def test_claim_server_state_rejects_live_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    write_server_identity(HOST, unused_tcp_port)

    with pytest.raises(ServerAlreadyRunningError, match="server already running"):
        claim_server_state(HOST, unused_tcp_port)


def test_claim_server_state_removes_stale_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    stale_pid = 123456
    identity_path(unused_tcp_port).write_text(
        json.dumps(
            {
                "state_version": STATE_VERSION,
                "pid": stale_pid,
                "host": HOST,
                "port": unused_tcp_port,
                "started_at": "stale",
            }
        ),
        encoding="utf-8",
    )
    pid_path(unused_tcp_port).write_text(f"{stale_pid}\n", encoding="utf-8")
    monkeypatch.setattr(shared, "is_pid_alive", lambda pid: pid != stale_pid)

    identity = claim_server_state(HOST, unused_tcp_port)

    payload = json.loads(identity_path(unused_tcp_port).read_text(encoding="utf-8"))
    assert identity.pid == os.getpid()
    assert payload["pid"] == os.getpid()
    assert pid_path(unused_tcp_port).read_text(encoding="utf-8") == f"{os.getpid()}\n"


async def wait_for_path(path: Path) -> None:
    deadline = asyncio.get_running_loop().time() + 1
    while asyncio.get_running_loop().time() < deadline:
        if path.exists():
            return
        await asyncio.sleep(0.01)
    raise TimeoutError(f"timed out waiting for {path}")


@pytest.mark.asyncio
async def test_run_server_rejects_second_live_server_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    identity_file = identity_path(unused_tcp_port)
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_path(identity_file)

    try:
        with pytest.raises(ServerAlreadyRunningError, match="server already running"):
            await run_server(HOST, unused_tcp_port)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert not identity_file.exists()
    assert not pid_path(unused_tcp_port).exists()
