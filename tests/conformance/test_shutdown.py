from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, control_hello, send_json

from inter_agent.core.errors import ErrorCode
from inter_agent.core.server import run_server
from inter_agent.core.shared import identity_path, load_or_create_token, pid_path

HOST = "127.0.0.1"


async def wait_for_identity(port: int) -> None:
    path = identity_path(port)
    deadline = asyncio.get_running_loop().time() + 1
    while asyncio.get_running_loop().time() < deadline:
        if path.exists():
            return
        await asyncio.sleep(0.01)
    raise TimeoutError(f"timed out waiting for {path}")


@pytest.mark.asyncio
async def test_shutdown_control_stops_server_and_cleans_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_identity(unused_tcp_port)

    async with (
        websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as agent,
        websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as control,
    ):
        welcome = await send_json(agent, agent_hello(token, session_id="a", name="agent-a"))
        assert welcome["op"] == "welcome"
        await send_json(control, control_hello(token, session_id="ctl"))
        response = await send_json(control, {"op": "shutdown"})

        with pytest.raises(websockets.ConnectionClosed):
            await agent.recv()

    await asyncio.wait_for(task, timeout=1)
    assert response == {"op": "shutdown_ok"}
    assert not identity_path(unused_tcp_port).exists()
    assert not pid_path(unused_tcp_port).exists()


@pytest.mark.asyncio
async def test_shutdown_requires_valid_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_identity(unused_tcp_port)

    try:
        async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as ws:
            err = await send_json(ws, agent_hello("wrong-token"))

        async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as control:
            await send_json(control, control_hello(token, session_id="ctl"))
            pong = await send_json(control, {"op": "ping"})
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
    token = load_or_create_token()
    task = asyncio.create_task(run_server(HOST, unused_tcp_port))
    await wait_for_identity(unused_tcp_port)

    try:
        async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}") as agent:
            await send_json(agent, agent_hello(token, session_id="a", name="agent-a"))
            err = await send_json(agent, {"op": "shutdown"})
            pong = await send_json(agent, {"op": "ping"})
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.BAD_ROLE.value
    assert pong == {"op": "pong"}
