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

from inter_agent.adapters.claude import commands as claude_commands
from inter_agent.adapters.claude.cli import main as claude_main
from inter_agent.adapters.claude.formatting import STDOUT_CAP
from inter_agent.adapters.claude.listener import Listener
from inter_agent.core.client import build_hello
from inter_agent.core.shared import control_hello


@dataclass(frozen=True)
class CommandCapture:
    code: int
    stdout: str
    stderr: str


def run_claude(args: list[str]) -> CommandCapture:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = claude_main(args)
    return CommandCapture(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def run_claude_function(function: Callable[..., int], *args: object) -> CommandCapture:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = function(*args)
    assert isinstance(code, int)
    return CommandCapture(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def use_live_claude_defaults(monkeypatch: pytest.MonkeyPatch, server: LiveServer) -> None:
    monkeypatch.setattr(claude_commands, "DEFAULT_HOST", server.host)
    monkeypatch.setattr(claude_commands, "DEFAULT_PORT", server.port)


async def wait_for_claude_status_state(state: str) -> dict[str, object]:
    deadline = asyncio.get_running_loop().time() + 1
    last_payload: dict[str, object] = {}
    while asyncio.get_running_loop().time() < deadline:
        status = await asyncio.to_thread(run_claude, ["status", "--json"])
        last_payload = json.loads(status.stdout)
        if last_payload.get("state") == state:
            return last_payload
        await asyncio.sleep(0.02)
    return last_payload


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
async def test_claude_status_reports_available_without_connected_agent(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)

    result = await asyncio.to_thread(run_claude, ["status", "--json"])

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
async def test_claude_cli_list_reports_live_agent_sessions(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)
    async with websockets.connect(live_server.url) as agent:
        await connect_agent(agent, live_server, "a", "agent-a", "Agent A")

        result = await asyncio.to_thread(run_claude, ["list"])

    assert result.code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "op": "list_ok",
        "sessions": [{"session_id": "a", "name": "agent-a", "label": "Agent A"}],
    }


@pytest.mark.asyncio
async def test_claude_python_send_delivers_to_live_agent(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)
    async with websockets.connect(live_server.url) as target:
        await connect_agent(target, live_server, "b", "agent-b")

        result = await asyncio.to_thread(
            run_claude_function, claude_commands.send, "agent-b", "hello"
        )
        delivered = await recv_json(target)

    assert result.code == 0
    assert result.stderr == ""
    assert result.stdout == ""
    assert delivered["op"] == "msg"
    assert delivered["to"] == "agent-b"
    assert delivered["text"] == "hello"


@pytest.mark.asyncio
async def test_claude_python_broadcast_delivers_to_agents_only(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)
    async with (
        websockets.connect(live_server.url) as agent_a,
        websockets.connect(live_server.url) as agent_b,
        websockets.connect(live_server.url) as control,
    ):
        await connect_agent(agent_a, live_server, "a", "agent-a")
        await connect_agent(agent_b, live_server, "b", "agent-b")
        await connect_control(control, live_server, "ctl")

        result = await asyncio.to_thread(
            run_claude_function, claude_commands.broadcast, "hello all"
        )
        delivered_a = await recv_json(agent_a)
        delivered_b = await recv_json(agent_b)
        await assert_no_message(control)

    assert result.code == 0
    assert result.stderr == ""
    assert result.stdout == ""
    assert delivered_a["text"] == "hello all"
    assert delivered_b["text"] == "hello all"


@pytest.mark.asyncio
async def test_claude_cli_send_unknown_target_returns_protocol_error(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)

    result = await asyncio.to_thread(run_claude, ["send", "missing-agent", "hello"])

    lines = result.stdout.strip().splitlines()
    assert result.code == 1
    assert result.stderr == ""
    assert len(lines) == 1
    error = json.loads(lines[0])
    assert error["op"] == "error"
    assert error["code"] == "UNKNOWN_TARGET"


@pytest.mark.asyncio
async def test_claude_cli_shutdown_stops_live_server(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)

    result = await asyncio.to_thread(run_claude, ["shutdown"])
    status_payload = await wait_for_claude_status_state("unavailable")

    assert result.code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"op": "shutdown_ok"}
    assert status_payload["state"] == "unavailable"


