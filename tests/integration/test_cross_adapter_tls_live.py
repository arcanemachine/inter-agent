from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import redirect_stderr, redirect_stdout, suppress
from dataclasses import dataclass
from pathlib import Path

import pytest
import websockets

from inter_agent.adapters.claude import commands as claude_commands
from inter_agent.adapters.claude.cli import main as claude_main
from inter_agent.adapters.claude.listener import Listener as ClaudeListener
from inter_agent.adapters.pi import commands as pi_commands
from inter_agent.adapters.pi.cli import main as pi_main
from inter_agent.adapters.pi.listener import run_listener as run_pi_listener
from inter_agent.core.server import run_server
from inter_agent.core.status import check_server_status
from inter_agent.core.tls import (
    build_client_ssl_context,
    default_cert_path,
    default_key_path,
    ensure_tls_material,
)
from inter_agent.core.transport import websocket_uri

HOST = "127.0.0.1"
# A fixed, test-only secret. It is never printed in assertions or reports.
TEST_SECRET = "tls-matrix-fixed-test-secret-do-not-use"


@dataclass(frozen=True)
class CommandCapture:
    code: int
    stdout: str
    stderr: str


def run_command(function: Callable[..., int], *args: object) -> CommandCapture:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = function(*args)
    return CommandCapture(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def run_pi(args: list[str]) -> CommandCapture:
    return run_command(pi_main, args)


def run_claude(args: list[str]) -> CommandCapture:
    return run_command(claude_main, args)


async def wait_until(predicate: Callable[[], object], timeout: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        result = predicate()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("timed out waiting for TLS matrix state")


def pi_messages(output: io.StringIO) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    for line in output.getvalue().splitlines():
        if not line.strip():
            continue
        try:
            payload: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("op") == "msg":
            messages.append({str(key): value for key, value in payload.items()})
    return messages


def claude_msg_lines(output: io.StringIO) -> list[str]:
    return [line for line in output.getvalue().splitlines() if line.startswith("[inter-agent msg=")]


def assert_no_leakage(*streams: str) -> None:
    """Assert no traceback, shared secret, or private-key PEM content leaks."""
    for stream in streams:
        assert "Traceback" not in stream
        assert TEST_SECRET not in stream
        assert "PRIVATE KEY" not in stream


class TlsServer:
    """One isolated loopback wss:// server with generated certificate material."""

    def __init__(self, host: str, port: int, data_dir: Path, secret: str) -> None:
        self.host = host
        self.port = port
        self.data_dir = data_dir
        self.secret = secret
        self.cert_path = default_cert_path(data_dir)
        self.task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.task = asyncio.create_task(
            run_server(self.host, self.port, tls=True, data_dir=self.data_dir)
        )
        await self.wait_available()

    async def wait_available(self, timeout: float = 5.0) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        last_state = ""
        while asyncio.get_running_loop().time() < deadline:
            status = await check_server_status(
                self.host, self.port, timeout=0.3, tls=True, data_dir=self.data_dir
            )
            last_state = status.state
            if status.state == "available":
                return
            await asyncio.sleep(0.05)
        raise AssertionError(f"TLS server did not become available: state={last_state}")

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None

    async def restart(self) -> None:
        await self.stop()
        await self.start()


@pytest.fixture
async def tls_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
    unused_tcp_port: int,
) -> AsyncIterator[TlsServer]:
    # Short data directory keeps AF_UNIX control-socket paths within limits.
    data_dir = tmp_path_factory.mktemp("d")
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(tmp_path_factory.mktemp("c") / "missing.json"))
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("INTER_AGENT_SECRET", TEST_SECRET)
    monkeypatch.setenv("INTER_AGENT_HOST", HOST)
    monkeypatch.setenv("INTER_AGENT_PORT", str(unused_tcp_port))
    monkeypatch.setenv("INTER_AGENT_TLS", "true")
    # Point clients/helpers at the generated certificate explicitly so the
    # resolved certificate source is concrete and consistent across the
    # listeners (programmatic cert_path) and the status/list helpers (env).
    # The private key is never exposed to clients.
    server = TlsServer(HOST, unused_tcp_port, data_dir, TEST_SECRET)
    monkeypatch.setenv("INTER_AGENT_TLS_CERT", str(server.cert_path))
    monkeypatch.delenv("INTER_AGENT_TLS_KEY", raising=False)
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


