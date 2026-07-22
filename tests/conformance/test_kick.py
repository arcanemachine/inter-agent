from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import websockets
from helpers import connect_agent, connect_control, recv_json, running_server, send_json

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

            # The target receives a terminal KICKED error before the close.
            kicked = await recv_json(agent)
            assert kicked["op"] == "error"
            assert kicked["code"] == ErrorCode.KICKED.value
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

            kicked = await recv_json(agent)
            assert kicked["op"] == "error"
            assert kicked["code"] == ErrorCode.KICKED.value
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
            kicked = await recv_json(agent)
            assert kicked["op"] == "error"
            assert kicked["code"] == ErrorCode.KICKED.value
            with pytest.raises(websockets.ConnectionClosed):
                await agent.recv()

            list_response = await send_json(control, {"op": "list"})
            sessions = list_response["sessions"]
            assert isinstance(sessions, list)
            names = {s["name"] for s in sessions}
            assert "agent-a" not in names


@pytest.mark.asyncio
async def test_kick_sends_bounded_kicked_error_without_metadata(
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

            kicked = await recv_json(agent)
            assert kicked["op"] == "error"
            assert kicked["code"] == ErrorCode.KICKED.value
            # The KICKED message must not expose controller identity, the
            # target's private session metadata, or the shared secret.
            assert kicked["message"] == "removed by kick"
            assert "from" not in kicked
            assert "from_name" not in kicked
            assert "session_id" not in kicked
            assert "secret" not in kicked


@pytest.mark.asyncio
async def test_kick_rejects_control_target_without_closing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with (
            websockets.connect(ctx.url) as target,
            websockets.connect(ctx.url) as kicker,
        ):
            await connect_control(target, ctx, session_id="ctl-target")
            await connect_control(kicker, ctx, session_id="ctl-kicker")

            response = await send_json(kicker, {"op": "kick", "session_id": "ctl-target"})

            assert response["op"] == "error"
            assert response["code"] == ErrorCode.BAD_ROLE.value

            # The targeted control connection is rejected, not closed; it stays usable.
            list_response = await send_json(target, {"op": "list"})
            assert list_response["op"] == "list_ok"


@pytest.mark.asyncio
async def test_kick_late_close_keeps_newer_same_name_agent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with (
            websockets.connect(ctx.url) as control,
            websockets.connect(ctx.url) as old_agent,
        ):
            await connect_agent(old_agent, ctx, session_id="old", name="shared")
            await connect_control(control, ctx)

            await send_json(control, {"op": "kick", "name": "shared"})
            await recv_json(old_agent)  # KICKED
            # Let the kicked socket's server-side cleanup run.
            await asyncio.sleep(0.05)

            # The name is immediately free: a new session claims the same name
            # under a different session id.
            async with websockets.connect(ctx.url) as new_agent:
                await connect_agent(new_agent, ctx, session_id="new", name="shared")
                # Allow any late cleanup from the old socket to race; the newer
                # same-name connection must remain registered.
                await asyncio.sleep(0.05)
                list_response = await send_json(control, {"op": "list"})
                sessions = list_response["sessions"]
                assert isinstance(sessions, list)
                shared = [s for s in sessions if s["name"] == "shared"]
                assert len(shared) == 1
                assert shared[0]["session_id"] == "new"

                # The newer connection is still usable.
                own_list = await send_json(new_agent, {"op": "list"})
                assert own_list["op"] == "list_ok"


@pytest.mark.asyncio
async def test_kicked_name_can_register_again_immediately(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as ctx:
        async with (
            websockets.connect(ctx.url) as control,
            websockets.connect(ctx.url) as agent,
        ):
            await connect_agent(agent, ctx, session_id="a", name="reuse-me")
            await connect_control(control, ctx)

            await send_json(control, {"op": "kick", "name": "reuse-me"})
            await recv_json(agent)  # KICKED
            with pytest.raises(websockets.ConnectionClosed):
                await agent.recv()

        # The name is free immediately; a fresh connection reclaims it.
        async with websockets.connect(ctx.url) as reused:
            welcome = await connect_agent(reused, ctx, session_id="b", name="reuse-me")
            assert welcome["op"] == "welcome"
            assert welcome["assigned_name"] == "reuse-me"
