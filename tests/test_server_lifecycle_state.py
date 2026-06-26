from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from inter_agent.core.server import run_server
from inter_agent.core.shared import token_path

HOST = "127.0.0.1"


@pytest.mark.asyncio
async def test_run_server_rejects_second_live_server_by_bind_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await asyncio.sleep(0.1)

    try:
        with pytest.raises(OSError):
            await run_server(HOST, unused_tcp_port)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


def test_no_server_lifecycle_metadata_paths_are_created(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    assert token_path().name == "token"
    assert not list(tmp_path.glob("server.*.meta"))
    assert not list(tmp_path.glob("server.*.pid"))
    assert not list(tmp_path.glob("server.*.shutdown"))