@dataclass
class BothListeners:
    pi_name: str
    claude_name: str
    pi_output: io.StringIO
    claude_output: io.StringIO
    pi_task: asyncio.Task[int]
    claude_listener: ClaudeListener
    claude_task: asyncio.Task[int]


@pytest.fixture
async def both_listeners(tls_server: TlsServer) -> AsyncIterator[BothListeners]:
    pi_name = "pi-tls-matrix"
    claude_name = "claude-tls-matrix"
    pi_output = io.StringIO()
    claude_output = io.StringIO()

    pi_task = asyncio.create_task(
        run_pi_listener(
            tls_server.host,
            tls_server.port,
            pi_name,
            None,
            output=pi_output,
            tls=True,
            data_dir=tls_server.data_dir,
            tls_cert_path=tls_server.cert_path,
        )
    )
    claude_listener = ClaudeListener(
        host=tls_server.host,
        port=tls_server.port,
        name=claude_name,
        output=claude_output,
        tls=True,
        data_dir=tls_server.data_dir,
        tls_cert_path=tls_server.cert_path,
    )
    claude_task = asyncio.create_task(claude_listener.run())
    try:
        await wait_until(lambda: '"op":"welcome"' in pi_output.getvalue().replace(" ", ""))
        await wait_until(lambda: f'connected as "{claude_name}"' in claude_output.getvalue())
        yield BothListeners(
            pi_name=pi_name,
            claude_name=claude_name,
            pi_output=pi_output,
            claude_output=claude_output,
            pi_task=pi_task,
            claude_listener=claude_listener,
            claude_task=claude_task,
        )
    finally:
        claude_listener.stop()
        with suppress(asyncio.CancelledError):
            await claude_task
        pi_task.cancel()
        with suppress(asyncio.CancelledError):
            await pi_task


async def wait_for_exact_names(
    tls_server: TlsServer, expected: list[str], timeout: float = 8.0
) -> None:
    """Poll list until the registered agent names are exactly ``expected``,
    each once, with no suffixed or duplicate registrations."""

    async def exact() -> bool:
        result = await asyncio.to_thread(run_pi, ["list"])
        if result.code != 0:
            return False
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False
        listed = [entry.get("name") for entry in payload.get("sessions", [])]
        return sorted(listed) == sorted(expected) and len(listed) == len(expected)

    await wait_until(exact, timeout=timeout)


async def current_list_names() -> list[str]:
    result = await asyncio.to_thread(run_pi, ["list"])
    if result.code != 0:
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [entry.get("name") for entry in payload.get("sessions", [])]


# ── Phase 1A: generated material and permissions ────────────────────────────


@pytest.mark.asyncio
async def test_tls_server_generates_material_with_restrictive_permissions(
    tls_server: TlsServer,
) -> None:
    assert tls_server.cert_path.exists()
    key_path = default_key_path(tls_server.data_dir)
    assert key_path.exists()
    if os.name == "posix":
        assert tls_server.data_dir.stat().st_mode & 0o777 == 0o700
        assert tls_server.cert_path.stat().st_mode & 0o777 == 0o600
        assert key_path.stat().st_mode & 0o777 == 0o600

    status = await check_server_status(
        tls_server.host, tls_server.port, timeout=0.5, tls=True, data_dir=tls_server.data_dir
    )
    assert status.state == "available"


# ── Phase 1B: real adapter listeners authenticate and register once ─────────


