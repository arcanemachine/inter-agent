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
    verify_server_identity,
    verify_server_identity_details,
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
        "instance_nonce": identity.instance_nonce,
        "process_start_marker": identity.process_start_marker,
    }
    assert json.loads(pid_path(unused_tcp_port).read_text(encoding="utf-8")) == {
        "state_version": STATE_VERSION,
        "pid": os.getpid(),
        "instance_nonce": identity.instance_nonce,
    }
    assert file_mode(tmp_path) == 0o700
    assert file_mode(identity_path(unused_tcp_port)) == 0o600
    assert file_mode(pid_path(unused_tcp_port)) == 0o600
    assert not list(tmp_path.glob("*.tmp"))


def test_verify_server_identity_rejects_missing_and_mismatched_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    assert not verify_server_identity(HOST, unused_tcp_port)
    assert verify_server_identity_details(HOST, unused_tcp_port).reason == "missing_metadata"

    write_server_identity(HOST, unused_tcp_port)

    assert verify_server_identity(HOST, unused_tcp_port)
    assert not verify_server_identity("localhost", unused_tcp_port)
    details = verify_server_identity_details("localhost", unused_tcp_port)
    assert details.reason == "endpoint_mismatch"


def test_verify_server_identity_rejects_pid_metadata_nonce_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    identity = write_server_identity(HOST, unused_tcp_port)
    pid_path(unused_tcp_port).write_text(
        json.dumps(
            {
                "state_version": STATE_VERSION,
                "pid": identity.pid,
                "instance_nonce": "different-nonce",
            }
        ),
        encoding="utf-8",
    )

    details = verify_server_identity_details(HOST, unused_tcp_port)

    assert not details.ok
    assert details.reason == "pid_metadata_mismatch"


def test_verify_server_identity_rejects_process_marker_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(shared, "process_start_marker", lambda pid: "start-a")
    write_server_identity(HOST, unused_tcp_port)
    monkeypatch.setattr(shared, "process_start_marker", lambda pid: "start-b")

    details = verify_server_identity_details(HOST, unused_tcp_port)

    assert not details.ok
    assert details.reason == "process_marker_mismatch"


def test_verify_server_identity_allows_documented_marker_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(shared, "process_start_marker", lambda pid: None)
    write_server_identity(HOST, unused_tcp_port)

    assert verify_server_identity(HOST, unused_tcp_port)


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
                "instance_nonce": "stale-nonce",
                "process_start_marker": None,
            }
        ),
        encoding="utf-8",
    )
    pid_path(unused_tcp_port).write_text(
        json.dumps(
            {
                "state_version": STATE_VERSION,
                "pid": stale_pid,
                "instance_nonce": "stale-nonce",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(shared, "is_pid_alive", lambda pid: pid != stale_pid)

    identity = claim_server_state(HOST, unused_tcp_port)

    payload = json.loads(identity_path(unused_tcp_port).read_text(encoding="utf-8"))
    assert identity.pid == os.getpid()
    assert payload["pid"] == os.getpid()
    pid_payload = json.loads(pid_path(unused_tcp_port).read_text(encoding="utf-8"))
    assert pid_payload["pid"] == os.getpid()
    assert pid_payload["instance_nonce"] == identity.instance_nonce


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
