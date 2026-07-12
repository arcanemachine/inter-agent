from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import websockets
from helpers import (
    assert_no_message,
    connect_agent,
    connect_control,
    publish,
    recv_json,
    request_channels,
    running_server,
    subscribe,
    unsubscribe,
)

from inter_agent.core.errors import ErrorCode
from inter_agent.core.shared import Limits


@pytest.mark.asyncio
async def test_subscribe_returns_subscribe_ok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            response = await subscribe(ws, "build")

    assert response == {"op": "subscribe_ok", "channel": "build"}


@pytest.mark.asyncio
async def test_subscribe_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            first = await subscribe(ws, "build")
            second = await subscribe(ws, "build")

    assert first == {"op": "subscribe_ok", "channel": "build"}
    assert second == {"op": "subscribe_ok", "channel": "build"}


@pytest.mark.asyncio
async def test_unsubscribe_returns_unsubscribe_ok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            await subscribe(ws, "build")
            response = await unsubscribe(ws, "build")

    assert response == {"op": "unsubscribe_ok", "channel": "build"}


@pytest.mark.asyncio
async def test_unsubscribe_without_subscription_returns_not_subscribed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            response = await unsubscribe(ws, "build")

    assert response["op"] == "error"
    assert response["code"] == ErrorCode.NOT_SUBSCRIBED.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "channel",
    [
        123,
        "",
        "-bad",
        "Bad",
        "bad_",
        "a" * 41,
    ],
)
async def test_subscribe_rejects_invalid_channel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    channel: object,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            response = await subscribe(ws, channel)  # type: ignore[arg-type]

    assert response["op"] == "error"
    assert response["code"] == ErrorCode.BAD_CHANNEL.value


@pytest.mark.asyncio
async def test_subscribe_rejects_channel_over_byte_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(channel_name_max=4)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            ok = await subscribe(ws, "abcd")
            over = await subscribe(ws, "abcde")

    assert ok == {"op": "subscribe_ok", "channel": "abcd"}
    assert over["op"] == "error"
    assert over["code"] == ErrorCode.BAD_CHANNEL.value


@pytest.mark.asyncio
async def test_agent_publish_delivers_to_subscribers_except_sender(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as publisher,
            websockets.connect(context.url) as subscriber,
        ):
            await connect_agent(publisher, context, "a", "agent-a")
            await connect_agent(subscriber, context, "b", "agent-b")
            await subscribe(publisher, "build")
            await subscribe(subscriber, "build")
            err = await publish(publisher, "build", "hello")
            assert err is None
            msg = await recv_json(subscriber)
            await assert_no_message(publisher)

    assert msg["op"] == "msg"
    assert msg["from"] == "a"
    assert msg["from_name"] == "agent-a"
    assert msg["text"] == "hello"
    assert msg["channel"] == "build"
    assert "to" not in msg
    assert "msg_id" in msg
    assert "ts" in msg


@pytest.mark.asyncio
async def test_control_publish_delivers_to_subscribers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as control,
            websockets.connect(context.url) as subscriber,
        ):
            await connect_control(control, context)
            await connect_agent(subscriber, context, "b", "agent-b")
            await subscribe(subscriber, "build")
            err = await publish(control, "build", "hello", from_name="ci")
            assert err is None
            msg = await recv_json(subscriber)

    assert msg["op"] == "msg"
    assert msg["from_name"] == "ci"
    assert msg["text"] == "hello"
    assert msg["channel"] == "build"


@pytest.mark.asyncio
async def test_publish_to_unknown_channel_returns_unknown_channel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            err = await publish(ws, "build", "hello")

    assert err is not None
    assert err["op"] == "error"
    assert err["code"] == ErrorCode.UNKNOWN_CHANNEL.value


@pytest.mark.asyncio
async def test_publish_text_must_be_string(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            await subscribe(ws, "build")
            err = await publish(ws, "build", 123)  # type: ignore[arg-type]

    assert err is not None
    assert err["op"] == "error"
    assert err["code"] == ErrorCode.BAD_TEXT.value


@pytest.mark.asyncio
async def test_publish_text_size_is_limited_by_broadcast_max(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    exact = "éé"
    over = "ééx"
    limit = len(exact.encode("utf-8"))
    limits = Limits(broadcast_text_max=limit)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as target,
        ):
            await connect_agent(sender, context, "a", "agent-a")
            await connect_agent(target, context, "b", "agent-b")
            await subscribe(sender, "build")
            await subscribe(target, "build")

            await sender.send(json.dumps({"op": "publish", "channel": "build", "text": exact}))
            delivered = await recv_json(target)
            await assert_no_message(sender)

            err = await publish(sender, "build", over)
            await assert_no_message(target)

    assert delivered["op"] == "msg"
    assert delivered["text"] == exact
    assert err is not None
    assert err["op"] == "error"
    assert err["code"] == ErrorCode.TEXT_TOO_LARGE.value


@pytest.mark.asyncio
async def test_publish_does_not_deliver_to_unsubscribed_agents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as publisher,
            websockets.connect(context.url) as subscribed,
            websockets.connect(context.url) as unsubscribed,
        ):
            await connect_agent(publisher, context, "a", "agent-a")
            await connect_agent(subscribed, context, "b", "agent-b")
            await connect_agent(unsubscribed, context, "c", "agent-c")
            await subscribe(publisher, "build")
            await subscribe(subscribed, "build")
            err = await publish(publisher, "build", "hello")
            assert err is None
            msg = await recv_json(subscribed)
            await assert_no_message(unsubscribed)

    assert msg["text"] == "hello"


