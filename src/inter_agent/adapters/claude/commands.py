"""Claude adapter wrappers around importable core command APIs."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys

from websockets.exceptions import WebSocketException

from inter_agent.adapters.claude import state
from inter_agent.core import list as core_list
from inter_agent.core import send as core_send
from inter_agent.core import shutdown as core_shutdown
from inter_agent.core import status as core_status
from inter_agent.core.send import SendResult
from inter_agent.core.shared import DEFAULT_HOST, DEFAULT_PORT


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
    print(result.welcome)
    if result.error is not None:
        print(result.error.raw)
        return 1
    return 0


def connect(name: str, label: str | None = None) -> int:
    """Connect is handled by the Monitor listener; this is a no-op for CLI use."""
    print("Use '/inter-agent connect' in Claude Code to start the listener.")
    return 0


def send(to: str, text: str) -> int:
    try:
        result = asyncio.run(core_send.send_direct_message(DEFAULT_HOST, DEFAULT_PORT, to, text))
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    return _send_result_code(result)


def broadcast(text: str) -> int:
    try:
        result = asyncio.run(core_send.broadcast_message(DEFAULT_HOST, DEFAULT_PORT, text))
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    return _send_result_code(result)


def list_sessions() -> int:
    try:
        result = asyncio.run(core_list.list_sessions(DEFAULT_HOST, DEFAULT_PORT))
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    print(result.raw_response)
    return 0


def shutdown() -> int:
    try:
        result = asyncio.run(core_shutdown.shutdown_server(DEFAULT_HOST, DEFAULT_PORT))
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    print(result.response)
    return 0 if result.response_payload.get("op") == "shutdown_ok" else 1


def status() -> dict[str, object]:
    command = core_status.command_status()
    server = asyncio.run(core_status.check_server_status(DEFAULT_HOST, DEFAULT_PORT))
    return {
        "state": server.state,
        "host": server.host,
        "port": server.port,
        "server_reachable": server.reachable,
        "identity_verified": server.identity_verified,
        "message": server.message,
        "core_list_supported": command.list_supported,
        "adapter_list_exposed": True,
    }


def status_json() -> str:
    return json.dumps(status())


def disconnect() -> int:
    """Stop the running listener for this Claude Code session."""
    found_state, path = state.find_listener_state()
    if found_state is None:
        print("not connected", file=sys.stderr)
        return 1

    listener_pid = found_state.get("listener_pid")
    if listener_pid and isinstance(listener_pid, int):
        try:
            os.kill(listener_pid, signal.SIGTERM)
            print(f"stopped listener pid {listener_pid}")
            return 0
        except (OSError, ProcessLookupError):
            pass

    # Stale state — clean it up
    if path is not None:
        state.unlink_if_matches(path, found_state)
    print("not connected (stale state cleaned up)", file=sys.stderr)
    return 1
