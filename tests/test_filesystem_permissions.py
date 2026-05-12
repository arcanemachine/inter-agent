from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path

import pytest

from inter_agent.core.server import run_server
from inter_agent.core.shared import (
    data_dir,
    identity_path,
    load_or_create_token,
    pid_path,
    token_path,
    write_server_identity,
)

pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="POSIX mode assertions require POSIX-compatible filesystem permissions",
)

HOST = "127.0.0.1"


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_data_dir_tightens_existing_directory_permissions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tmp_path.chmod(0o755)
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    path = data_dir()

    assert path == tmp_path
    assert file_mode(path) == 0o700


def test_token_identity_and_pid_files_are_owner_read_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    load_or_create_token()
    write_server_identity(HOST, unused_tcp_port)

    assert file_mode(token_path()) == 0o600
    assert file_mode(identity_path(unused_tcp_port)) == 0o600
    assert file_mode(pid_path(unused_tcp_port)) == 0o600


@pytest.mark.asyncio
async def test_server_start_preserves_restrictive_permissions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    deadline = asyncio.get_running_loop().time() + 1
    while asyncio.get_running_loop().time() < deadline:
        if identity_path(unused_tcp_port).exists():
            break
        await asyncio.sleep(0.01)
    else:
        raise TimeoutError("server identity metadata was not created")

    try:
        assert file_mode(tmp_path) == 0o700
        assert file_mode(token_path()) == 0o600
        assert file_mode(identity_path(unused_tcp_port)) == 0o600
        assert file_mode(pid_path(unused_tcp_port)) == 0o600
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
