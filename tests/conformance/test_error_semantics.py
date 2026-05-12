from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import websockets
from websockets.asyncio.client import ClientConnection

from inter_agent.core.errors import ErrorCode
from inter_agent.core.server import run_server
from inter_agent.core.shared import Limits, load_or_create_token


@asynccontextmanager
async def _running_server(
    host: str, port: int, limits: Limits | None = None
) -> AsyncIterator[None]:
    task = asyncio.create_task(run_server(host, port, limits=limits))
    await asyncio.sleep(0.1)
    try:
        yield
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


def _hello(
    token: str,
    *,
    role: object = "agent",
    session_id: object = "a",
    name: object = "agent-a",
) -> dict[str, object]:
    return {
        "op": "hello",
        "token": token,
        "role": role,
        "session_id": session_id,
        "name": name,
        "capabilities": {},
    }


async def _send_json(ws: ClientConnection, payload: object) -> dict[str, object]:
    await ws.send(json.dumps(payload))
    response = json.loads(await ws.recv())
    assert isinstance(response, dict)
    return response


async def _connect_agent(ws: ClientConnection, token: str, session_id: str, name: str) -> None:
    response = await _send_json(ws, _hello(token, session_id=session_id, name=name))
    assert response["op"] == "welcome"


@pytest.mark.asyncio
async def test_auth_failure_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    host, port = "127.0.0.1", unused_tcp_port
    load_or_create_token()

    async with _running_server(host, port):
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            err = await _send_json(ws, _hello("wrong"))

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hello_payload", "expected_code"),
    [
        ({"op": "ping"}, ErrorCode.PROTOCOL_ERROR),
        (_hello("token", role="observer"), ErrorCode.BAD_ROLE),
        (_hello("token", session_id=""), ErrorCode.BAD_SESSION),
        (_hello("token", name="Not Valid"), ErrorCode.BAD_NAME),
        ({**_hello("token"), "label": 42}, ErrorCode.BAD_LABEL),
    ],
)
async def test_handshake_validation_errors_use_canonical_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
    unused_tcp_port: int,
    hello_payload: dict[str, object],
    expected_code: ErrorCode,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", unused_tcp_port

    payload = dict(hello_payload)
    if payload.get("token") == "token":
        payload["token"] = token

    async with _running_server(host, port):
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            err = await _send_json(ws, payload)

    assert err["op"] == "error"
    assert err["code"] == expected_code.value


@pytest.mark.asyncio
async def test_duplicate_name_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", unused_tcp_port

    async with _running_server(host, port):
        async with (
            websockets.connect(f"ws://{host}:{port}") as first,
            websockets.connect(f"ws://{host}:{port}") as duplicate,
        ):
            await _connect_agent(first, token, "a", "agent-a")
            err = await _send_json(duplicate, _hello(token, session_id="b", name="agent-a"))

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.NAME_TAKEN.value


@pytest.mark.asyncio
async def test_unknown_operation_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", unused_tcp_port

    async with _running_server(host, port):
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            await _connect_agent(ws, token, "a", "agent-a")
            err = await _send_json(ws, {"op": "not_supported"})

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
    tmp_path: object,
    unused_tcp_port: int,
    message: dict[str, object],
    expected_code: ErrorCode,
    limits: Limits | None,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", unused_tcp_port

    async with _running_server(host, port, limits):
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            await _connect_agent(ws, token, "a", "agent-a")
            err = await _send_json(ws, message)

    assert err["op"] == "error"
    assert err["code"] == expected_code.value


@pytest.mark.asyncio
async def test_targeted_custom_unknown_target_uses_canonical_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", unused_tcp_port

    async with _running_server(host, port):
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            await _connect_agent(ws, token, "a", "agent-a")
            err = await _send_json(
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
