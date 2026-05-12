from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, connect_agent, running_server, send_json

from inter_agent.core.errors import ErrorCode


@pytest.mark.asyncio
async def test_duplicate_active_session_id_is_rejected_without_displacing_original(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as original,
            websockets.connect(context.url) as duplicate,
        ):
            await connect_agent(original, context, "same-session", "agent-a")
            err = await send_json(
                duplicate,
                agent_hello(
                    context.token,
                    session_id="same-session",
                    name="agent-b",
                ),
            )
            pong = await send_json(original, {"op": "ping"})

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.SESSION_TAKEN.value
    assert pong == {"op": "pong"}


@pytest.mark.asyncio
async def test_session_id_can_reconnect_after_disconnect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as first:
            await connect_agent(first, context, "same-session", "agent-a")
        await asyncio.sleep(0.05)

        async with websockets.connect(context.url) as second:
            welcome = await send_json(
                second,
                agent_hello(
                    context.token,
                    session_id="same-session",
                    name="agent-a",
                ),
            )

    assert welcome["op"] == "welcome"
    assert welcome["session_id"] == "same-session"
    assert welcome["assigned_name"] == "agent-a"
