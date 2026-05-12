from __future__ import annotations

import json
from pathlib import Path

import pytest
import websockets
from helpers import assert_no_message, connect_agent, recv_json, running_server, send_json

from inter_agent.core.errors import ErrorCode


@pytest.mark.asyncio
async def test_direct_send_exact_name_wins_over_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as exact,
            websockets.connect(context.url) as longer,
        ):
            await connect_agent(sender, context, "s", "sender")
            await connect_agent(exact, context, "a", "agent")
            await connect_agent(longer, context, "b", "agent-b")

            await sender.send(json.dumps({"op": "send", "to": "agent", "text": "hi"}))
            delivered = await recv_json(exact)
            await assert_no_message(longer)

    assert delivered["op"] == "msg"
    assert delivered["to"] == "agent"
    assert delivered["text"] == "hi"


@pytest.mark.asyncio
async def test_direct_send_unique_prefix_routes_to_matching_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as target,
            websockets.connect(context.url) as other,
        ):
            await connect_agent(sender, context, "s", "sender")
            await connect_agent(target, context, "a", "agent-alpha")
            await connect_agent(other, context, "b", "worker-beta")

            await sender.send(json.dumps({"op": "send", "to": "agent-a", "text": "hi"}))
            delivered = await recv_json(target)
            await assert_no_message(other)

    assert delivered["op"] == "msg"
    assert delivered["to"] == "agent-alpha"
    assert delivered["text"] == "hi"


@pytest.mark.asyncio
async def test_direct_send_ambiguous_prefix_returns_error_without_delivery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as first,
            websockets.connect(context.url) as second,
        ):
            await connect_agent(sender, context, "s", "sender")
            await connect_agent(first, context, "a", "agent-alpha")
            await connect_agent(second, context, "b", "agent-amber")

            err = await send_json(sender, {"op": "send", "to": "agent-a", "text": "hi"})
            await assert_no_message(first)
            await assert_no_message(second)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AMBIGUOUS_TARGET.value


@pytest.mark.asyncio
async def test_direct_send_label_is_not_a_routing_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as target,
        ):
            await connect_agent(sender, context, "s", "sender")
            await connect_agent(target, context, "a", "agent-alpha", "Agent Alpha")

            err = await send_json(sender, {"op": "send", "to": "Agent Alpha", "text": "hi"})
            await assert_no_message(target)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.UNKNOWN_TARGET.value


@pytest.mark.asyncio
async def test_targeted_custom_unique_prefix_routes_to_matching_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as target,
            websockets.connect(context.url) as other,
        ):
            await connect_agent(sender, context, "s", "sender")
            await connect_agent(target, context, "a", "agent-alpha")
            await connect_agent(other, context, "b", "worker-beta")

            await sender.send(
                json.dumps(
                    {
                        "op": "custom",
                        "custom_type": "x.test.v1",
                        "to": "agent-a",
                        "payload": {"ok": True},
                    }
                )
            )
            delivered = await recv_json(target)
            await assert_no_message(other)

    assert delivered["op"] == "msg"
    assert delivered["to"] == "agent-alpha"
    assert delivered["custom_type"] == "x.test.v1"
    assert delivered["payload"] == {"ok": True}


@pytest.mark.asyncio
async def test_targeted_custom_ambiguous_prefix_returns_error_without_delivery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as first,
            websockets.connect(context.url) as second,
        ):
            await connect_agent(sender, context, "s", "sender")
            await connect_agent(first, context, "a", "agent-alpha")
            await connect_agent(second, context, "b", "agent-amber")

            err = await send_json(
                sender,
                {
                    "op": "custom",
                    "custom_type": "x.test.v1",
                    "to": "agent-a",
                    "payload": {},
                },
            )
            await assert_no_message(first)
            await assert_no_message(second)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AMBIGUOUS_TARGET.value
