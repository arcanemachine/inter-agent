from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import websockets
from helpers import assert_no_message, connect_agent, recv_json, running_server
from websockets.exceptions import ConnectionClosed

from inter_agent.core.errors import ErrorCode
from inter_agent.core.shared import Limits

EXACT_TEXT = "éé"
OVER_TEXT = "ééx"
TEXT_LIMIT = len(EXACT_TEXT.encode("utf-8"))
FRAME_LIMIT = 256


def _limits_for(operation: str, max_bytes: int, frame_max: int = 4096) -> Limits:
    if operation == "send":
        return Limits(frame_max=frame_max, direct_text_max=max_bytes)
    if operation == "broadcast":
        return Limits(frame_max=frame_max, broadcast_text_max=max_bytes)
    raise AssertionError(f"unsupported operation: {operation}")


def _payload_for(operation: str, text: str) -> dict[str, object]:
    if operation == "send":
        return {"op": "send", "to": "agent-b", "text": text}
    if operation == "broadcast":
        return {"op": "broadcast", "text": text}
    raise AssertionError(f"unsupported operation: {operation}")


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["send", "broadcast"])
async def test_text_at_exact_utf8_byte_limit_is_delivered(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    operation: str,
) -> None:
    assert len(EXACT_TEXT) < TEXT_LIMIT
    limits = _limits_for(operation, TEXT_LIMIT)

    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits) as context:
        async with (
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as b,
        ):
            await connect_agent(a, context, "a", "agent-a")
            await connect_agent(b, context, "b", "agent-b")

            await a.send(json.dumps(_payload_for(operation, EXACT_TEXT)))
            msg = await recv_json(b)
            await assert_no_message(a)

    assert msg["op"] == "msg"
    assert msg["from"] == "a"
    assert msg["from_name"] == "agent-a"
    assert msg["text"] == EXACT_TEXT
    if operation == "send":
        assert msg["to"] == "agent-b"
    else:
        assert "to" not in msg


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["send", "broadcast"])
async def test_text_one_utf8_byte_over_limit_returns_text_too_large(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    operation: str,
) -> None:
    assert len(OVER_TEXT.encode("utf-8")) == TEXT_LIMIT + 1
    assert len(OVER_TEXT) <= TEXT_LIMIT
    limits = _limits_for(operation, TEXT_LIMIT)

    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits) as context:
        async with (
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as b,
        ):
            await connect_agent(a, context, "a", "agent-a")
            await connect_agent(b, context, "b", "agent-b")

            await a.send(json.dumps(_payload_for(operation, OVER_TEXT)))
            err = await recv_json(a)
            await assert_no_message(b)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.TEXT_TOO_LARGE.value


@pytest.mark.asyncio
async def test_oversized_websocket_frame_closes_connection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    limits = Limits(frame_max=FRAME_LIMIT)
    oversized_frame = {"op": "ping", "padding": "x" * FRAME_LIMIT}
    assert len(json.dumps(oversized_frame).encode("utf-8")) > FRAME_LIMIT

    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            await ws.send(json.dumps(oversized_frame))

            with pytest.raises(ConnectionClosed):
                await asyncio.wait_for(ws.recv(), timeout=1)
