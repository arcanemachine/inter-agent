from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import websockets
from helpers import (
    agent_hello,
    assert_no_message,
    connect_agent,
    recv_json,
    running_server,
    send_json,
)

from inter_agent.core.errors import ErrorCode
from inter_agent.core.shared import Limits


@pytest.mark.asyncio
async def test_connection_limit_rejects_excess_active_connection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(connection_max=1)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with (
            websockets.connect(context.url) as first,
            websockets.connect(context.url) as second,
        ):
            await connect_agent(first, context, "a", "agent-a")
            err = await send_json(
                second,
                agent_hello(context.token, session_id="b", name="agent-b"),
            )

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.TOO_MANY_CONNECTIONS.value


@pytest.mark.asyncio
async def test_connection_limit_allows_new_connection_after_disconnect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(connection_max=1)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with websockets.connect(context.url) as first:
            await connect_agent(first, context, "a", "agent-a")
        await asyncio.sleep(0.05)
        async with websockets.connect(context.url) as second:
            welcome = await send_json(
                second,
                agent_hello(context.token, session_id="b", name="agent-b"),
            )

    assert welcome["op"] == "welcome"
    assert welcome["assigned_name"] == "agent-b"


@pytest.mark.asyncio
@pytest.mark.parametrize("custom_type", [None, "", 123])
async def test_custom_type_must_be_non_empty_string(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    custom_type: object,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as sender:
            await connect_agent(sender, context, "a", "agent-a")
            payload: dict[str, object] = {"op": "custom", "payload": {}}
            if custom_type is not None:
                payload["custom_type"] = custom_type
            err = await send_json(sender, payload)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.BAD_CUSTOM_TYPE.value


@pytest.mark.asyncio
async def test_custom_type_is_size_limited(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(custom_type_max=4)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with websockets.connect(context.url) as sender:
            await connect_agent(sender, context, "a", "agent-a")
            err = await send_json(
                sender,
                {"op": "custom", "custom_type": "abcde", "payload": {}},
            )

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.BAD_CUSTOM_TYPE.value


@pytest.mark.asyncio
async def test_custom_payload_is_size_limited_without_delivery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(custom_payload_max=10)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as target,
        ):
            await connect_agent(sender, context, "a", "agent-a")
            await connect_agent(target, context, "b", "agent-b")
            err = await send_json(
                sender,
                {
                    "op": "custom",
                    "custom_type": "x.test.v1",
                    "to": "agent-b",
                    "payload": {"data": "too large"},
                },
            )
            await assert_no_message(target)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.CUSTOM_PAYLOAD_TOO_LARGE.value


@pytest.mark.asyncio
async def test_custom_payload_at_limit_is_delivered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    payload = {"a": "b"}
    payload_size = len(json.dumps(payload, ensure_ascii=False).encode())
    limits = Limits(custom_payload_max=payload_size)
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits=limits) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as target,
        ):
            await connect_agent(sender, context, "a", "agent-a")
            await connect_agent(target, context, "b", "agent-b")
            await sender.send(
                json.dumps(
                    {
                        "op": "custom",
                        "custom_type": "x.test.v1",
                        "to": "agent-b",
                        "payload": payload,
                    }
                )
            )
            delivered = await recv_json(target)

    assert delivered["op"] == "msg"
    assert delivered["payload"] == payload
