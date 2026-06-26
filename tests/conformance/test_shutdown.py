from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, connect_agent, connect_control, recv_json

from inter_agent.core.auth import build_auth_response, parse_auth_challenge
from inter_agent.core.errors import ErrorCode
from inter_agent.core.server import run_server
from inter_agent.core.shared import resolve_shared_secret

HOST = "127.0.0.1"


@dataclass(frozen=True)
class AuthContext:
    secret: str


def hello_client_nonce(hello: dict[str, object]) -> str:
    auth = hello["auth"]
    assert isinstance(auth, dict)
    nonce = auth["client_nonce"]
    assert isinstance(nonce, str)
    return nonce


async def wait_for_server() -> None:
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_shutdown_control_stops_server(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    secret = resolve_shared_secret().secret
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_server()

    async with (
        websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as agent,
        websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as control,
    ):
        context = AuthContext(secret)
        await connect_agent(agent, context, "a", "agent-a")
        await connect_control(control, context, "ctl")
        await control.send('{"op":"shutdown"}')
        response = await recv_json(control)

        with pytest.raises(websockets.ConnectionClosed):
            await agent.recv()

    await asyncio.wait_for(task, timeout=1)
    assert response == {"op": "shutdown_ok"}


@pytest.mark.asyncio
async def test_shutdown_requires_valid_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    secret = resolve_shared_secret().secret
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_server()

    try:
        async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as ws:
            hello = agent_hello(session_id="a", name="agent-a")
            await ws.send(json.dumps(hello))
            challenge = parse_auth_challenge(await recv_json(ws))
            await ws.send(
                json.dumps(
                    build_auth_response(
                        "wrong-secret",
                        client_nonce=hello_client_nonce(hello),
                        server_nonce=challenge.server_nonce,
                        hello=hello,
                    )
                )
            )
            err = await recv_json(ws)

        async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as control:
            await connect_control(control, AuthContext(secret), "ctl")
            await control.send('{"op":"ping"}')
            pong = await recv_json(control)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value
    assert pong == {"op": "pong"}


@pytest.mark.asyncio
async def test_shutdown_requires_control_role(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    secret = resolve_shared_secret().secret
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_server()

    try:
        async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as agent:
            await connect_agent(agent, AuthContext(secret), "a", "agent-a")
            await agent.send('{"op":"shutdown"}')
            err = await recv_json(agent)
            await agent.send('{"op":"ping"}')
            pong = await recv_json(agent)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.BAD_ROLE.value
    assert pong == {"op": "pong"}


@pytest.mark.asyncio
async def test_idle_timeout_shuts_down_when_no_connections_arrive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    task = asyncio.create_task(run_server(HOST, unused_tcp_port, idle_timeout_s=0.1))
    await asyncio.wait_for(task, timeout=1.0)


@pytest.mark.asyncio
async def test_default_idle_timeout_is_disabled_after_last_disconnect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    secret = resolve_shared_secret().secret
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_server()

    try:
        async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as ws:
            await connect_agent(ws, AuthContext(secret), "a", "agent-a")

        await asyncio.sleep(0.15)
        assert not task.done()
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_idle_timeout_shuts_down_after_last_disconnect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    secret = resolve_shared_secret().secret
    task = asyncio.create_task(run_server(HOST, unused_tcp_port, idle_timeout_s=0.3))
    await wait_for_server()

    async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as ws:
        await connect_agent(ws, AuthContext(secret), "a", "agent-a")

    await asyncio.wait_for(task, timeout=1.0)


@pytest.mark.asyncio
async def test_idle_timeout_cancelled_by_new_connection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    secret = resolve_shared_secret().secret
    context = AuthContext(secret)
    task = asyncio.create_task(run_server(HOST, unused_tcp_port, idle_timeout_s=0.3))
    await wait_for_server()

    async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as ws:
        await connect_agent(ws, context, "a", "agent-a")

    await asyncio.sleep(0.15)

    async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as ws2:
        await connect_agent(ws2, context, "b", "agent-b")

    await asyncio.sleep(0.25)

    assert not task.done()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