@pytest.mark.asyncio
async def test_tls_listeners_authenticate_and_appear_once_in_status_and_list(
    both_listeners: BothListeners,
    tls_server: TlsServer,
) -> None:
    await wait_for_exact_names(tls_server, [both_listeners.pi_name, both_listeners.claude_name])

    pi_status = await asyncio.to_thread(run_pi, ["status", "--json"])
    assert pi_status.code == 0
    pi_payload = json.loads(pi_status.stdout)
    assert pi_payload["state"] == "available"
    assert pi_payload["tls"] is True
    assert pi_payload["tls_source"] == "env"
    assert pi_payload["scheme"] == "wss"
    assert pi_payload["port"] == tls_server.port
    assert pi_payload["data_dir"] == str(tls_server.data_dir)
    assert pi_payload["tls_cert_path"] == str(tls_server.cert_path)
    assert pi_payload["tls_cert_source"] == "env"

    claude_status = await asyncio.to_thread(run_claude, ["status", "--json"])
    assert claude_status.code == 0
    claude_payload = json.loads(claude_status.stdout)
    assert claude_payload["state"] == "available"
    assert claude_payload["tls"] is True
    assert claude_payload["tls_source"] == "env"
    assert claude_payload["scheme"] == "wss"
    assert claude_payload["port"] == tls_server.port
    assert claude_payload["data_dir"] == str(tls_server.data_dir)
    assert claude_payload["tls_cert_path"] == str(tls_server.cert_path)
    assert claude_payload["tls_cert_source"] == "env"
    assert claude_payload["connected_name"] == both_listeners.claude_name

    # Control sessions used by status/list must not appear as persistent agents;
    # both adapters appear exactly once each.
    await wait_for_exact_names(tls_server, [both_listeners.pi_name, both_listeners.claude_name])
    for result in (
        await asyncio.to_thread(run_pi, ["list"]),
        await asyncio.to_thread(run_claude, ["list"]),
    ):
        assert result.code == 0
        payload = json.loads(result.stdout)
        listed = [entry["name"] for entry in payload["sessions"]]
        assert sorted(listed) == sorted([both_listeners.pi_name, both_listeners.claude_name])
        assert len(listed) == 2


# ── Phase 1C: direct and broadcast delivery both directions ─────────────────


