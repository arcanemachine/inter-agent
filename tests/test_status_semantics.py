from __future__ import annotations

import json
from pathlib import Path

import pytest
import websockets
from conftest import LiveServer
from websockets.asyncio.server import ServerConnection

from inter_agent.core.shared import token_path, write_server_identity
from inter_agent.core.status import check_server_status

HOST = "127.0.0.1"


@pytest.mark.asyncio
async def test_status_reports_auth_failure(live_server: LiveServer) -> None:
    token_path().write_text("wrong-token\n", encoding="utf-8")

    status = await check_server_status(live_server.host, live_server.port)

    assert status.state == "auth_failed"
    assert status.identity_verified is True
    assert status.reachable is True
    assert status.message == "server authentication failed"


@pytest.mark.asyncio
async def test_status_reports_protocol_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    write_server_identity(HOST, unused_tcp_port)

    async def handler(ws: ServerConnection) -> None:
        _ = await ws.recv()
        await ws.send(json.dumps({"op": "unexpected"}))

    async with websockets.serve(handler, HOST, unused_tcp_port):
        status = await check_server_status(HOST, unused_tcp_port)

    assert status.state == "protocol_mismatch"
    assert status.identity_verified is True
    assert status.reachable is True
    assert status.message == "server returned an unexpected status response"


@pytest.mark.asyncio
async def test_status_reports_unreachable_with_verified_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    write_server_identity(HOST, unused_tcp_port)

    status = await check_server_status(HOST, unused_tcp_port, timeout=0.1)

    assert status.state == "unavailable"
    assert status.identity_verified is True
    assert status.reachable is False
    assert status.message == "server connection failed"
