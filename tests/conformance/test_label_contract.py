from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import websockets
from websockets.asyncio.client import ClientConnection

from inter_agent.core.server import run_server
from inter_agent.core.shared import load_or_create_token

_MISSING = object()


@asynccontextmanager
async def _running_server(host: str, port: int) -> AsyncIterator[None]:
    task = asyncio.create_task(run_server(host, port))
    await asyncio.sleep(0.1)
    try:
        yield
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def _send_agent_hello(
    ws: ClientConnection,
    token: str,
    session_id: str,
    name: str,
    label: object = _MISSING,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "op": "hello",
        "token": token,
        "role": "agent",
        "session_id": session_id,
        "name": name,
        "capabilities": {},
    }
    if label is not _MISSING:
        payload["label"] = label
    await ws.send(json.dumps(payload))
    response = json.loads(await ws.recv())
    assert isinstance(response, dict)
    return response


async def _send_control_hello(ws: ClientConnection, token: str) -> None:
    await ws.send(
        json.dumps(
            {
                "op": "hello",
                "token": token,
                "role": "control",
                "session_id": "ctl",
                "name": "control",
                "capabilities": {},
            }
        )
    )
    response = json.loads(await ws.recv())
    assert response["op"] == "welcome"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("label", "expected_label"),
    [
        (_MISSING, None),
        ("Agent A", "Agent A"),
        (None, None),
    ],
)
async def test_label_values_are_listed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
    label: object,
    expected_label: str | None,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", unused_tcp_port

    async with _running_server(host, port):
        async with (
            websockets.connect(f"ws://{host}:{port}") as agent,
            websockets.connect(f"ws://{host}:{port}") as control,
        ):
            welcome = await _send_agent_hello(agent, token, "a", "agent-a", label)
            assert welcome["op"] == "welcome"
            await _send_control_hello(control, token)
            await control.send(json.dumps({"op": "list"}))
            list_ok = json.loads(await control.recv())

            assert list_ok["op"] == "list_ok"
            sessions = list_ok["sessions"]
            assert sessions == [
                {
                    "session_id": "a",
                    "name": "agent-a",
                    "label": expected_label,
                }
            ]


@pytest.mark.asyncio
async def test_invalid_label_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", unused_tcp_port

    async with _running_server(host, port):
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            err = await _send_agent_hello(ws, token, "a", "agent-a", 42)

            assert err["op"] == "error"
            assert err["code"] == "BAD_LABEL"
