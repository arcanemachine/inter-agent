from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from websockets.asyncio.client import ClientConnection

from inter_agent.core.server import run_server
from inter_agent.core.shared import Limits, load_or_create_token

HOST = "127.0.0.1"
MISSING = object()


@dataclass(frozen=True)
class ServerContext:
    host: str
    port: int
    token: str

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"


@asynccontextmanager
async def running_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    limits: Limits | None = None,
) -> AsyncIterator[ServerContext]:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    context = ServerContext(host=HOST, port=unused_tcp_port, token=token)
    task = asyncio.create_task(run_server(context.host, context.port, limits=limits))
    await asyncio.sleep(0.1)
    try:
        yield context
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


def agent_hello(
    token: str,
    *,
    role: object = "agent",
    session_id: object = "a",
    name: object = "agent-a",
    label: object = MISSING,
    capabilities: object = MISSING,
) -> dict[str, object]:
    payload = {
        "op": "hello",
        "token": token,
        "role": role,
        "session_id": session_id,
        "name": name,
        "capabilities": {} if capabilities is MISSING else capabilities,
    }
    if label is not MISSING:
        payload["label"] = label
    return payload


def control_hello(
    token: str,
    *,
    session_id: object = "ctl",
    name: object = "control",
    capabilities: object = MISSING,
) -> dict[str, object]:
    return {
        "op": "hello",
        "token": token,
        "role": "control",
        "session_id": session_id,
        "name": name,
        "capabilities": {} if capabilities is MISSING else capabilities,
    }


async def recv_json(ws: ClientConnection) -> dict[str, object]:
    response = json.loads(await ws.recv())
    assert isinstance(response, dict)
    return {str(key): value for key, value in response.items()}


async def send_json(ws: ClientConnection, payload: object) -> dict[str, object]:
    await ws.send(json.dumps(payload))
    return await recv_json(ws)


async def connect_agent(
    ws: ClientConnection,
    context: ServerContext,
    session_id: str,
    name: str,
    label: object = MISSING,
) -> dict[str, object]:
    response = await send_json(
        ws,
        agent_hello(context.token, session_id=session_id, name=name, label=label),
    )
    assert response["op"] == "welcome"
    return response


async def connect_control(
    ws: ClientConnection,
    context: ServerContext,
    session_id: str = "ctl",
) -> dict[str, object]:
    response = await send_json(ws, control_hello(context.token, session_id=session_id))
    assert response["op"] == "welcome"
    return response


async def assert_no_message(ws: ClientConnection, timeout: float = 0.1) -> None:
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ws.recv(), timeout=timeout)
