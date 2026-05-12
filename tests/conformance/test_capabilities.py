from __future__ import annotations

from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, connect_agent, connect_control, running_server, send_json

BASELINE_CAPABILITIES = {
    "core": {"version": "0.1"},
    "channels": False,
    "rate_limit": False,
}


@pytest.mark.asyncio
async def test_agent_welcome_returns_baseline_server_capabilities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            welcome = await connect_agent(ws, context, "a", "agent-a")

    assert welcome["capabilities"] == BASELINE_CAPABILITIES


@pytest.mark.asyncio
async def test_control_welcome_returns_baseline_server_capabilities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            welcome = await connect_control(ws, context)

    assert welcome["capabilities"] == BASELINE_CAPABILITIES


@pytest.mark.asyncio
async def test_unknown_client_capabilities_do_not_break_handshake(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    client_capabilities = {
        "core": {"version": "0.1"},
        "channels": True,
        "rate_limit": True,
        "x.example.experimental": {"enabled": True},
    }

    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            welcome = await send_json(
                ws,
                agent_hello(
                    context.token,
                    session_id="a",
                    name="agent-a",
                    capabilities=client_capabilities,
                ),
            )

    assert welcome["op"] == "welcome"
    assert welcome["capabilities"] == BASELINE_CAPABILITIES