def test_claude_cli_shutdown_unavailable_identity_returns_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(claude_commands, "DEFAULT_PORT", unused_tcp_port)

    result = run_claude(["shutdown"])

    assert result.code == 1
    assert result.stdout == ""
    assert result.stderr == "No server is running. Start one with inter-agent-server\n"


@pytest.mark.parametrize(
    "args",
    [
        ["send", "agent-b", "hello"],
        ["broadcast", "hello"],
        ["list"],
    ],
)
def test_claude_cli_unavailable_identity_failures_use_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    args: list[str],
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(claude_commands, "DEFAULT_PORT", unused_tcp_port)

    result = run_claude(args)

    assert result.code == 1


@pytest.mark.asyncio
async def test_listener_receives_direct_message(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    use_live_claude_defaults(monkeypatch, live_server)

    out = io.StringIO()
    listener = Listener(
        host=live_server.host,
        port=live_server.port,
        name="listener-a",
        output=out,
    )

    task = asyncio.create_task(listener.run())
    await asyncio.sleep(0.3)

    async with websockets.connect(live_server.url) as sender:
        await connect_agent(sender, live_server, "snd", "sender")
        await sender.send(json.dumps({"op": "send", "to": "listener-a", "text": "direct hello"}))
        await asyncio.sleep(0.2)

    listener.stop()
    await task

    lines = [line for line in out.getvalue().splitlines() if line.startswith("[inter-agent msg=")]
    assert len(lines) == 1
    assert 'from="sender"' in lines[0]
    assert 'kind="direct"' in lines[0]
    assert "direct hello" in lines[0]


@pytest.mark.asyncio
async def test_listener_receives_broadcast_message(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    use_live_claude_defaults(monkeypatch, live_server)

    out = io.StringIO()
    listener = Listener(
        host=live_server.host,
        port=live_server.port,
        name="listener-b",
        output=out,
    )

    task = asyncio.create_task(listener.run())
    await asyncio.sleep(0.3)

    async with websockets.connect(live_server.url) as sender:
        await connect_agent(sender, live_server, "snd", "sender")
        await sender.send(json.dumps({"op": "broadcast", "text": "broadcast hello"}))
        await asyncio.sleep(0.2)

    listener.stop()
    await task

    lines = [line for line in out.getvalue().splitlines() if line.startswith("[inter-agent msg=")]
    assert len(lines) == 1
    assert 'from="sender"' in lines[0]
    assert 'kind="broadcast"' in lines[0]
    assert "broadcast hello" in lines[0]


@pytest.mark.asyncio
async def test_listener_truncates_long_messages(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    use_live_claude_defaults(monkeypatch, live_server)

    out = io.StringIO()
    listener = Listener(
        host=live_server.host,
        port=live_server.port,
        name="listener-c",
        output=out,
    )

    task = asyncio.create_task(listener.run())
    await asyncio.sleep(0.3)

    long_text = "x" * (STDOUT_CAP + 100)
    async with websockets.connect(live_server.url) as sender:
        await connect_agent(sender, live_server, "snd", "sender")
        await sender.send(json.dumps({"op": "broadcast", "text": long_text}))
        await asyncio.sleep(0.2)

    listener.stop()
    await task

    lines = [line for line in out.getvalue().splitlines() if line.startswith("[inter-agent msg=")]
    assert len(lines) == 2
    assert "truncated=" in lines[0]
    assert "[inter-agent msg=" in lines[1] and " cont]" in lines[1]


@pytest.mark.asyncio
async def test_listener_exits_on_name_taken(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    use_live_claude_defaults(monkeypatch, live_server)

    out = io.StringIO()
    async with websockets.connect(live_server.url) as first:
        await connect_agent(first, live_server, "first", "duplicate-name")

        listener = Listener(
            host=live_server.host,
            port=live_server.port,
            name="duplicate-name",
            output=out,
        )
        task = asyncio.create_task(listener.run())
        result = await asyncio.wait_for(task, timeout=2.0)

    assert result == 1
    assert "NAME_TAKEN" in out.getvalue()
