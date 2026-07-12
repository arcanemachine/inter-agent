import asyncio
import json
from collections.abc import AsyncIterable

import pytest

from inter_agent.core.auth import AUTH_METHOD
from inter_agent.core.client import AgentSession, build_hello
from inter_agent.core.shared import control_hello, validate_name

_CLOSED = object()


class FakeWebSocket:
    def __init__(self) -> None:
        self._recv_queue: asyncio.Queue[str | object] = asyncio.Queue()
        self.sent: list[str] = []
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        item = await self._recv_queue.get()
        if item is _CLOSED:
            raise StopAsyncIteration
        return item  # type: ignore[return-value]

    def inject(self, message: str) -> None:
        self._recv_queue.put_nowait(message)

    def close_reader(self) -> None:
        self._recv_queue.put_nowait(_CLOSED)

    def __aiter__(self) -> "FakeWebSocket":
        return self

    async def __anext__(self) -> str:
        item = await self._recv_queue.get()
        if item is _CLOSED:
            raise StopAsyncIteration
        return item  # type: ignore[return-value]

    async def close(self) -> None:
        self.closed = True


async def _open_session(session: AgentSession, ws: FakeWebSocket) -> None:
    session._ws = ws  # type: ignore[assignment]
    await session._inbox.put(json.dumps({"op": "welcome", "assigned_name": session.name}))
    session._reader_task = asyncio.create_task(session._reader_loop())
    await asyncio.sleep(0)


async def _collect_frames(
    session: AgentSession, frames: list[dict[str, object]], count: int
) -> None:
    async for frame in session:
        frames.append(json.loads(frame))
        if len(frames) >= count:
            break


def test_build_hello_payload() -> None:
    payload = build_hello("sess-1", "agent-a")
    assert payload["op"] == "hello"
    assert payload["role"] == "agent"
    auth = payload["auth"]
    assert isinstance(auth, dict)
    assert auth["method"] == AUTH_METHOD
    assert isinstance(auth["client_nonce"], str)
    assert "token" not in payload
    assert "label" not in payload


def test_build_hello_payload_with_label() -> None:
    payload = build_hello("sess-1", "agent-a", "Agent A")
    assert payload["label"] == "Agent A"


def test_control_hello_payload() -> None:
    payload = control_hello("ctl-1")
    assert payload["op"] == "hello"
    assert payload["role"] == "control"
    assert "token" not in payload


def test_validate_name() -> None:
    assert validate_name("agent-a")
    assert not validate_name("Agent-A")


def test_agent_session_is_async_context_manager() -> None:
    session = AgentSession("127.0.0.1", 16837, "agent-a")
    assert session.__aenter__ is not None
    assert session.__aexit__ is not None
    assert isinstance(session, AsyncIterable)


@pytest.mark.asyncio
async def test_agent_session_routes_response_installed_before_send() -> None:
    session = AgentSession("127.0.0.1", 16837, "agent-a")
    ws = FakeWebSocket()

    original_send = ws.send

    async def send_and_inject(message: str) -> None:
        await original_send(message)
        ws.inject(json.dumps({"op": "subscribe_ok", "channel": "updates"}))

    ws.send = send_and_inject  # type: ignore[method-assign]

    await _open_session(session, ws)
    try:
        response = await asyncio.wait_for(session.subscribe("updates"), timeout=0.5)
    finally:
        await session._close()

    assert response == {"op": "subscribe_ok", "channel": "updates"}


@pytest.mark.asyncio
async def test_agent_session_buffers_unrelated_frame_before_command_response() -> None:
    session = AgentSession("127.0.0.1", 16837, "agent-a")
    ws = FakeWebSocket()

    original_send = ws.send

    async def send_and_inject(message: str) -> None:
        await original_send(message)
        ws.inject(json.dumps({"op": "msg", "text": "buffered"}))
        ws.inject(json.dumps({"op": "subscribe_ok", "channel": "updates"}))

    ws.send = send_and_inject  # type: ignore[method-assign]

    await _open_session(session, ws)
    frames: list[dict[str, object]] = []
    try:
        collect_task = asyncio.create_task(_collect_frames(session, frames, count=2))
        await asyncio.sleep(0)
        response = await asyncio.wait_for(session.subscribe("updates"), timeout=0.5)
        await asyncio.wait_for(collect_task, timeout=0.5)
    finally:
        await session._close()

    assert response == {"op": "subscribe_ok", "channel": "updates"}
    assert len(frames) == 2
    assert frames[0]["op"] == "welcome"
    assert frames[1]["op"] == "msg"
    assert frames[1]["text"] == "buffered"


@pytest.mark.asyncio
async def test_agent_session_delivers_eof_when_reader_closes() -> None:
    session = AgentSession("127.0.0.1", 16837, "agent-a")
    ws = FakeWebSocket()
    ws.close_reader()

    await _open_session(session, ws)

    frames: list[dict[str, object]] = []
    async for frame in session:
        frames.append(json.loads(frame))

    await session._close()

    assert len(frames) == 1
    assert frames[0]["op"] == "welcome"


@pytest.mark.asyncio
async def test_agent_session_eof_delivery_is_idempotent() -> None:
    session = AgentSession("127.0.0.1", 16837, "agent-a")
    ws = FakeWebSocket()
    ws.close_reader()

    await _open_session(session, ws)

    frames: list[dict[str, object]] = []
    async for frame in session:
        frames.append(json.loads(frame))

    await session._close()
    await session._close()

    assert len(frames) == 1
