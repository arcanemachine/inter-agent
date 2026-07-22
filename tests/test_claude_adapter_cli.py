from __future__ import annotations

import json
from pathlib import Path

import pytest

import inter_agent.adapters.control as control
import inter_agent.core.channels as core_channels
import inter_agent.core.kick as core_kick
import inter_agent.core.list as core_list
import inter_agent.core.publish as core_publish
import inter_agent.core.send as core_send
import inter_agent.core.shutdown as core_shutdown
from inter_agent.adapters.claude import commands, state
from inter_agent.adapters.claude.cli import main
from inter_agent.core.channels import ChannelsResult
from inter_agent.core.kick import KickResult
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
        "scheme": "ws",
        "tls": False,
        "tls_source": "default",
        "tls_cert_path": None,
        "tls_cert_source": None,
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
        host: str,
        port: int,
        to: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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
        host: str,
        port: int,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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
        host: str,
        port: int,
        to: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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
        host: str,
        port: int,
        to: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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
        host: str,
        port: int,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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
        host: str,
        port: int,
        to: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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
        host: str,
        port: int,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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

    async def fake_list(host: str, port: int, **kwargs: object) -> ListResult:
        del kwargs
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
        host: str,
        port: int,
        to: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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
        host: str,
        port: int,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
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

    async def fake_shutdown(host: str, port: int, **kwargs: object) -> core_shutdown.ShutdownResult:
        del kwargs
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


def test_subscribe_invokes_control_bridge(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, str, int, str, str, str, str]] = []

    async def fake_request(
        adapter: str, host: str, port: int, name: str, base_dir: object, op: str, channel: str
    ) -> dict[str, object]:
        calls.append((adapter, host, port, name, str(base_dir), op, channel))
        return {"op": "subscribe_ok", "channel": channel}

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = main(["subscribe", "updates"])

    assert code == 0
    assert calls == [
        (
            "claude",
            "127.0.0.1",
            16837,
            "agent-a",
            str(state.claude_data_dir()),
            "subscribe",
            "updates",
        )
    ]
    assert json.loads(capsys.readouterr().out) == {"op": "subscribe_ok", "channel": "updates"}


def test_unsubscribe_invokes_control_bridge(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_request(
        adapter: str, host: str, port: int, name: str, base_dir: object, op: str, channel: str
    ) -> dict[str, object]:
        return {"op": "unsubscribe_ok", "channel": channel}

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = main(["unsubscribe", "updates"])

    assert code == 0
    assert json.loads(capsys.readouterr().out) == {"op": "unsubscribe_ok", "channel": "updates"}


def test_subscribe_protocol_error_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_request(
        adapter: str, host: str, port: int, name: str, base_dir: object, op: str, channel: str
    ) -> dict[str, object]:
        return {
            "op": "error",
            "code": "CHANNEL_LIMIT_REACHED",
            "message": " subscription limit reached",
        }

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = main(["subscribe", "updates"])

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "inter-agent-claude: (CHANNEL_LIMIT_REACHED):  subscription limit reached",
    ]


def test_subscribe_requires_connected_listener(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_request(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("control.request must not be called")

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: None)

    code = commands.subscribe("updates")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "not connected. Run '/inter-agent connect' first.\n"


def test_subscribe_missing_listener_reports_cleanly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_request(*args: object, **kwargs: object) -> dict[str, object]:
        raise control.ControlError("listener not reachable; reconnecting or not running")

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = commands.subscribe("updates")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert captured.err.startswith("inter-agent-claude: ")


def test_subscribe_invalid_channel_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_request(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("control.request must not be called")

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = commands.subscribe("Bad Channel!")

    assert code == 1
    captured = capsys.readouterr()
    assert "invalid channel name" in captured.err


def test_publish_uses_connected_name_and_delegates_to_core(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str, str | None]] = []

    async def fake_publish(
        host: str,
        port: int,
        channel: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
        calls.append((host, port, channel, text, from_name))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_publish, "publish_to_channel", fake_publish)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-connected")

    code = main(["publish", "updates", "hello"])

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "updates", "hello", "agent-connected")]
    # Claude publish success is silent.
    assert capsys.readouterr().out == ""


def test_publish_protocol_error_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_publish(
        host: str,
        port: int,
        channel: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
        return SendResult(
            welcome='{"op": "welcome"}',
            welcome_payload={"op": "welcome"},
            error=ProtocolErrorResult(
                code="UNKNOWN_CHANNEL",
                message="unknown channel",
                raw='{"op": "error", "code": "UNKNOWN_CHANNEL", "message": "unknown channel"}',
            ),
        )

    monkeypatch.setattr(core_publish, "publish_to_channel", fake_publish)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = commands.publish("updates", "hello")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "inter-agent-claude: publish failed (UNKNOWN_CHANNEL): unknown channel",
    ]


def test_publish_requires_connected_listener(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_publish(*args: object, **kwargs: object) -> SendResult:
        raise AssertionError("publish must not be called")

    monkeypatch.setattr(core_publish, "publish_to_channel", fake_publish)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: None)

    code = commands.publish("updates", "hello")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.err == "not connected. Run '/inter-agent connect' first.\n"


def test_publish_suppresses_duplicate_within_window(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[str] = []

    async def fake_publish(
        host: str,
        port: int,
        channel: str,
        text: str,
        from_name: str | None = None,
        **kwargs: object,
    ) -> SendResult:
        del kwargs
        calls.append(text)
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_publish, "publish_to_channel", fake_publish)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    assert commands.publish("updates", "hello") == 0
    assert commands.publish("updates", "hello") == 0
    assert calls == ["hello"]


