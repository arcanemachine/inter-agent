from __future__ import annotations

import json
from pathlib import Path

import pytest

import inter_agent.core.list as core_list
import inter_agent.core.send as core_send
import inter_agent.core.shutdown as core_shutdown
from inter_agent.adapters.claude import commands, state
from inter_agent.adapters.claude.cli import main
from inter_agent.core.list import ListResult
from inter_agent.core.send import ProtocolErrorResult, SendResult


class Capture:
    def __init__(self, code: int, stdout: str, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the adapter data dir so send-dedup state never leaks between
    tests or touches the real on-disk cache."""
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))


def run_claude(args: list[str], capsys: pytest.CaptureFixture[str]) -> Capture:
    code = main(args)
    captured = capsys.readouterr()
    return Capture(code=code, stdout=captured.out, stderr=captured.err)


def test_status_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INTER_AGENT_PORT", str(unused_tcp_port))

    code = main(["status", "--json"])
    captured = capsys.readouterr()

    assert code == 0
    assert json.loads(captured.out) == {
        "state": "unavailable",
        "host": "127.0.0.1",
        "port": unused_tcp_port,
        "configured_host": "127.0.0.1",
        "configured_port": unused_tcp_port,
        "host_source": "default",
        "port_source": "env",
        "data_dir": str(tmp_path),
        "data_dir_source": "env",
        "config_path": None,
        "hints": ["start inter-agent-server or check INTER_AGENT_HOST and INTER_AGENT_PORT"],
        "server_reachable": False,
        "message": "server connection failed",
        "core_list_supported": True,
        "adapter_list_exposed": True,
        "connected": False,
        "connected_name": None,
    }


def test_send_suppresses_duplicate_within_window(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str, str | None]] = []

    async def fake_send(
        host: str, port: int, to: str, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, to, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    assert commands.send("agent-b", "hello") == 0
    assert commands.send("agent-b", "hello") == 0

    # Only the first invocation reaches the bus.
    assert calls == [("127.0.0.1", 16837, "agent-b", "hello", "agent-a")]


def test_broadcast_suppresses_duplicate_within_window(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str | None]] = []

    async def fake_broadcast(
        host: str, port: int, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "broadcast_message", fake_broadcast)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    assert commands.broadcast("hello all") == 0
    assert commands.broadcast("hello all") == 0

    assert calls == [("127.0.0.1", 16837, "hello all", "agent-a")]


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
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = commands.send("agent-b", "hello")

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "agent-b", "hello", "agent-a")]
    assert capsys.readouterr().out == ""


def test_send_protocol_error_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_send(
        host: str, port: int, to: str, text: str, from_name: str | None = None
    ) -> SendResult:
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
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = commands.send("missing", "hello")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "inter-agent-claude: delivery failed (UNKNOWN_TARGET): unknown target: missing",
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
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = commands.broadcast("hello all")

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "hello all", "agent-a")]
    assert capsys.readouterr().out == ""


def test_send_requires_connected_listener(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_send(
        host: str, port: int, to: str, text: str, from_name: str | None = None
    ) -> SendResult:
        raise AssertionError("send should not be called")

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: None)

    code = commands.send("agent-b", "hello")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "not connected. Run '/inter-agent connect' first.\n"


def test_broadcast_requires_connected_listener(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_broadcast(
        host: str, port: int, text: str, from_name: str | None = None
    ) -> SendResult:
        raise AssertionError("broadcast should not be called")

    monkeypatch.setattr(core_send, "broadcast_message", fake_broadcast)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: None)

    code = commands.broadcast("hello all")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "not connected. Run '/inter-agent connect' first.\n"


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


def test_send_uses_connected_name_instead_of_from_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str, str | None]] = []

    async def fake_send(
        host: str, port: int, to: str, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, to, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-connected")

    code = main(["send", "agent-b", "hello", "--from", "agent-a"])

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "agent-b", "hello", "agent-connected")]


def test_broadcast_uses_connected_name_instead_of_from_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str | None]] = []

    async def fake_broadcast(
        host: str, port: int, text: str, from_name: str | None = None
    ) -> SendResult:
        calls.append((host, port, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "broadcast_message", fake_broadcast)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-connected")

    code = main(["broadcast", "hello all", "--from", "agent-a"])

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "hello all", "agent-connected")]


def test_message_prints_full_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    log = state.messages_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        json.dumps({"msg_id": "m1", "from_name": "x", "text": "the full text"}) + "\n",
        encoding="utf-8",
    )

    assert commands.message("m1") == 0
    assert capsys.readouterr().out == "the full text\n"


def test_message_json_prints_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    log = state.messages_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        json.dumps({"msg_id": "m1", "from_name": "x", "text": "the full text"}) + "\n",
        encoding="utf-8",
    )

    assert commands.message("m1", as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"msg_id": "m1", "from_name": "x", "text": "the full text"}


def test_message_missing_returns_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    assert commands.message("nope") == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no message found" in captured.err


def test_message_cli_dispatches_to_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    log = state.messages_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        json.dumps({"msg_id": "m1", "from_name": "x", "text": "via cli"}) + "\n",
        encoding="utf-8",
    )

    assert main(["messages", "m1"]) == 0
    assert capsys.readouterr().out == "via cli\n"


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
    assert calls == [("127.0.0.1", 16837)]
    assert capsys.readouterr().out == '{"op": "shutdown_ok"}\n'
