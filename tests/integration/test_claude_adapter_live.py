from __future__ import annotations

import asyncio
import io
import json
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout, suppress
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
from inter_agent.core import publish as core_publish
from inter_agent.core.auth import client_handshake
from inter_agent.core.client import build_hello
from inter_agent.core.server import run_server
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
    monkeypatch.setenv("INTER_AGENT_HOST", server.host)
    monkeypatch.setenv("INTER_AGENT_PORT", str(server.port))


def use_short_data_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
    server: LiveServer,
) -> None:
    """Short isolated data dir so control sockets fit the AF_UNIX path limit.

    The live server already fixed its secret at construction; pinning
    INTER_AGENT_SECRET lets the listener auth against it without depending on
    the token file living in this (short) data dir.
    """
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path_factory.mktemp("d")))
    monkeypatch.setenv("INTER_AGENT_SECRET", server.secret)


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
    response = json.loads(
        await client_handshake(ws, server.secret, build_hello(session_id, name, label))
    )
    assert response["op"] == "welcome"


async def connect_control(ws: ClientConnection, server: LiveServer, session_id: str) -> None:
    response = json.loads(await client_handshake(ws, server.secret, control_hello(session_id)))
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
    monkeypatch.setattr(claude_commands, "_connected_from_name", lambda: "agent-a")
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
    assert delivered["from_name"] == "agent-a"


@pytest.mark.asyncio
async def test_claude_python_broadcast_delivers_to_agents_only(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)
    monkeypatch.setattr(claude_commands, "_connected_from_name", lambda: "agent-a")
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
    assert delivered_a["from_name"] == "agent-a"
    assert delivered_b["text"] == "hello all"
    assert delivered_b["from_name"] == "agent-a"