def test_channels_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int]] = []

    async def fake_channels(host: str, port: int, **kwargs: object) -> ChannelsResult:
        del kwargs
        calls.append((host, port))
        return ChannelsResult(
            raw_response='{"op": "channels_ok", "channels": []}',
            response={"op": "channels_ok", "channels": []},
            channels=(),
        )

    monkeypatch.setattr(core_channels, "list_channels", fake_channels)

    code = commands.channels()

    assert code == 0
    assert calls == [("127.0.0.1", 16837)]
    assert json.loads(capsys.readouterr().out) == {"op": "channels_ok", "channels": []}


def test_subscribe_config_failure_is_adapter_prefixed_and_traceback_free(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """resolve_endpoint config failures stay adapter-prefixed and traceback-free."""
    monkeypatch.setenv("INTER_AGENT_PORT", "not-an-int")

    async def fake_request(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("control.request must not be called for a config failure")

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = main(["subscribe", "updates"])

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert captured.err.startswith("inter-agent-claude: ")
    assert "INTER_AGENT_PORT" in captured.err


def test_unsubscribe_config_failure_is_adapter_prefixed_and_traceback_free(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("INTER_AGENT_PORT", "not-an-int")

    async def fake_request(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("control.request must not be called for a config failure")

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    code = main(["unsubscribe", "updates"])

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert captured.err.startswith("inter-agent-claude: ")


def test_subscribe_data_dir_oserror_is_adapter_prefixed_and_traceback_free(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An OSError from the data-dir lookup is adapter-prefixed and clean."""

    async def fake_request(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("control.request must not be called for a data-dir failure")

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    def boom() -> Path:
        raise OSError("disk full")

    monkeypatch.setattr(state, "claude_data_dir", boom)

    code = main(["subscribe", "updates"])

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert captured.err.startswith("inter-agent-claude: ")
    assert "disk full" in captured.err


def test_unsubscribe_data_dir_oserror_is_adapter_prefixed_and_traceback_free(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_request(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("control.request must not be called for a data-dir failure")

    monkeypatch.setattr(control, "request", fake_request)
    monkeypatch.setattr(commands, "_connected_from_name", lambda: "agent-a")

    def boom() -> Path:
        raise OSError("disk full")

    monkeypatch.setattr(state, "claude_data_dir", boom)

    code = main(["unsubscribe", "updates"])

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert captured.err.startswith("inter-agent-claude: ")
    assert "disk full" in captured.err


def test_kick_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str | None, str | None]] = []

    async def fake_kick(
        host: str,
        port: int,
        *,
        name: str | None = None,
        session_id: str | None = None,
        **kwargs: object,
    ) -> KickResult:
        del kwargs
        calls.append((host, port, name, session_id))
        return KickResult(
            response='{"op": "kick_ok", "name": "agent-b", "session_id": "b"}',
            response_payload={"op": "kick_ok", "name": "agent-b", "session_id": "b"},
        )

    monkeypatch.setattr(core_kick, "kick_session", fake_kick)

    code = commands.kick("agent-b")

    assert code == 0
    assert calls == [("127.0.0.1", 16837, "agent-b", None)]
    assert json.loads(capsys.readouterr().out) == {
        "op": "kick_ok",
        "name": "agent-b",
        "session_id": "b",
    }


def test_kick_cli_dispatches_to_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_kick(
        host: str,
        port: int,
        *,
        name: str | None = None,
        session_id: str | None = None,
        **kwargs: object,
    ) -> KickResult:
        del kwargs
        return KickResult(
            response='{"op": "kick_ok", "name": "agent-b", "session_id": "b"}',
            response_payload={"op": "kick_ok", "name": "agent-b", "session_id": "b"},
        )

    monkeypatch.setattr(core_kick, "kick_session", fake_kick)

    assert main(["kick", "agent-b"]) == 0
    assert json.loads(capsys.readouterr().out)["op"] == "kick_ok"


def test_kick_protocol_error_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_kick(
        host: str,
        port: int,
        *,
        name: str | None = None,
        session_id: str | None = None,
        **kwargs: object,
    ) -> KickResult:
        del kwargs, name, session_id
        return KickResult(
            response='{"op": "error", "code": "UNKNOWN_TARGET", "message": "unknown target"}',
            response_payload={
                "op": "error",
                "code": "UNKNOWN_TARGET",
                "message": "unknown target",
            },
        )

    monkeypatch.setattr(core_kick, "kick_session", fake_kick)

    code = commands.kick("ghost")

    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "inter-agent-claude: (UNKNOWN_TARGET): unknown target",
    ]


def test_kick_does_not_require_connected_listener(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """kick uses a short-lived control connection and must not require this
    Claude Code session's active listener."""

    async def fake_kick(
        host: str,
        port: int,
        *,
        name: str | None = None,
        session_id: str | None = None,
        **kwargs: object,
    ) -> KickResult:
        del kwargs
        return KickResult(
            response='{"op": "kick_ok", "name": "x", "session_id": "x"}',
            response_payload={"op": "kick_ok", "name": "x", "session_id": "x"},
        )

    monkeypatch.setattr(core_kick, "kick_session", fake_kick)

    def fail_connected() -> str | None:
        raise AssertionError("kick must not require a connected listener")

    monkeypatch.setattr(commands, "_connected_from_name", fail_connected)
    monkeypatch.setattr(commands, "_require_connected_from_name", fail_connected)

    assert commands.kick("x") == 0
    assert json.loads(capsys.readouterr().out)["op"] == "kick_ok"
