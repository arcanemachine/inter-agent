from __future__ import annotations

from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, assert_no_message, connect_agent, running_server, send_json

from inter_agent.core.errors import ErrorCode


@pytest.mark.asyncio
async def test_auth_failure_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            err = await send_json(ws, agent_hello("wrong"))

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hello_payload", "expected_code"),
    [
        ({"op": "ping"}, ErrorCode.PROTOCOL_ERROR),
        (agent_hello("token", role="observer"), ErrorCode.BAD_ROLE),
        (agent_hello("token", session_id=""), ErrorCode.BAD_SESSION),
        (agent_hello("token", name="Not Valid"), ErrorCode.BAD_NAME),
        ({**agent_hello("token"), "label": 42}, ErrorCode.BAD_LABEL),
        (
            {k: v for k, v in agent_hello("token").items() if k != "capabilities"},
            ErrorCode.PROTOCOL_ERROR,
        ),
        (agent_hello("token", capabilities=[]), ErrorCode.PROTOCOL_ERROR),
    ],
)
async def test_handshake_validation_errors_use_canonical_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    hello_payload: dict[str, object],
    expected_code: ErrorCode,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        payload = dict(hello_payload)
        if payload.get("_test_secret") == "token":
            payload["_test_secret"] = context.token
        if payload.get("token") == "token":
            payload["token"] = context.token
        async with websockets.connect(context.url) as ws:
            err = await send_json(ws, payload)

    assert err["op"] == "error"
    assert err["code"] == expected_code.value


@pytest.mark.asyncio
async def test_duplicate_name_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as first,
            websockets.connect(context.url) as duplicate,
        ):
            await connect_agent(first, context, "a", "agent-a")
            err = await send_json(
                duplicate, agent_hello(context.token, session_id="b", name="agent-a")
            )

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.NAME_TAKEN.value


@pytest.mark.asyncio
async def test_unknown_operation_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            err = await send_json(ws, {"op": "not_supported"})

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.UNKNOWN_OP.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected_code"),
    [
        ({"op": "send", "to": "agent-b", "text": 123}, ErrorCode.BAD_TEXT),
        ({"op": "send", "to": "agent-b", "text": "hi"}, ErrorCode.UNKNOWN_TARGET),
    ],
)
async def test_routing_errors_use_canonical_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    message: dict[str, object],
    expected_code: ErrorCode,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            err = await send_json(ws, message)

    assert err["op"] == "error"
    assert err["code"] == expected_code.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        {"op": "send", "to": "agent-b", "text": "hi", "from_name": 123},
        {"op": "broadcast", "text": "hi", "from_name": 123},
        {"op": "publish", "channel": "build", "text": "hi", "from_name": 123},
    ],
)
async def test_non_string_from_name_is_rejected_without_delivery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    message: dict[str, object],
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as sender,
            websockets.connect(context.url) as recipient,
        ):
            await connect_agent(sender, context, "a", "agent-a")
            await connect_agent(recipient, context, "b", "agent-b")
            if message["op"] == "publish":
                await send_json(recipient, {"op": "subscribe", "channel": "build"})

            err = await send_json(sender, message)
            await assert_no_message(recipient)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.BAD_FROM_NAME.value


@pytest.mark.asyncio
async def test_targeted_custom_unknown_target_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            err = await send_json(
                ws,
                {
                    "op": "custom",
                    "custom_type": "x.unknown.v1",
                    "to": "missing",
                    "payload": {},
                },
            )

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.UNKNOWN_TARGET.value
