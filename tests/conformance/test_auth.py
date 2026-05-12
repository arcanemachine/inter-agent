from __future__ import annotations

from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, running_server, send_json

from inter_agent.core.errors import ErrorCode


@pytest.mark.asyncio
async def test_auth_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            err = await send_json(ws, agent_hello("wrong"))

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value
