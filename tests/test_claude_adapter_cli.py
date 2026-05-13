from __future__ import annotations

import json
from pathlib import Path

import pytest

import inter_agent.core.list as core_list
import inter_agent.core.send as core_send
import inter_agent.core.shutdown as core_shutdown
from inter_agent.adapters.claude import commands
from inter_agent.adapters.claude.cli import main
from inter_agent.core.list import ListResult
from inter_agent.core.send import ProtocolErrorResult, SendResult
from inter_agent.core.shared import identity_path, write_server_identity


class Capture:
    def __init__(self, code: int, stdout: str, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr


def run_claude(args: list[str], capsys: pytest.CaptureFixture[str]) -> Capture:
    code = main(args)
    captured = capsys.readouterr()
    return Capture(code=code, stdout=captured.out, stderr=captured.err)


def test_status_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    code = main(["status", "--json"])
    captured = capsys.readouterr()

    assert code == 0
    assert json.loads(captured.out) == {
        "state": "unavailable",
        "host": "127.0.0.1",
        "port": 9473,
        "server_reachable": False,
        "identity_verified": False,
        "message": "server identity not found",
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
    monkeypatch.setattr(commands, "DEFAULT_PORT", unused_tcp_port)
    write_server_identity("127.0.0.1", unused_tcp_port)
    identity_payload = json.loads(identity_path(unused_tcp_port).read_text(encoding="utf-8"))
    identity_payload["port"] = unused_tcp_port + 1
    identity_path(unused_tcp_port).write_text(json.dumps(identity_payload), encoding="utf-8")

    code = main(["status", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["state"] == "identity_check_failed"
    assert payload["identity_verified"] is False
    assert payload["message"] == "server identity metadata does not match requested endpoint"


def test_send_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str]] = []

    async def fake_send(host: str, port: int, to: str, text: str) -> SendResult:
        calls.append((host, port, to, text))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)

    code = commands.send("agent-b", "hello")

    assert code == 0
    assert calls == [("127.0.0.1", 9473, "agent-b", "hello")]
    assert capsys.readouterr().out == '{"op": "welcome"}\n'


def test_send_protocol_error_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_send(host: str, port: int, to: str, text: str) -> SendResult:
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
    calls: list[tuple[str, int, str]] = []

    async def fake_broadcast(host: str, port: int, text: str) -> SendResult:
        calls.append((host, port, text))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "broadcast_message", fake_broadcast)

    code = commands.broadcast("hello all")

    assert code == 0
    assert calls == [("127.0.0.1", 9473, "hello all")]
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
    assert calls == [("127.0.0.1", 9473)]
    assert capsys.readouterr().out == '{"op": "list_ok", "sessions": []}\n'


def test_shutdown_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int]] = []

    async def fake_shutdown(host: str, port: int) -> core_shutdown.ShutdownResult:
        calls.append((host, port))
        return core_shutdown.ShutdownResult(
            response='{"op": "shutdown_ok"}',
            response_payload={"op": "shutdown_ok"},
        )

    monkeypatch.setattr(core_shutdown, "shutdown_server", fake_shutdown)

    code = commands.shutdown()

    assert code == 0
    assert calls == [("127.0.0.1", 9473)]
    assert capsys.readouterr().out == '{"op": "shutdown_ok"}\n'
