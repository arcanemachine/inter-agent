from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import pytest

from inter_agent.core.server import run_server
from inter_agent.core.shared import load_or_create_token

HOST = "127.0.0.1"


@dataclass(frozen=True)
class LiveServer:
    host: str
    port: int
    token: str

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"


@pytest.fixture
async def live_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> AsyncIterator[LiveServer]:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    server = LiveServer(host=HOST, port=unused_tcp_port, token=token)
    task = asyncio.create_task(run_server(server.host, server.port))
    await asyncio.sleep(0.1)
    try:
        yield server
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