@pytest.mark.asyncio
async def test_tls_direct_and_broadcast_delivery_both_directions(
    both_listeners: BothListeners,
    tls_server: TlsServer,
) -> None:
    pi_name = both_listeners.pi_name
    claude_name = both_listeners.claude_name
    pi_out = both_listeners.pi_output
    claude_out = both_listeners.claude_output

    # Pi -> Claude direct.
    pi_to_claude = "pi-direct-to-claude"
    send_pc = await asyncio.to_thread(
        run_command, pi_commands.send, claude_name, pi_to_claude, pi_name
    )
    assert send_pc.code == 0
    assert json.loads(send_pc.stdout)["op"] == "welcome"
    await wait_until(lambda: any(pi_to_claude in line for line in claude_msg_lines(claude_out)))
    pc_lines = [line for line in claude_msg_lines(claude_out) if pi_to_claude in line]
    assert len(pc_lines) == 1
    assert f'from="{pi_name}"' in pc_lines[0]
    assert 'kind="direct"' in pc_lines[0]
    assert f'to="{claude_name}"' in pc_lines[0]

    # Claude -> Pi direct (from_name resolved from the live Claude listener).
    claude_to_pi = "claude-direct-to-pi"
    send_cp = await asyncio.to_thread(run_command, claude_commands.send, pi_name, claude_to_pi)
    assert send_cp.code == 0
    assert send_cp.stdout == ""
    await wait_until(lambda: any(m.get("text") == claude_to_pi for m in pi_messages(pi_out)))
    cp_msgs = [m for m in pi_messages(pi_out) if m.get("text") == claude_to_pi]
    assert len(cp_msgs) == 1
    assert cp_msgs[0]["to"] == pi_name
    assert cp_msgs[0]["from_name"] == claude_name
    assert "channel" not in cp_msgs[0]

    # Pi -> Claude broadcast. The helper sends from a short-lived control
    # session using the Pi listener's routing name as display metadata.
    # Broadcast delivery is session-based: the sending control session is
    # excluded, but every other connected agent session — including the
    # same-named Pi listener, which is a distinct session — receives the
    # broadcast exactly once.
    bcast_pc = "pi-broadcast-to-claude"
    bcast_pc_result = await asyncio.to_thread(run_command, pi_commands.broadcast, bcast_pc, pi_name)
    assert bcast_pc_result.code == 0
    assert json.loads(bcast_pc_result.stdout)["op"] == "welcome"
    await wait_until(lambda: any(bcast_pc in line for line in claude_msg_lines(claude_out)))
    await wait_until(lambda: any(m.get("text") == bcast_pc for m in pi_messages(pi_out)))
    # The other adapter (Claude) receives it exactly once.
    bcast_pc_lines = [line for line in claude_msg_lines(claude_out) if bcast_pc in line]
    assert len(bcast_pc_lines) == 1
    assert f'from="{pi_name}"' in bcast_pc_lines[0]
    assert 'kind="broadcast"' in bcast_pc_lines[0]
    # The same-named Pi listener is a distinct session and also receives it
    # exactly once.
    bcast_pc_pi = [m for m in pi_messages(pi_out) if m.get("text") == bcast_pc]
    assert len(bcast_pc_pi) == 1
    assert bcast_pc_pi[0]["from_name"] == pi_name
    assert "to" not in bcast_pc_pi[0]
    assert "channel" not in bcast_pc_pi[0]
    # The sending control session receives no msg: the helper result is a
    # welcome envelope, not a delivered msg.
    assert json.loads(bcast_pc_result.stdout)["op"] != "msg"

    # Claude -> Pi broadcast. Same session-based semantics: the sending
    # control session is excluded; both persistent listeners (including the
    # same-named Claude listener) receive it exactly once.
    bcast_cp = "claude-broadcast-to-pi"
    bcast_cp_result = await asyncio.to_thread(run_command, claude_commands.broadcast, bcast_cp)
    assert bcast_cp_result.code == 0
    assert bcast_cp_result.stdout == ""
    await wait_until(lambda: any(m.get("text") == bcast_cp for m in pi_messages(pi_out)))
    await wait_until(lambda: any(bcast_cp in line for line in claude_msg_lines(claude_out)))
    # The other adapter (Pi) receives it exactly once.
    bcast_cp_msgs = [m for m in pi_messages(pi_out) if m.get("text") == bcast_cp]
    assert len(bcast_cp_msgs) == 1
    assert bcast_cp_msgs[0]["from_name"] == claude_name
    assert "to" not in bcast_cp_msgs[0]
    assert "channel" not in bcast_cp_msgs[0]
    # The same-named Claude listener is a distinct session and also receives
    # it exactly once.
    bcast_cp_claude = [line for line in claude_msg_lines(claude_out) if bcast_cp in line]
    assert len(bcast_cp_claude) == 1
    assert f'from="{claude_name}"' in bcast_cp_claude[0]
    assert 'kind="broadcast"' in bcast_cp_claude[0]
    # The sending control session receives no msg: Claude publish/broadcast
    # success is silent.
    assert bcast_cp_result.stdout == ""

    assert_no_leakage(pi_out.getvalue(), claude_out.getvalue())


# ── Phase 1D: pub/sub and control paths ──────────────────────────────────────


