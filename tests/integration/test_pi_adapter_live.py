from __future__ import annotations

import asyncio
import io
import json
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path

import pytest
import websockets
from conftest import LiveServer
from websockets.asyncio.client import ClientConnection

from inter_agent.adapters.pi import commands as pi_commands
from inter_agent.adapters.pi.cli import main as pi_main
from inter_agent.core.client import build_hello
from inter_agent.core.shared import control_hello, write_server_identity


@dataclass(frozen=True)
class CommandCapture:
    code: int
    stdout: str
    stderr: str


def run_pi(args: list[str]) -> CommandCapture:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = pi_main(args)
    return CommandCapture(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def run_pi_function(function: Callable[..., int], *args: object) -> CommandCapture:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = function(*args)
    assert isinstance(code, int)
    return CommandCapture(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def use_live_pi_defaults(monkeypatch: pytest.MonkeyPatch, server: LiveServer) -> None:
    monkeypatch.setattr(pi_commands, "DEFAULT_HOST", server.host)
    monkeypatch.setattr(pi_commands, "DEFAULT_PORT", server.port)


async def recv_json(ws: ClientConnection) -> dict[str, object]:
    response: object = json.loads(await ws.recv())
    assert isinstance(response, dict)
    return {str(key): value for key, value in response.items()}


async def send_json(ws: ClientConnection, payload: object) -> dict[str, object]:
    await ws.send(json.dumps(payload))
    return await recv_json(ws)


async def connect_agent(
    ws: ClientConnection,
    server: LiveServer,
    session_id: str,
    name: str,
    label: str | None = None,
) -> None:
    response = await send_json(ws, build_hello(server.token, session_id, name, label))
    assert response["op"] == "welcome"


async def connect_control(ws: ClientConnection, server: LiveServer, session_id: str) -> None:
    response = await send_json(ws, control_hello(server.token, session_id))
    assert response["op"] == "welcome"


async def assert_no_message(ws: ClientConnection) -> None:
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ws.recv(), timeout=0.1)


@pytest.mark.asyncio
async def test_pi_status_reports_available_without_connected_agent(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_pi_defaults(monkeypatch, live_server)

    result = await asyncio.to_thread(run_pi, ["status", "--json"])

    payload = json.loads(result.stdout)
    assert result.code == 0
    assert result.stderr == ""
    assert payload["state"] == "available"
    assert payload["host"] == live_server.host
    assert payload["port"] == live_server.port
    assert payload["server_reachable"] is True
    assert payload["identity_verified"] is True
    assert payload["core_list_supported"] is True
    assert payload["adapter_list_exposed"] is True


@pytest.mark.asyncio
async def test_pi_cli_list_reports_live_agent_sessions(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_pi_defaults(monkeypatch, live_server)
    async with websockets.connect(live_server.url) as agent:
        await connect_agent(agent, live_server, "a", "agent-a", "Agent A")

        result = await asyncio.to_thread(run_pi, ["list"])

    assert result.code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "op": "list_ok",
        "sessions": [{"session_id": "a", "name": "agent-a", "label": "Agent A"}],
    }


@pytest.mark.asyncio
async def test_pi_python_send_delivers_to_live_agent(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_pi_defaults(monkeypatch, live_server)
    async with websockets.connect(live_server.url) as target:
        await connect_agent(target, live_server, "b", "agent-b")

        result = await asyncio.to_thread(run_pi_function, pi_commands.send, "agent-b", "hello")
        delivered = await recv_json(target)

    assert result.code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["op"] == "welcome"
    assert delivered["op"] == "msg"
    assert delivered["to"] == "agent-b"
    assert delivered["text"] == "hello"


@pytest.mark.asyncio
async def test_pi_python_broadcast_delivers_to_agents_only(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_pi_defaults(monkeypatch, live_server)
    async with (
        websockets.connect(live_server.url) as agent_a,
        websockets.connect(live_server.url) as agent_b,
        websockets.connect(live_server.url) as control,
    ):
        await connect_agent(agent_a, live_server, "a", "agent-a")
        await connect_agent(agent_b, live_server, "b", "agent-b")
        await connect_control(control, live_server, "ctl")

        result = await asyncio.to_thread(run_pi_function, pi_commands.broadcast, "hello all")
        delivered_a = await recv_json(agent_a)
        delivered_b = await recv_json(agent_b)
        await assert_no_message(control)

    assert result.code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["op"] == "welcome"
    assert delivered_a["text"] == "hello all"
    assert delivered_b["text"] == "hello all"


@pytest.mark.asyncio
async def test_pi_cli_send_unknown_target_returns_protocol_error(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_pi_defaults(monkeypatch, live_server)

    result = await asyncio.to_thread(run_pi, ["send", "missing-agent", "hello"])

    lines = result.stdout.strip().splitlines()
    assert result.code == 1
    assert result.stderr == ""
    assert json.loads(lines[0])["op"] == "welcome"
    error = json.loads(lines[1])
    assert error["op"] == "error"
    assert error["code"] == "UNKNOWN_TARGET"


def test_pi_cli_list_unavailable_identity_returns_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(pi_commands, "DEFAULT_PORT", unused_tcp_port)

    result = run_pi(["list"])

    assert result.code == 1
    assert result.stdout == ""
    assert result.stderr == "server identity check failed\n"


def test_pi_cli_list_connection_failure_returns_error_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(pi_commands, "DEFAULT_PORT", unused_tcp_port)
    write_server_identity("127.0.0.1", unused_tcp_port)

    result = run_pi(["list"])

    assert result.code == 1
    assert result.stdout == ""
    assert result.stderr.startswith("inter-agent-pi: ")
    assert "Traceback" not in result.stderr
