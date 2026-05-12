from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import cast

import pytest
import websockets
from helpers import (
    assert_no_message,
    connect_agent,
    connect_control,
    recv_json,
    running_server,
    send_json,
)
from websockets.asyncio.client import ClientConnection


def _sessions(response: dict[str, object]) -> list[dict[str, object]]:
    sessions = response["sessions"]
    assert isinstance(sessions, list)
    return cast(list[dict[str, object]], sessions)


async def _wait_for_sessions(
    ws: ClientConnection,
    expected: list[dict[str, object]],
) -> None:
    deadline = asyncio.get_running_loop().time() + 1
    last: list[dict[str, object]] = []
    while asyncio.get_running_loop().time() < deadline:
        response = await send_json(ws, {"op": "list"})
        assert response["op"] == "list_ok"
        last = _sessions(response)
        if last == expected:
            return
        await asyncio.sleep(0.02)
    assert last == expected


@pytest.mark.asyncio
async def test_handshake_and_direct_send(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as b,
        ):
            welcome_a = await connect_agent(a, context, "a", "agent-a")
            welcome_b = await connect_agent(b, context, "b", "agent-b")

            assert welcome_a["assigned_name"] == "agent-a"
            assert welcome_b["assigned_name"] == "agent-b"
            assert "capabilities" in welcome_a

            await a.send(json.dumps({"op": "send", "to": "agent-b", "text": "hi"}))
            msg = await recv_json(b)

    assert msg["op"] == "msg"
    assert msg["from"] == "a"
    assert msg["from_name"] == "agent-a"
    assert msg["to"] == "agent-b"
    assert msg["text"] == "hi"


@pytest.mark.asyncio
async def test_ping_pong(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            pong = await send_json(ws, {"op": "ping"})

    assert pong == {"op": "pong"}


@pytest.mark.asyncio
async def test_bye_removes_session_from_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as agent,
            websockets.connect(context.url) as control,
        ):
            await connect_agent(agent, context, "a", "agent-a")
            await connect_control(control, context)
            await agent.send(json.dumps({"op": "bye"}))
            await _wait_for_sessions(control, [])


@pytest.mark.asyncio
async def test_list_reports_agents_to_agent_and_control_roles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    expected = [
        {"session_id": "a", "name": "agent-a", "label": "Agent A"},
        {"session_id": "b", "name": "agent-b", "label": None},
    ]

    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as b,
            websockets.connect(context.url) as control,
        ):
            await connect_agent(a, context, "a", "agent-a", "Agent A")
            await connect_agent(b, context, "b", "agent-b")
            await connect_control(control, context)

            control_list = await send_json(control, {"op": "list"})
            agent_list = await send_json(a, {"op": "list"})

    assert control_list["op"] == "list_ok"
    assert agent_list["op"] == "list_ok"
    assert _sessions(control_list) == expected
    assert _sessions(agent_list) == expected


@pytest.mark.asyncio
async def test_list_is_sorted_by_name_and_excludes_control_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    expected = [
        {"session_id": "a", "name": "agent-a", "label": None},
        {"session_id": "b", "name": "agent-b", "label": None},
    ]

    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as b,
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as control,
        ):
            await connect_agent(b, context, "b", "agent-b")
            await connect_agent(a, context, "a", "agent-a")
            await connect_control(control, context)

            response = await send_json(control, {"op": "list"})

    assert response["op"] == "list_ok"
    assert _sessions(response) == expected


@pytest.mark.asyncio
async def test_broadcast_excludes_sender_and_control_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as b,
            websockets.connect(context.url) as control,
        ):
            await connect_agent(a, context, "a", "agent-a")
            await connect_agent(b, context, "b", "agent-b")
            await connect_control(control, context)

            await a.send(json.dumps({"op": "broadcast", "text": "all"}))
            bmsg = await recv_json(b)
            await assert_no_message(a)
            await assert_no_message(control)

    assert bmsg["op"] == "msg"
    assert bmsg["from"] == "a"
    assert "to" not in bmsg
    assert bmsg["text"] == "all"


@pytest.mark.asyncio
async def test_custom_broadcast_excludes_sender_and_control_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as b,
            websockets.connect(context.url) as control,
        ):
            await connect_agent(a, context, "a", "agent-a")
            await connect_agent(b, context, "b", "agent-b")
            await connect_control(control, context)

            await a.send(
                json.dumps(
                    {
                        "op": "custom",
                        "custom_type": "x.unknown.v1",
                        "payload": {"k": "v"},
                    }
                )
            )
            bmsg = await recv_json(b)
            await assert_no_message(a)
            await assert_no_message(control)

    assert bmsg["op"] == "msg"
    assert bmsg["from"] == "a"
    assert bmsg["custom_type"] == "x.unknown.v1"
    assert bmsg["payload"] == {"k": "v"}
    assert "to" not in bmsg
