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

from inter_agent.core.auth import client_handshake
from inter_agent.core.channels import ChannelInfo, ChannelsResult, list_channels
from inter_agent.core.client import AgentSession, build_hello, iter_client_frames
from inter_agent.core.kick import kick_session
from inter_agent.core.list import SessionInfo, list_sessions
from inter_agent.core.publish import publish_to_channel
from inter_agent.core.send import broadcast_message, send_direct_message
from inter_agent.core.server import run_server
from inter_agent.core.shared import resolve_shared_secret

HOST = "127.0.0.1"


@dataclass(frozen=True)
class ServerContext:
    host: str
    port: int
    token: str

    @property
    def secret(self) -> str:
        return self.token

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
    token = resolve_shared_secret().secret
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
    response: object = json.loads(
        await client_handshake(ws, context.secret, build_hello(session_id, name, label))
    )
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


@pytest.mark.asyncio
async def test_kick_session_by_name_disconnects_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as target:
            await connect_agent(target, context, "b", "agent-b")

            result = await kick_session(context.host, context.port, name="agent-b")

            with pytest.raises(websockets.ConnectionClosed):
                await target.recv()

    assert result.response_payload["op"] == "kick_ok"
    assert result.response_payload["name"] == "agent-b"


@pytest.mark.asyncio
async def test_kick_session_unknown_target_returns_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        result = await kick_session(context.host, context.port, name="ghost")

    assert result.response_payload["op"] == "error"
    assert result.response_payload["code"] == "UNKNOWN_TARGET"


def test_kick_session_requires_name_or_session_id() -> None:
    with pytest.raises(ValueError, match="name or session_id"):
        asyncio.run(kick_session(HOST, 16837))


@pytest.mark.asyncio
async def test_agent_session_yields_welcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    welcome: object | None = None
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with AgentSession(context.host, context.port, "agent-a") as session:
            async for frame in session:
                welcome = json.loads(frame)
                break

    assert isinstance(welcome, dict)
    assert welcome["op"] == "welcome"
    assert welcome["assigned_name"] == "agent-a"


@pytest.mark.asyncio
async def test_agent_session_subscribes_receives_publishes_unsubscribes_and_disconnects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    received: list[dict[str, object]] = []
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with AgentSession(context.host, context.port, "agent-a") as session:

            async def collect() -> None:
                async for frame in session:
                    payload = json.loads(frame)
                    received.append(payload)
                    if len(received) >= 2:
                        break

            collect_task = asyncio.create_task(collect())
            await asyncio.sleep(0.05)

            subscribe_response = await session.subscribe("updates")
            await publish_to_channel(context.host, context.port, "updates", "hello subscribers")
            await asyncio.wait_for(collect_task, timeout=1.0)
            unsubscribe_response = await session.unsubscribe("updates")

    assert received[0]["op"] == "welcome"
    assert received[1]["op"] == "msg"
    assert received[1]["channel"] == "updates"
    assert received[1]["text"] == "hello subscribers"
    assert subscribe_response == {"op": "subscribe_ok", "channel": "updates"}
    assert unsubscribe_response == {"op": "unsubscribe_ok", "channel": "updates"}


@pytest.mark.asyncio
async def test_agent_session_subscribe_error_reaches_caller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with AgentSession(context.host, context.port, "agent-a") as session:
            response = await session.subscribe("Bad Channel!")

    assert response["op"] == "error"
    assert response["code"] == "BAD_CHANNEL"


@pytest.mark.asyncio
async def test_agent_session_unsubscribe_error_reaches_caller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with AgentSession(context.host, context.port, "agent-a") as session:
            response = await session.unsubscribe("not-subscribed")

    assert response["op"] == "error"
    assert response["code"] == "NOT_SUBSCRIBED"


@pytest.mark.asyncio
async def test_agent_session_publish_error_reaches_caller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with AgentSession(context.host, context.port, "agent-a") as session:
            response = await session.publish("unknown-channel", "hello")

    assert response is not None
    assert response["op"] == "error"
    assert response["code"] == "UNKNOWN_CHANNEL"


@pytest.mark.asyncio
async def test_agent_session_buffers_inbound_frames_during_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    received: list[dict[str, object]] = []
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with AgentSession(context.host, context.port, "agent-a") as session:

            async def collect() -> None:
                async for frame in session:
                    payload = json.loads(frame)
                    received.append(payload)
                    if len(received) >= 2:
                        break

            collect_task = asyncio.create_task(collect())
            await asyncio.sleep(0.05)

            subscribe_task = asyncio.create_task(session.subscribe("updates"))
            await asyncio.sleep(0.05)

            await send_direct_message(context.host, context.port, "agent-a", "during subscribe")
            subscribe_response = await subscribe_task
            await asyncio.wait_for(collect_task, timeout=1.0)

    assert received[0]["op"] == "welcome"
    assert received[1]["op"] == "msg"
    assert received[1]["text"] == "during subscribe"
    assert subscribe_response["op"] == "subscribe_ok"
    assert subscribe_response["channel"] == "updates"