@pytest.mark.asyncio
async def test_tls_pubsub_and_control_paths(
    both_listeners: BothListeners,
    tls_server: TlsServer,
) -> None:
    pi_name = both_listeners.pi_name
    claude_name = both_listeners.claude_name
    pi_out = both_listeners.pi_output
    claude_out = both_listeners.claude_output
    channel = "tls-matrix-channel"

    pi_sub = await asyncio.to_thread(run_command, pi_commands.subscribe, channel, pi_name)
    claude_sub = await asyncio.to_thread(run_command, claude_commands.subscribe, channel)
    assert pi_sub.code == 0
    assert claude_sub.code == 0

    expected_entry = {"name": channel, "subscribers": sorted([claude_name, pi_name])}

    async def channel_has_both() -> bool:
        for result in (
            await asyncio.to_thread(run_pi, ["channels", "--json"]),
            await asyncio.to_thread(run_claude, ["channels", "--json"]),
        ):
            if result.code != 0:
                return False
            payload = json.loads(result.stdout)
            entries = payload.get("channels", [])
            if expected_entry not in entries:
                return False
        return True

    await wait_until(channel_has_both)

    # Claude -> Pi publish: Pi receives once, no echo in Claude output.
    pub_cp = "claude-channel-to-pi"
    pub_cp_result = await asyncio.to_thread(run_command, claude_commands.publish, channel, pub_cp)
    assert pub_cp_result.code == 0
    assert pub_cp_result.stdout == ""
    await wait_until(lambda: any(m.get("text") == pub_cp for m in pi_messages(pi_out)))
    pub_cp_msgs = [m for m in pi_messages(pi_out) if m.get("text") == pub_cp]
    assert len(pub_cp_msgs) == 1
    assert pub_cp_msgs[0]["channel"] == channel
    assert pub_cp_msgs[0]["from_name"] == claude_name
    assert pub_cp not in claude_out.getvalue()

    # Pi -> Claude publish: Claude receives once, no echo in Pi output.
    pub_pc = "pi-channel-to-claude"
    pub_pc_result = await asyncio.to_thread(
        run_command, pi_commands.publish, channel, pub_pc, pi_name
    )
    assert pub_pc_result.code == 0
    await wait_until(lambda: any(pub_pc in line for line in claude_msg_lines(claude_out)))
    pub_pc_lines = [line for line in claude_msg_lines(claude_out) if pub_pc in line]
    assert len(pub_pc_lines) == 1
    assert f'from="{pi_name}"' in pub_pc_lines[0]
    assert f'channel="{channel}"' in pub_pc_lines[0]
    assert 'kind="channel"' in pub_pc_lines[0]
    assert not any(m.get("text") == pub_pc for m in pi_messages(pi_out))

    # Unsubscribe Pi -> only Claude remains.
    pi_unsub = await asyncio.to_thread(run_command, pi_commands.unsubscribe, channel, pi_name)
    assert pi_unsub.code == 0

    async def only_claude_subscribed() -> bool:
        result = await asyncio.to_thread(run_claude, ["channels", "--json"])
        if result.code != 0:
            return False
        entries = json.loads(result.stdout).get("channels", [])
        return any(
            e.get("name") == channel and e.get("subscribers") == [claude_name] for e in entries
        )

    await wait_until(only_claude_subscribed)

    # Unsubscribe Claude -> channel disappears.
    claude_unsub = await asyncio.to_thread(run_command, claude_commands.unsubscribe, channel)
    assert claude_unsub.code == 0

    async def channel_gone() -> bool:
        result = await asyncio.to_thread(run_claude, ["channels", "--json"])
        if result.code != 0:
            return False
        entries = json.loads(result.stdout).get("channels", [])
        return all(e.get("name") != channel for e in entries)

    await wait_until(channel_gone)

    assert_no_leakage(pi_out.getvalue(), claude_out.getvalue())


# ── Phase 1E: restart and subscription recovery ─────────────────────────────


