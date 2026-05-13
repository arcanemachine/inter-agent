from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

import pytest
import websockets
from websockets.asyncio.client import ClientConnection

from inter_agent.core.client import build_hello, iter_client_frames
from inter_agent.core.list import SessionInfo, list_sessions
from inter_agent.core.send import broadcast_message, send_direct_message
from inter_agent.core.server import run_server
from inter_agent.core.shared import load_or_create_token

HOST = "127.0.0.1"


@dataclass(frozen=True)
class ServerContext:
    host: str
    port: int
    token: str

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"


@asynccontextmanager
async def running_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> AsyncIterator[ServerContext]:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    context = ServerContext(host=HOST, port=unused_tcp_port, token=token)
    task = asyncio.create_task(run_server(context.host, context.port))
    await asyncio.sleep(0.1)
    try:
        yield context
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def connect_agent(
    ws: ClientConnection,
    context: ServerContext,
    session_id: str,
    name: str,
    label: str | None = None,
) -> None:
    await ws.send(json.dumps(build_hello(context.token, session_id, name, label)))
    response: object = json.loads(await ws.recv())
    assert isinstance(response, dict)
    assert response["op"] == "welcome"


@pytest.mark.asyncio
async def test_iter_client_frames_yields_welcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    welcome: object | None = None
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        frames = iter_client_frames(context.host, context.port, "agent-a", "Agent A")
        try:
            welcome = json.loads(await anext(frames))
        finally:
            await frames.aclose()

    assert isinstance(welcome, dict)
    assert welcome["op"] == "welcome"
    assert welcome["assigned_name"] == "agent-a"


@pytest.mark.asyncio
async def test_list_sessions_returns_structured_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as agent:
            await connect_agent(agent, context, "a", "agent-a", "Agent A")

            result = await list_sessions(context.host, context.port)

    assert result.response["op"] == "list_ok"
    assert result.sessions == (SessionInfo(session_id="a", name="agent-a", label="Agent A"),)
    assert json.loads(result.raw_response) == result.response


@pytest.mark.asyncio
async def test_send_direct_message_delivers_to_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as target:
            await connect_agent(target, context, "b", "agent-b")

            result = await send_direct_message(context.host, context.port, "agent-b", "hello")
            delivered: object = json.loads(await target.recv())

    assert result.welcome_payload["op"] == "welcome"
    assert isinstance(delivered, dict)
    assert delivered["op"] == "msg"
    assert delivered["to"] == "agent-b"
    assert delivered["text"] == "hello"


@pytest.mark.asyncio
async def test_broadcast_message_delivers_to_agent_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as agent_a,
            websockets.connect(context.url) as agent_b,
        ):
            await connect_agent(agent_a, context, "a", "agent-a")
            await connect_agent(agent_b, context, "b", "agent-b")

            result = await broadcast_message(context.host, context.port, "hello all")
            delivered_a: object = json.loads(await agent_a.recv())
            delivered_b: object = json.loads(await agent_b.recv())

    assert result.welcome_payload["op"] == "welcome"
    assert isinstance(delivered_a, dict)
    assert isinstance(delivered_b, dict)
    assert delivered_a["text"] == "hello all"
    assert delivered_b["text"] == "hello all"


@pytest.mark.asyncio
async def test_send_direct_message_with_from_name_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as target:
            await connect_agent(target, context, "b", "agent-b")

            result = await send_direct_message(
                context.host, context.port, "agent-b", "hello", from_name="agent-a"
            )
            delivered: object = json.loads(await target.recv())

    assert result.welcome_payload["op"] == "welcome"
    assert isinstance(delivered, dict)
    assert delivered["op"] == "msg"
    assert delivered["to"] == "agent-b"
    assert delivered["text"] == "hello"
    assert delivered["from_name"] == "agent-a"


@pytest.mark.asyncio
async def test_broadcast_message_with_from_name_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as agent_a,
            websockets.connect(context.url) as agent_b,
        ):
            await connect_agent(agent_a, context, "a", "agent-a")
            await connect_agent(agent_b, context, "b", "agent-b")

            result = await broadcast_message(
                context.host, context.port, "hello all", from_name="agent-a"
            )
            delivered_a: object = json.loads(await agent_a.recv())
            delivered_b: object = json.loads(await agent_b.recv())

    assert result.welcome_payload["op"] == "welcome"
    assert isinstance(delivered_a, dict)
    assert isinstance(delivered_b, dict)
    assert delivered_a["from_name"] == "agent-a"
    assert delivered_b["from_name"] == "agent-a"
