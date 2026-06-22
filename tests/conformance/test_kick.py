from __future__ import annotations

from pathlib import Path

import pytest
import websockets
from helpers import connect_agent, connect_control, running_server, send_json

from inter_agent.core.errors import ErrorCode


@pytest.mark.asyncio
async def test_kick_by_name_disconnects_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with (
            websockets.connect(ctx.url) as agent,
            websockets.connect(ctx.url) as control,
        ):
            await connect_agent(agent, ctx, session_id="a", name="agent-a")
            await connect_control(control, ctx)

            response = await send_json(control, {"op": "kick", "name": "agent-a"})

            assert response["op"] == "kick_ok"
            assert response["name"] == "agent-a"
            assert response["session_id"] == "a"

            with pytest.raises(websockets.ConnectionClosed):
                await agent.recv()


@pytest.mark.asyncio
async def test_kick_by_session_id_disconnects_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with (
            websockets.connect(ctx.url) as agent,
            websockets.connect(ctx.url) as control,
        ):
            await connect_agent(agent, ctx, session_id="sid-b", name="agent-b")
            await connect_control(control, ctx)

            response = await send_json(control, {"op": "kick", "session_id": "sid-b"})

            assert response["op"] == "kick_ok"
            assert response["session_id"] == "sid-b"
            assert response["name"] == "agent-b"

            with pytest.raises(websockets.ConnectionClosed):
                await agent.recv()


@pytest.mark.asyncio
async def test_kick_requires_control_role(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with (
            websockets.connect(ctx.url) as kicker,
            websockets.connect(ctx.url) as victim,
        ):
            await connect_agent(kicker, ctx, session_id="k", name="kicker")
            await connect_agent(victim, ctx, session_id="v", name="victim")

            response = await send_json(kicker, {"op": "kick", "name": "victim"})

            assert response["op"] == "error"
            assert response["code"] == ErrorCode.BAD_ROLE.value


@pytest.mark.asyncio
async def test_kick_unknown_target_returns_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with websockets.connect(ctx.url) as control:
            await connect_control(control, ctx)

            response = await send_json(control, {"op": "kick", "name": "ghost"})

            assert response["op"] == "error"
            assert response["code"] == ErrorCode.UNKNOWN_TARGET.value


@pytest.mark.asyncio
async def test_kick_without_target_returns_protocol_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with websockets.connect(ctx.url) as control:
            await connect_control(control, ctx)

            response = await send_json(control, {"op": "kick"})

            assert response["op"] == "error"
            assert response["code"] == ErrorCode.PROTOCOL_ERROR.value


@pytest.mark.asyncio
async def test_kicked_session_no_longer_listed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with (
            websockets.connect(ctx.url) as agent,
            websockets.connect(ctx.url) as control,
        ):
            await connect_agent(agent, ctx, session_id="a", name="agent-a")
            await connect_control(control, ctx)

            await send_json(control, {"op": "kick", "name": "agent-a"})
            with pytest.raises(websockets.ConnectionClosed):
                await agent.recv()

            list_response = await send_json(control, {"op": "list"})
            sessions = list_response["sessions"]
            assert isinstance(sessions, list)
            names = {s["name"] for s in sessions}
            assert "agent-a" not in names