@pytest.mark.asyncio
async def test_tls_listeners_reconnect_with_same_names_and_subscriptions(
    both_listeners: BothListeners,
    tls_server: TlsServer,
) -> None:
    pi_name = both_listeners.pi_name
    claude_name = both_listeners.claude_name
    pi_out = both_listeners.pi_output
    claude_out = both_listeners.claude_output
    channel = "tls-restart-channel"

    pi_sub = await asyncio.to_thread(run_command, pi_commands.subscribe, channel, pi_name)
    claude_sub = await asyncio.to_thread(run_command, claude_commands.subscribe, channel)
    assert pi_sub.code == 0
    assert claude_sub.code == 0

    cert_hash = hashlib.sha256(tls_server.cert_path.read_bytes()).hexdigest()

    # Restart only the server; keep both listeners running so they reconnect.
    await tls_server.restart()

    # Both exact names must reappear exactly once each after reconnect; no
    # suffixed or duplicate registration is accepted.
    await wait_for_exact_names(tls_server, [pi_name, claude_name])
    listed = await current_list_names()
    assert sorted(listed) == sorted([pi_name, claude_name])
    assert len(listed) == 2

    async def both_resubscribed() -> bool:
        result = await asyncio.to_thread(run_claude, ["channels", "--json"])
        if result.code != 0:
            return False
        entries = json.loads(result.stdout).get("channels", [])
        return any(
            e.get("name") == channel
            and sorted(e.get("subscribers", [])) == sorted([pi_name, claude_name])
            for e in entries
        )

    await wait_until(both_resubscribed)

    # The certificate material is reused, not regenerated.
    assert hashlib.sha256(tls_server.cert_path.read_bytes()).hexdigest() == cert_hash

    # Post-restart traffic: exact-once delivery both directions.
    pub_cp = "restart-claude-to-pi"
    pub_cp_result = await asyncio.to_thread(run_command, claude_commands.publish, channel, pub_cp)
    assert pub_cp_result.code == 0
    await wait_until(lambda: any(m.get("text") == pub_cp for m in pi_messages(pi_out)))
    assert len([m for m in pi_messages(pi_out) if m.get("text") == pub_cp]) == 1

    pub_pc = "restart-pi-to-claude"
    pub_pc_result = await asyncio.to_thread(
        run_command, pi_commands.publish, channel, pub_pc, pi_name
    )
    assert pub_pc_result.code == 0
    await wait_until(lambda: any(pub_pc in line for line in claude_msg_lines(claude_out)))
    assert len([line for line in claude_msg_lines(claude_out) if pub_pc in line]) == 1

    direct_pc = "restart-direct-pi-to-claude"
    direct_pc_result = await asyncio.to_thread(
        run_command, pi_commands.send, claude_name, direct_pc, pi_name
    )
    assert direct_pc_result.code == 0
    await wait_until(lambda: any(direct_pc in line for line in claude_msg_lines(claude_out)))
    assert len([line for line in claude_msg_lines(claude_out) if direct_pc in line]) == 1

    direct_cp = "restart-direct-claude-to-pi"
    direct_cp_result = await asyncio.to_thread(
        run_command, claude_commands.send, pi_name, direct_cp
    )
    assert direct_cp_result.code == 0
    await wait_until(lambda: any(m.get("text") == direct_cp for m in pi_messages(pi_out)))
    assert len([m for m in pi_messages(pi_out) if m.get("text") == direct_cp]) == 1

    assert_no_leakage(pi_out.getvalue(), claude_out.getvalue())


# ── Phase 1F: negative transport/auth cases ──────────────────────────────────