@pytest.mark.asyncio
async def test_multiple_subscribers_receive_publish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as publisher,
            websockets.connect(context.url) as first,
            websockets.connect(context.url) as second,
        ):
            await connect_agent(publisher, context, "a", "agent-a")
            await connect_agent(first, context, "b", "agent-b")
            await connect_agent(second, context, "c", "agent-c")
            await subscribe(publisher, "build")
            await subscribe(first, "build")
            await subscribe(second, "build")
            err = await publish(publisher, "build", "hello")
            assert err is None
            msg_first = await recv_json(first)
            msg_second = await recv_json(second)

    assert msg_first["text"] == "hello"
    assert msg_second["text"] == "hello"
    assert msg_first["msg_id"]
    assert msg_first["msg_id"] == msg_second["msg_id"]


@pytest.mark.asyncio
async def test_session_subscription_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(subscriptions_max=2)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            await subscribe(ws, "one")
            await subscribe(ws, "two")
            err = await subscribe(ws, "three")

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.CHANNEL_LIMIT_REACHED.value


@pytest.mark.asyncio
async def test_server_channel_limit_blocks_new_channel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(channels_max=1)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with (
            websockets.connect(context.url) as first,
            websockets.connect(context.url) as second,
        ):
            await connect_agent(first, context, "a", "agent-a")
            await connect_agent(second, context, "b", "agent-b")
            await subscribe(first, "build")
            ok = await subscribe(second, "build")
            err = await subscribe(second, "deploy")

    assert ok == {"op": "subscribe_ok", "channel": "build"}
    assert err["op"] == "error"
    assert err["code"] == ErrorCode.CHANNEL_LIMIT_REACHED.value


@pytest.mark.asyncio
async def test_channels_is_control_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            response = await request_channels(ws)

    assert response["op"] == "error"
    assert response["code"] == ErrorCode.BAD_ROLE.value


@pytest.mark.asyncio
async def test_control_channels_returns_sorted_channels_and_subscribers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as control,
            websockets.connect(context.url) as zebra,
            websockets.connect(context.url) as alpha,
        ):
            await connect_control(control, context)
            await connect_agent(zebra, context, "z", "zebra")
            await connect_agent(alpha, context, "a", "alpha")
            await subscribe(zebra, "build")
            await subscribe(alpha, "build")
            await subscribe(alpha, "alerts")
            response = await request_channels(control)

    assert response["op"] == "channels_ok"
    assert response["channels"] == [
        {"name": "alerts", "subscribers": ["alpha"]},
        {"name": "build", "subscribers": ["alpha", "zebra"]},
    ]


@pytest.mark.asyncio
async def test_control_subscribe_and_unsubscribe_return_bad_role(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_control(ws, context)
            sub = await subscribe(ws, "build")
            unsub = await unsubscribe(ws, "build")

    assert sub["op"] == "error"
    assert sub["code"] == ErrorCode.BAD_ROLE.value
    assert unsub["op"] == "error"
    assert unsub["code"] == ErrorCode.BAD_ROLE.value


@pytest.mark.asyncio
async def test_disconnect_removes_memberships_and_empty_channels(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as control,
            websockets.connect(context.url) as agent,
        ):
            await connect_control(control, context)
            await connect_agent(agent, context, "a", "agent-a")
            await subscribe(agent, "build")
            await agent.close()
            await asyncio.sleep(0.05)
            response = await request_channels(control)

    assert response["op"] == "channels_ok"
    assert response["channels"] == []


@pytest.mark.asyncio
async def test_bye_removes_memberships_and_empty_channels(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as control,
            websockets.connect(context.url) as agent,
        ):
            await connect_control(control, context)
            await connect_agent(agent, context, "a", "agent-a")
            await subscribe(agent, "build")
            await agent.send(json.dumps({"op": "bye"}))
            await asyncio.sleep(0.05)
            response = await request_channels(control)

    assert response["op"] == "channels_ok"
    assert response["channels"] == []


@pytest.mark.asyncio
async def test_kick_removes_memberships_and_empty_channels(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as control,
            websockets.connect(context.url) as agent,
        ):
            await connect_control(control, context)
            await connect_agent(agent, context, "a", "agent-a")
            await subscribe(agent, "build")
            await control.send(json.dumps({"op": "kick", "name": "agent-a"}))
            response = await recv_json(control)
            assert response["op"] == "kick_ok"
            await asyncio.sleep(0.05)
            channels_response = await request_channels(control)

    assert channels_response["op"] == "channels_ok"
    assert channels_response["channels"] == []


@pytest.mark.asyncio
async def test_unsubscribe_removes_empty_channel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as agent,
            websockets.connect(context.url) as control,
        ):
            await connect_agent(agent, context, "a", "agent-a")
            await connect_control(control, context)
            await subscribe(agent, "build")
            await unsubscribe(agent, "build")
            response = await request_channels(control)

    assert response["op"] == "channels_ok"
    assert response["channels"] == []
