"""Claude adapter wrappers around importable core command APIs."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path

from websockets.exceptions import WebSocketException

from inter_agent.adapters import control
from inter_agent.adapters.claude import dedup, state
from inter_agent.core import channels as core_channels
from inter_agent.core import kick as core_kick
from inter_agent.core import list as core_list
from inter_agent.core import publish as core_publish
from inter_agent.core import send as core_send
from inter_agent.core import shutdown as core_shutdown
from inter_agent.core import status as core_status
from inter_agent.core.send import SendResult
from inter_agent.core.shared import Limits, resolve_endpoint, validate_channel_name


def _system_exit_code(exc: SystemExit) -> int:
    if isinstance(exc.code, int):
        return exc.code
    if exc.code is not None:
        print(exc.code, file=sys.stderr)
    return 1


def _expected_error_code(exc: Exception) -> int:
    print(f"inter-agent-claude: {exc}", file=sys.stderr)
    return 1


def _send_result_code(result: SendResult) -> int:
    if result.error is not None:
        print(
            f"inter-agent-claude: delivery failed ({result.error.code}): {result.error.message}",
            file=sys.stderr,
        )
        return 1
    return 0


def connect(name: str, label: str | None = None) -> int:
    """Connect is handled by the Monitor listener; this is a no-op for CLI use."""
    print("Use '/inter-agent connect' in Claude Code to start the listener.")
    return 0


def _connected_from_name() -> str | None:
    found_state, path = state.find_listener_state()
    if found_state is None or path is None:
        return None

    try:
        fd = state.acquire_lock(int(path.stem))
    except (OSError, ValueError):
        return None
    if fd is not None:
        state.release_lock(fd)
        state.unlink_if_matches(path, found_state)
        return None

    name = found_state.get("name")
    if not isinstance(name, str) or not name:
        return None
    return name


def _require_connected_from_name() -> str | None:
    from_name = _connected_from_name()
    if from_name is None:
        print("not connected. Run '/inter-agent connect' first.", file=sys.stderr)
        return None
    return from_name


def _control_response_code(response: dict[str, object], adapter_prefix: str) -> int:
    op = response.get("op")
    if op in ("subscribe_ok", "unsubscribe_ok"):
        print(json.dumps(response, ensure_ascii=False))
        return 0
    if op == "error":
        code = response.get("code", "PROTOCOL_ERROR")
        message = response.get("message", "protocol error")
        print(
            f"{adapter_prefix}: ({code}): {message}",
            file=sys.stderr,
        )
        return 1
    print(f"{adapter_prefix}: unexpected response: {response}", file=sys.stderr)
    return 1


def _validate_channel_or_error(channel: str, adapter_prefix: str) -> bool:
    if not validate_channel_name(channel, Limits().channel_name_max):
        print(f"{adapter_prefix}: invalid channel name: {channel!r}", file=sys.stderr)
        return False
    return True


def subscribe(channel: str) -> int:
    """Subscribe the current session's live listener to a channel."""
    if not _validate_channel_or_error(channel, "inter-agent-claude"):
        return 1
    connected_name = _require_connected_from_name()
    if connected_name is None:
        return 1
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        response = asyncio.run(
            control.request(
                "claude",
                endpoint.host,
                endpoint.port,
                connected_name,
                state.claude_data_dir(),
                "subscribe",
                channel,
            )
        )
    except (SystemExit, control.ControlError, OSError, TimeoutError, ValueError) as exc:
        print(f"inter-agent-claude: {exc}", file=sys.stderr)
        return 1
    return _control_response_code(response, "inter-agent-claude")


def unsubscribe(channel: str) -> int:
    """Unsubscribe the current session's live listener from a channel."""
    if not _validate_channel_or_error(channel, "inter-agent-claude"):
        return 1
    connected_name = _require_connected_from_name()
    if connected_name is None:
        return 1
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        response = asyncio.run(
            control.request(
                "claude",
                endpoint.host,
                endpoint.port,
                connected_name,
                state.claude_data_dir(),
                "unsubscribe",
                channel,
            )
        )
    except (SystemExit, control.ControlError, OSError, TimeoutError, ValueError) as exc:
        print(f"inter-agent-claude: {exc}", file=sys.stderr)
        return 1
    return _control_response_code(response, "inter-agent-claude")


def _publish_send_result_code(result: SendResult) -> int:
    # Claude publish success is silent (no welcome envelope printed).
    if result.error is not None:
        print(
            f"inter-agent-claude: publish failed ({result.error.code}): {result.error.message}",
            file=sys.stderr,
        )
        return 1
    return 0