@pytest.mark.asyncio
async def test_plaintext_client_cannot_handshake_with_tls_server(
    tls_server: TlsServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A raw ws:// client must not authenticate or list agents against the wss port.
    with pytest.raises((OSError, websockets.WebSocketException)):
        async with websockets.connect(f"ws://{tls_server.host}:{tls_server.port}"):
            pass

    # An adapter helper probing plaintext against the TLS port fails bounded,
    # lists nothing, and emits no traceback or private-key content.
    monkeypatch.setenv("INTER_AGENT_TLS", "false")
    result = await asyncio.to_thread(run_pi, ["list"])
    assert result.code == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("inter-agent-pi: ")
    assert_no_leakage(result.stderr, result.stdout)

    # Restore trusted TLS and prove the negative client registered nothing.
    monkeypatch.setenv("INTER_AGENT_TLS", "true")
    trusted = await asyncio.to_thread(run_pi, ["list"])
    assert trusted.code == 0
    assert json.loads(trusted.stdout)["sessions"] == []


@pytest.mark.asyncio
async def test_untrusted_certificate_cannot_authenticate(
    tls_server: TlsServer,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Generate an unrelated certificate in a separate data directory.
    other_data_dir = tmp_path_factory.mktemp("untrusted")
    other_cert, _other_key = ensure_tls_material(other_data_dir, tls_server.host)
    untrusted_context = build_client_ssl_context(other_data_dir, other_cert)

    # Probing the real wss server with the unrelated CA must fail without
    # bypassing certificate validation.
    with pytest.raises((OSError, websockets.WebSocketException)):
        async with websockets.connect(
            websocket_uri(tls_server.host, tls_server.port, tls=True),
            ssl=untrusted_context,
        ):
            pass

    # The adapter helper path must fail bounded, register nothing, and leak no
    # secret or private-key content.
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(other_data_dir))
    monkeypatch.setenv("INTER_AGENT_TLS_CERT", str(other_cert))
    result = await asyncio.to_thread(run_pi, ["list"])
    assert result.code == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("inter-agent-pi: ")
    assert_no_leakage(result.stderr, result.stdout)

    # Restore the trusted certificate/data dir and prove no registration occurred.
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tls_server.data_dir))
    monkeypatch.setenv("INTER_AGENT_TLS_CERT", str(tls_server.cert_path))
    trusted = await asyncio.to_thread(run_pi, ["list"])
    assert trusted.code == 0
    assert json.loads(trusted.stdout)["sessions"] == []


@pytest.mark.asyncio
async def test_missing_configured_certificate_reports_bounded_failure(
    tls_server: TlsServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_cert = tls_server.data_dir / "does-not-exist.pem"
    monkeypatch.setenv("INTER_AGENT_TLS_CERT", str(missing_cert))

    result = await asyncio.to_thread(run_pi, ["status", "--json"])
    assert result.code == 0
    payload = json.loads(result.stdout)
    assert payload["state"] == "unavailable"
    assert payload["message"].startswith("TLS configuration failed:")
    # The missing path must be named so the failure is actionable.
    assert str(missing_cert) in payload["message"]
    assert_no_leakage(result.stdout, result.stderr)

    # Restore the trusted certificate and prove the server is reachable again.
    monkeypatch.setenv("INTER_AGENT_TLS_CERT", str(tls_server.cert_path))
    trusted = await asyncio.to_thread(run_pi, ["status", "--json"])
    assert trusted.code == 0
    assert json.loads(trusted.stdout)["state"] == "available"


@pytest.mark.asyncio
async def test_wrong_secret_over_trusted_tls_fails_authentication(
    tls_server: TlsServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrong_secret = "wrong-tls-matrix-secret"
    # Trusted certificate, but a different shared secret: HMAC must still fail.
    monkeypatch.setenv("INTER_AGENT_SECRET", wrong_secret)

    # The status helper reports the canonical auth_failed state, proving TLS
    # did not bypass the shared-secret challenge-response.
    status_result = await asyncio.to_thread(run_pi, ["status", "--json"])
    assert status_result.code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["state"] == "auth_failed"
    assert status_payload["server_reachable"] is True
    assert_no_leakage(status_result.stdout, status_result.stderr)
    assert wrong_secret not in status_result.stdout
    assert wrong_secret not in status_result.stderr

    # The list helper fails bounded with the canonical auth diagnostic.
    list_result = await asyncio.to_thread(run_pi, ["list"])
    assert list_result.code == 1
    assert list_result.stdout == ""
    assert "authentication failed" in list_result.stderr.lower()
    assert "Traceback" not in list_result.stderr
    assert wrong_secret not in list_result.stderr
    assert TEST_SECRET not in list_result.stderr

    # Restore the trusted secret and prove the wrong-secret client registered
    # nothing on the bus.
    monkeypatch.setenv("INTER_AGENT_SECRET", TEST_SECRET)
    trusted = await asyncio.to_thread(run_pi, ["list"])
    assert trusted.code == 0
    assert json.loads(trusted.stdout)["sessions"] == []
