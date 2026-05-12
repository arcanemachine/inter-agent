from __future__ import annotations

from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, connect_agent, running_server, send_json

from inter_agent.core.errors import ErrorCode
from inter_agent.core.shared import Limits


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
    ("message", "expected_code", "limits"),
    [
        ({"op": "send", "to": "agent-b", "text": 123}, ErrorCode.BAD_TEXT, None),
        ({"op": "send", "to": "agent-b", "text": "hi"}, ErrorCode.UNKNOWN_TARGET, None),
        (
            {"op": "broadcast", "text": "too large"},
            ErrorCode.TEXT_TOO_LARGE,
            Limits(broadcast_text_max=1),
        ),
    ],
)
async def test_routing_errors_use_canonical_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    message: dict[str, object],
    expected_code: ErrorCode,
    limits: Limits | None,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port, limits) as context:
        async with websockets.connect(context.url) as ws:
            await connect_agent(ws, context, "a", "agent-a")
            err = await send_json(ws, message)

    assert err["op"] == "error"
    assert err["code"] == expected_code.value


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
