from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import pytest
from jsonschema import Draft202012Validator
from websockets.asyncio.client import ClientConnection

from inter_agent.core.auth import build_auth_response, client_handshake, parse_auth_challenge
from inter_agent.core.client import build_hello as build_agent_hello
from inter_agent.core.server import run_server
from inter_agent.core.shared import Limits, resolve_shared_secret
from inter_agent.core.shared import control_hello as build_control_hello

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "spec" / "schemas"
HOST = "127.0.0.1"
MISSING = object()


@lru_cache
def _server_frame_validator(op: str) -> Draft202012Validator:
    schema_path = SCHEMA_DIR / f"{op}.json"
    assert schema_path.exists(), f"server emitted unknown protocol operation: {op!r}"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    return Draft202012Validator(schema)


def assert_server_frame_matches_schema(response: dict[str, object]) -> None:
    op = response.get("op")
    assert isinstance(op, str), "server frame must include a string operation"
    _server_frame_validator(op).validate(response)


class HasSecret(Protocol):
    @property
    def secret(self) -> str: ...


@dataclass(frozen=True)
class ServerContext:
    host: str
    port: int
    secret: str

    @property
    def token(self) -> str:
        return self.secret

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
    secret = resolve_shared_secret().secret
    context = ServerContext(host=HOST, port=unused_tcp_port, secret=secret)
    task = asyncio.create_task(run_server(context.host, context.port, limits=limits))
    await asyncio.sleep(0.1)
    try:
        yield context
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


def agent_hello(
    _secret: str | None = None,
    *,
    role: object = "agent",
    session_id: object = "a",
    name: object = "agent-a",
    label: object = MISSING,
    capabilities: object = MISSING,
    client_nonce: str | None = None,
) -> dict[str, object]:
    payload = build_agent_hello(
        str(session_id),
        str(name),
        label if isinstance(label, str) else None,
        client_nonce=client_nonce,
    )
    if _secret is not None:
        payload["_test_secret"] = _secret
    payload["role"] = role
    payload["session_id"] = session_id
    payload["name"] = name
    payload["capabilities"] = {} if capabilities is MISSING else capabilities
    if label is MISSING:
        payload.pop("label", None)
    else:
        payload["label"] = label
    return payload


def control_hello_payload(
    _secret: str | None = None,
    *,
    session_id: object = "ctl",
    name: object = "control",
    capabilities: object = MISSING,
) -> dict[str, object]:
    payload = build_control_hello(str(session_id))
    if _secret is not None:
        payload["_test_secret"] = _secret
    payload["session_id"] = session_id
    payload["name"] = name
    payload["capabilities"] = {} if capabilities is MISSING else capabilities
    return payload


async def recv_json(ws: ClientConnection) -> dict[str, object]:
    response = json.loads(await ws.recv())
    assert isinstance(response, dict)
    normalized = {str(key): value for key, value in response.items()}
    assert_server_frame_matches_schema(normalized)
    return normalized


def _client_nonce(hello: dict[str, object]) -> str:
    auth = hello.get("auth")
    assert isinstance(auth, dict)
    nonce = auth.get("client_nonce")
    assert isinstance(nonce, str)
    return nonce


async def send_json(ws: ClientConnection, payload: object) -> dict[str, object]:
    secret: str | None = None
    outbound = payload
    if isinstance(payload, dict):
        outbound = dict(payload)
        raw_secret = outbound.pop("_test_secret", None)
        if isinstance(raw_secret, str):
            secret = raw_secret
    await ws.send(json.dumps(outbound))
    response = await recv_json(ws)
    if (
        secret is not None
        and isinstance(outbound, dict)
        and outbound.get("op") == "hello"
        and response.get("op") == "auth_challenge"
    ):
        challenge = parse_auth_challenge(response)
        await ws.send(
            json.dumps(
                build_auth_response(
                    secret,
                    client_nonce=_client_nonce(outbound),
                    server_nonce=challenge.server_nonce,
                    hello=outbound,
                )
            )
        )
        return await recv_json(ws)
    return response


async def connect_agent(
    ws: ClientConnection,
    context: HasSecret,
    session_id: str,
    name: str,
    label: object = MISSING,
) -> dict[str, object]:
    hello = agent_hello(session_id=session_id, name=name, label=label)
    response = json.loads(await client_handshake(ws, context.secret, hello))
    assert isinstance(response, dict)
    response = {str(key): value for key, value in response.items()}
    assert response["op"] == "welcome"
    return response


control_hello = control_hello_payload


async def connect_control(
    ws: ClientConnection,
    context: HasSecret,
    session_id: str = "ctl",
) -> dict[str, object]:
    response = json.loads(
        await client_handshake(ws, context.secret, control_hello_payload(session_id=session_id))
    )
    assert isinstance(response, dict)
    response = {str(key): value for key, value in response.items()}
    assert response["op"] == "welcome"
    return response


async def subscribe(ws: ClientConnection, channel: str) -> dict[str, object]:
    return await send_json(ws, {"op": "subscribe", "channel": channel})


async def unsubscribe(ws: ClientConnection, channel: str) -> dict[str, object]:
    return await send_json(ws, {"op": "unsubscribe", "channel": channel})


async def publish(
    ws: ClientConnection,
    channel: str,
    text: str,
    from_name: str | None = None,
    timeout: float = 0.1,
) -> dict[str, object] | None:
    payload: dict[str, object] = {"op": "publish", "channel": channel, "text": text}
    if from_name is not None:
        payload["from_name"] = from_name
    await ws.send(json.dumps(payload))
    try:
        return await asyncio.wait_for(recv_json(ws), timeout=timeout)
    except TimeoutError:
        return None


async def request_channels(ws: ClientConnection) -> dict[str, object]:
    return await send_json(ws, {"op": "channels"})


async def assert_no_message(ws: ClientConnection, timeout: float = 0.1) -> None:
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ws.recv(), timeout=timeout)