@pytest.mark.asyncio
async def test_claude_cli_send_unknown_target_returns_protocol_error(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_live_claude_defaults(monkeypatch, live_server)
    monkeypatch.setattr(claude_commands, "_connected_from_name", lambda: "agent-a")

    result = await asyncio.to_thread(run_claude, ["send", "missing-agent", "hello"])

    assert result.code == 1
    assert result.stdout.strip() == ""
    assert result.stderr.splitlines() == [
        "inter-agent-claude: delivery failed (UNKNOWN_TARGET): unknown target: missing-agent",
    ]


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
    monkeypatch.setenv("INTER_AGENT_PORT", str(unused_tcp_port))

    result = run_claude(["shutdown"])

    assert result.code == 1
    assert result.stdout == ""
    assert result.stderr.startswith("inter-agent-claude: ")
    assert "Traceback" not in result.stderr


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
    monkeypatch.setenv("INTER_AGENT_PORT", str(unused_tcp_port))

    result = run_claude(args)

    assert result.code == 1


@pytest.mark.asyncio
async def test_listener_receives_direct_message(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    use_short_data_dir(monkeypatch, tmp_path_factory, live_server)
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
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    use_short_data_dir(monkeypatch, tmp_path_factory, live_server)
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
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    use_short_data_dir(monkeypatch, tmp_path_factory, live_server)
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
async def test_listener_retries_name_taken_once(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    use_short_data_dir(monkeypatch, tmp_path_factory, live_server)
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
        await asyncio.sleep(0.3)
        listener.stop()
        result = await asyncio.wait_for(task, timeout=2.0)

    assert result == 0
    output = out.getvalue()
    assert 'name "duplicate-name" is already in use; retrying as "duplicate-name-2"' in output
    assert 'connected as "duplicate-name-2"' in output


async def wait_for_connected_name(name: str) -> bool:
    deadline = asyncio.get_running_loop().time() + 2
    while asyncio.get_running_loop().time() < deadline:
        status = await asyncio.to_thread(run_claude, ["status", "--json"])
        payload = json.loads(status.stdout)
        if payload.get("connected_name") == name:
            return True
        await asyncio.sleep(0.05)
    return False


async def wait_for_channel_subscriber(channel: str, name: str) -> bool:
    """Poll ``channels`` until ``name`` is registered under ``channel``."""
    deadline = asyncio.get_running_loop().time() + 5
    while asyncio.get_running_loop().time() < deadline:
        result = await asyncio.to_thread(run_claude, ["channels", "--json"])
        payload = json.loads(result.stdout)
        for entry in payload.get("channels", []):
            if entry.get("name") == channel and name in entry.get("subscribers", []):
                return True
        await asyncio.sleep(0.1)
    return False


@pytest.mark.asyncio
async def test_claude_subscribe_unsubscribe_publish_channels_round_trip(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    use_short_data_dir(monkeypatch, tmp_path_factory, live_server)
    use_live_claude_defaults(monkeypatch, live_server)

    out = io.StringIO()
    listener = Listener(
        host=live_server.host,
        port=live_server.port,
        name="listener-a",
        output=out,
    )
    task = asyncio.create_task(listener.run())
    try:
        assert await wait_for_connected_name("listener-a")

        subscribe_result = await asyncio.to_thread(run_claude, ["subscribe", "updates"])
        assert subscribe_result.code == 0
        assert json.loads(subscribe_result.stdout) == {"op": "subscribe_ok", "channel": "updates"}

        channels_result = await asyncio.to_thread(run_claude, ["channels", "--json"])
        assert channels_result.code == 0
        payload = json.loads(channels_result.stdout)
        assert payload["op"] == "channels_ok"
        assert any(
            c["name"] == "updates" and "listener-a" in c["subscribers"] for c in payload["channels"]
        )

        publish_result = await asyncio.to_thread(
            run_claude, ["publish", "updates", "channel hello"]
        )
        assert publish_result.code == 0
        assert publish_result.stdout == ""  # Claude publish success is silent
        await asyncio.sleep(0.1)
        # The short-lived publisher uses the listener routing name, so the
        # listener suppresses its own channel delivery.
        assert "channel hello" not in out.getvalue()

        unsubscribe_result = await asyncio.to_thread(run_claude, ["unsubscribe", "updates"])
        assert unsubscribe_result.code == 0
        assert json.loads(unsubscribe_result.stdout) == {
            "op": "unsubscribe_ok",
            "channel": "updates",
        }

        # Publishing to the now-empty channel fails with UNKNOWN_CHANNEL.
        empty_result = await asyncio.to_thread(run_claude, ["publish", "updates", "no one"])
        assert empty_result.code == 1
        assert "UNKNOWN_CHANNEL" in empty_result.stderr
    finally:
        listener.stop()
        await task
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_claude_subscribe_without_listener_fails_cleanly(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    use_short_data_dir(monkeypatch, tmp_path_factory, live_server)
    use_live_claude_defaults(monkeypatch, live_server)

    result = await asyncio.to_thread(run_claude, ["subscribe", "updates"])

    assert result.code == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "not connected" in result.stderr


@pytest.mark.asyncio
async def test_claude_publish_suppresses_duplicate_within_window(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    use_short_data_dir(monkeypatch, tmp_path_factory, live_server)
    use_live_claude_defaults(monkeypatch, live_server)

    out = io.StringIO()
    listener = Listener(
        host=live_server.host,
        port=live_server.port,
        name="listener-a",
        output=out,
    )
    task = asyncio.create_task(listener.run())
    try:
        assert await wait_for_connected_name("listener-a")
        async with websockets.connect(live_server.url) as subscriber:
            await connect_agent(subscriber, live_server, "subscriber", "subscriber")
            subscribe_result = await send_json(
                subscriber, {"op": "subscribe", "channel": "updates"}
            )
            assert subscribe_result["op"] == "subscribe_ok"

            await asyncio.to_thread(run_claude, ["publish", "updates", "dup hello"])
            await asyncio.to_thread(run_claude, ["publish", "updates", "dup hello"])
            delivered = await recv_json(subscriber)
            assert delivered["text"] == "dup hello"
            await assert_no_message(subscriber)
    finally:
        listener.stop()
        await task
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_claude_listener_reapplies_subscriptions_after_server_restart(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path_factory.mktemp("d")))
    monkeypatch.setenv("INTER_AGENT_SECRET", "test-secret-fixed")
    monkeypatch.setenv("INTER_AGENT_HOST", "127.0.0.1")
    monkeypatch.setenv("INTER_AGENT_PORT", str(unused_tcp_port))

    server_task = asyncio.create_task(run_server("127.0.0.1", unused_tcp_port))
    await asyncio.sleep(0.1)
    out = io.StringIO()
    listener = Listener(host="127.0.0.1", port=unused_tcp_port, name="listener-a", output=out)
    task = asyncio.create_task(listener.run())
    try:
        assert await wait_for_connected_name("listener-a")
        await asyncio.to_thread(run_claude, ["subscribe", "updates"])

        # Bounce the server; the listener must reconnect and stay subscribed.
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task
        server_task = asyncio.create_task(run_server("127.0.0.1", unused_tcp_port))
        await asyncio.sleep(0.1)
        # Wait until the listener has reconnected and resubscribed.
        assert await wait_for_channel_subscriber("updates", "listener-a")

        publish_result = await core_publish.publish_to_channel(
            "127.0.0.1",
            unused_tcp_port,
            "updates",
            "post-restart",
            "external-publisher",
        )
        assert publish_result.error is None
        await asyncio.sleep(0.1)
        assert 'kind="channel" channel="updates"' in out.getvalue()
        assert "post-restart" in out.getvalue()
    finally:
        listener.stop()
        await task
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task