def publish(channel: str, text: str, from_name: str | None = None) -> int:
    del from_name
    if not _validate_channel_or_error(channel, "inter-agent-claude"):
        return 1
    connected_name = _require_connected_from_name()
    if connected_name is None:
        return 1
    if dedup.is_duplicate_publish(connected_name, channel, text):
        return 0
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_publish.publish_to_channel(
                endpoint.host,
                endpoint.port,
                channel,
                text,
                connected_name,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    return _publish_send_result_code(result)


def channels(as_json: bool = True) -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_channels.list_channels(
                endpoint.host,
                endpoint.port,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    print(result.raw_response)
    return 0 if result.response.get("op") == "channels_ok" else 1


def send(to: str, text: str, from_name: str | None = None) -> int:
    del from_name
    connected_name = _require_connected_from_name()
    if connected_name is None:
        return 1
    if dedup.is_duplicate_send(connected_name, to, text):
        return 0
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_send.send_direct_message(
                endpoint.host,
                endpoint.port,
                to,
                text,
                connected_name,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    return _send_result_code(result)


def broadcast(text: str, from_name: str | None = None) -> int:
    del from_name
    connected_name = _require_connected_from_name()
    if connected_name is None:
        return 1
    if dedup.is_duplicate_send(connected_name, text):
        return 0
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_send.broadcast_message(
                endpoint.host,
                endpoint.port,
                text,
                connected_name,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    return _send_result_code(result)


def list_sessions() -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_list.list_sessions(
                endpoint.host,
                endpoint.port,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    print(result.raw_response)
    return 0


def message(msg_id: str, as_json: bool = False) -> int:
    """Look up a stored inbound message by msg_id and print its full text.

    Truncated inbound messages are written to the adapter messages log by the
    listener. This command reads the full text back by msg_id so the agent does
    not have to grep/tail the log file itself.
    """
    record = state.read_message_by_id(msg_id)
    if record is None:
        print(f"no message found for msg_id={msg_id!r}", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps(record, ensure_ascii=False))
    else:
        text = record.get("text")
        if not isinstance(text, str):
            print(f"message {msg_id!r} has no text field", file=sys.stderr)
            return 1
        print(text)
    return 0


def kick(name: str) -> int:
    """Force-disconnect a named agent role session via a control connection.

    User-only: the installed skill invokes this only on an explicit user
    request. It does not require this Claude Code session's active listener.
    """
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_kick.kick_session(
                endpoint.host,
                endpoint.port,
                name=name,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    if result.response_payload.get("op") == "kick_ok":
        print(result.response)
        return 0
    code = result.response_payload.get("code", "PROTOCOL_ERROR")
    message = result.response_payload.get("message", "kick failed")
    print(f"inter-agent-claude: ({code}): {message}", file=sys.stderr)
    return 1


def shutdown() -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_shutdown.shutdown_server(
                endpoint.host,
                endpoint.port,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    print(result.response)
    return 0 if result.response_payload.get("op") == "shutdown_ok" else 1


def status() -> dict[str, object]:
    command = core_status.command_status()
    endpoint = resolve_endpoint(allow_discovery=True)
    server = asyncio.run(core_status.check_resolved_server_status(endpoint))
    connected_name = _connected_from_name()
    return {
        "state": server.state,
        "host": server.host,
        "port": server.port,
        "configured_host": server.configured_host,
        "configured_port": server.configured_port,
        "scheme": server.scheme,
        "tls": server.tls,
        "tls_source": server.tls_source,
        "tls_cert_path": server.tls_cert_path,
        "tls_cert_source": server.tls_cert_source,
        "host_source": server.host_source,
        "port_source": server.port_source,
        "data_dir": server.data_dir,
        "data_dir_source": server.data_dir_source,
        "config_path": server.config_path,
        "hints": list(server.hints),
        "server_reachable": server.reachable,
        "message": server.message,
        "core_list_supported": command.list_supported,
        "adapter_list_exposed": True,
        "connected": connected_name is not None,
        "connected_name": connected_name,
    }


def status_json() -> str:
    return json.dumps(status())


def _stop_listener(found_state: dict[str, object], path: Path | None) -> int:
    listener_pid = found_state.get("listener_pid")
    if listener_pid and isinstance(listener_pid, int):
        try:
            os.kill(listener_pid, signal.SIGTERM)
            print(f"stopped listener pid {listener_pid}")
            return 0
        except (OSError, ProcessLookupError):
            pass

    if path is not None:
        state.unlink_if_matches(path, found_state)
    print("not connected (stale state cleaned up)", file=sys.stderr)
    return 1


def disconnect() -> int:
    """Stop the running listener for this Claude Code session."""
    found_state, path = state.find_listener_state()
    if found_state is not None:
        return _stop_listener(found_state, path)

    # Scan for orphaned listeners from other parent PIDs.
    for session_file in state.claude_data_dir().glob("*.session"):
        sess = state.read_session_state(int(session_file.stem))
        if sess is None:
            continue
        fd = state.acquire_lock(int(session_file.stem))
        if fd is None:
            return _stop_listener(sess, session_file)
        state.release_lock(fd)
        if state.unlink_if_matches(session_file, sess):
            print("not connected (stale state cleaned up)", file=sys.stderr)
            return 1

    print("not connected", file=sys.stderr)
    return 1