@pytest.mark.asyncio
async def test_agent_session_concurrent_instances_remain_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    received_a: list[dict[str, object]] = []
    received_b: list[dict[str, object]] = []
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            AgentSession(context.host, context.port, "agent-a") as session_a,
            AgentSession(context.host, context.port, "agent-b") as session_b,
        ):

            async def collect(received: list[dict[str, object]], session: AgentSession) -> None:
                async for frame in session:
                    payload = json.loads(frame)
                    received.append(payload)
                    if len(received) >= 2:
                        break

            task_a = asyncio.create_task(collect(received_a, session_a))
            task_b = asyncio.create_task(collect(received_b, session_b))
            await asyncio.sleep(0.05)

            await session_a.subscribe("channel-a")
            await session_b.subscribe("channel-b")
            await publish_to_channel(context.host, context.port, "channel-a", "msg-a")
            await publish_to_channel(context.host, context.port, "channel-b", "msg-b")
            await asyncio.wait_for(asyncio.gather(task_a, task_b), timeout=1.0)

    assert received_a[0]["op"] == "welcome"
    assert received_a[0]["assigned_name"] == "agent-a"
    assert received_b[0]["op"] == "welcome"
    assert received_b[0]["assigned_name"] == "agent-b"
    assert len(received_a) == 2
    assert received_a[1]["channel"] == "channel-a"
    assert received_a[1]["text"] == "msg-a"
    assert len(received_b) == 2
    assert received_b[1]["channel"] == "channel-b"
    assert received_b[1]["text"] == "msg-b"


@pytest.mark.asyncio
async def test_publish_to_channel_delivers_to_subscribers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as subscriber:
            await connect_agent(subscriber, context, "a", "agent-a")
            await subscriber.send(json.dumps({"op": "subscribe", "channel": "updates"}))
            subscribe_response: object = json.loads(await subscriber.recv())
            assert isinstance(subscribe_response, dict)
            assert subscribe_response["op"] == "subscribe_ok"

            result = await publish_to_channel(
                context.host, context.port, "updates", "hello subscribers"
            )
            delivered: object = json.loads(await subscriber.recv())

    assert result.welcome_payload["op"] == "welcome"
    assert result.error is None
    assert isinstance(delivered, dict)
    assert delivered["op"] == "msg"
    assert delivered["channel"] == "updates"
    assert delivered["text"] == "hello subscribers"


@pytest.mark.asyncio
async def test_publish_to_channel_unknown_channel_returns_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        result = await publish_to_channel(
            context.host, context.port, "missing", "hello subscribers"
        )

    assert result.welcome_payload["op"] == "welcome"
    assert result.error is not None
    assert result.error.code == "UNKNOWN_CHANNEL"


def test_publish_to_channel_rejects_invalid_channel_name() -> None:
    with pytest.raises(ValueError, match="invalid channel name"):
        asyncio.run(publish_to_channel(HOST, 16837, "Bad Channel!", "hello"))


@pytest.mark.asyncio
async def _subscribe(ws: ClientConnection, channel: str) -> None:
    await ws.send(json.dumps({"op": "subscribe", "channel": channel}))
    response: object = json.loads(await ws.recv())
    assert isinstance(response, dict)
    assert response["op"] == "subscribe_ok"


async def test_list_channels_returns_structured_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as agent:
            await connect_agent(agent, context, "a", "agent-a", "Agent A")
            await _subscribe(agent, "news")
            await _subscribe(agent, "alerts")

            result = await list_channels(context.host, context.port)

    assert isinstance(result, ChannelsResult)
    assert result.response["op"] == "channels_ok"
    assert result.channels == (
        ChannelInfo(name="alerts", subscribers=("agent-a",)),
        ChannelInfo(name="news", subscribers=("agent-a",)),
    )
    assert json.loads(result.raw_response) == {
        "op": "channels_ok",
        "channels": [
            {"name": "alerts", "subscribers": ["agent-a"]},
            {"name": "news", "subscribers": ["agent-a"]},
        ],
    }


@pytest.mark.asyncio
async def test_list_channels_empty_when_no_subscriptions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port):
        result = await list_channels(HOST, unused_tcp_port)

    assert result.response["op"] == "channels_ok"
    assert result.channels == ()


@pytest.mark.asyncio
async def test_list_channels_error_response_is_preserved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    import inter_agent.core.channels as channels_module

    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        monkeypatch.setattr(
            channels_module,
            "_json_object",
            lambda raw: {"op": "error", "code": "TEST_ERROR"},
        )

        error_result = await list_channels(context.host, context.port)

    assert error_result.response["op"] == "error"
    assert error_result.response["code"] == "TEST_ERROR"
    assert error_result.channels == ()
