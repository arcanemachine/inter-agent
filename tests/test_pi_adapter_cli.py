from __future__ import annotations

import json
from pathlib import Path

import pytest

import inter_agent.core.list as core_list
import inter_agent.core.send as core_send
import inter_agent.core.shutdown as core_shutdown
from inter_agent.adapters.pi import commands, listener
from inter_agent.adapters.pi.cli import main
from inter_agent.core.list import ListResult
from inter_agent.core.send import ProtocolErrorResult, SendResult
from inter_agent.core.shared import identity_path, write_server_identity
from inter_agent.core.shutdown import ShutdownResult


def test_status_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    code = main(["status", "--json"])

    assert code == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "unavailable",
        "host": "127.0.0.1",
        "port": 16837,
        "configured_host": "127.0.0.1",
        "configured_port": 16837,
        "host_source": "default",
        "port_source": "default",
        "data_dir": str(tmp_path),
        "data_dir_source": "env",
        "config_path": None,
        "discovered": False,
        "discovered_servers": [],
        "hints": [],
        "server_reachable": False,
        "identity_verified": False,
        "message": "No server is running. Start one with inter-agent-server",
        "core_list_supported": True,
        "adapter_list_exposed": True,
    }


def test_status_reports_identity_check_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INTER_AGENT_PORT", str(unused_tcp_port))
    write_server_identity("127.0.0.1", unused_tcp_port)
    identity_payload = json.loads(identity_path(unused_tcp_port).read_text(encoding="utf-8"))
    identity_payload["port"] = unused_tcp_port + 1
    identity_path(unused_tcp_port).write_text(json.dumps(identity_payload), encoding="utf-8")

    code = main(["status"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["state"] == "identity_check_failed"
    assert payload["identity_verified"] is False
    assert payload["message"] == "server identity metadata does not match requested endpoint"


def test_send_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str, str | None]] = []

    async def fake_send(
        host: str, port: int, to: str, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, to, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)

    code = commands.send("agent-b", "hello", "agent-a")

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "agent-b", "hello", "agent-a")]
    assert capsys.readouterr().out == '{"op": "welcome"}\n'


def test_send_cli_accepts_from_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str, str | None]] = []

    async def fake_send(
        host: str, port: int, to: str, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, to, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)

    assert main(["send", "agent-b", "hello", "--from", "agent-a"]) == 0

    assert calls == [("127.0.0.1", 16837, "agent-b", "hello", "agent-a")]
    assert capsys.readouterr().out == '{"op": "welcome"}\n'


def test_send_protocol_error_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_send(
        host: str, port: int, to: str, text: str, from_name: str | None = None
    ) -> SendResult:
        del from_name
        return SendResult(
            welcome='{"op": "welcome"}',
            welcome_payload={"op": "welcome"},
            error=ProtocolErrorResult(
                code="UNKNOWN_TARGET",
                message="unknown target: missing",
                raw=(
                    '{"op": "error", "code": "UNKNOWN_TARGET", '
                    '"message": "unknown target: missing"}'
                ),
            ),
        )

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)

    code = commands.send("missing", "hello")

    assert code == 1
    assert capsys.readouterr().out.splitlines() == [
        '{"op": "welcome"}',
        '{"op": "error", "code": "UNKNOWN_TARGET", "message": "unknown target: missing"}',
    ]


def test_broadcast_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str | None]] = []

    async def fake_broadcast(
        host: str, port: int, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "broadcast_message", fake_broadcast)

    code = commands.broadcast("hello all", "agent-a")

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "hello all", "agent-a")]
    assert capsys.readouterr().out == '{"op": "welcome"}\n'


def test_broadcast_cli_accepts_from_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str | None]] = []

    async def fake_broadcast(
        host: str, port: int, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "broadcast_message", fake_broadcast)

    assert main(["broadcast", "hello all", "--from", "agent-a"]) == 0

    assert calls == [("127.0.0.1", 16837, "hello all", "agent-a")]
    assert capsys.readouterr().out == '{"op": "welcome"}\n'


def test_list_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int]] = []

    async def fake_list(host: str, port: int) -> ListResult:
        calls.append((host, port))
        return ListResult(
            raw_response='{"op": "list_ok", "sessions": []}',
            response={"op": "list_ok", "sessions": []},
            sessions=(),
        )

    monkeypatch.setattr(core_list, "list_sessions", fake_list)

    code = commands.list_sessions()

    assert code == 0
    assert calls == [("127.0.0.1", 16837)]
    assert capsys.readouterr().out == '{"op": "list_ok", "sessions": []}\n'


def test_shutdown_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int]] = []

    async def fake_shutdown(host: str, port: int) -> ShutdownResult:
        calls.append((host, port))
        return ShutdownResult(
            response='{"op": "shutdown_ok"}',
            response_payload={"op": "shutdown_ok"},
        )

    monkeypatch.setattr(core_shutdown, "shutdown_server", fake_shutdown)

    code = commands.shutdown()

    assert code == 0
    assert calls == [("127.0.0.1", 16837)]
    assert capsys.readouterr().out == '{"op": "shutdown_ok"}\n'


def test_connect_uses_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, str, str | None]] = []

    async def fake_run_listener(
        host: str, port: int, name: str, label: str | None = None, **kwargs: object
    ) -> int:
        calls.append((host, port, name, label))
        return 0

    monkeypatch.setattr(listener, "run_listener", fake_run_listener)

    code = commands.connect("agent-a", "Agent A")

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "agent-a", "Agent A")]
