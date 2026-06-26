"""Pi adapter wrappers around importable core command APIs.

Core supports `list`; adapter surfaces may choose whether to expose it.
"""

from __future__ import annotations

import asyncio
import json
import sys

from websockets.exceptions import WebSocketException

from inter_agent.adapters.pi import listener
from inter_agent.core import list as core_list
from inter_agent.core import send as core_send
from inter_agent.core import shutdown as core_shutdown
from inter_agent.core import status as core_status
from inter_agent.core.send import SendResult
from inter_agent.core.shared import resolve_endpoint


def _system_exit_code(exc: SystemExit) -> int:
    if isinstance(exc.code, int):
        return exc.code
    if exc.code is not None:
        print(exc.code, file=sys.stderr)
    return 1


def _expected_error_code(exc: Exception) -> int:
    print(f"inter-agent-pi: {exc}", file=sys.stderr)
    return 1


def _send_result_code(result: SendResult) -> int:
    if result.error is not None:
        print(
            f"inter-agent-pi: delivery failed ({result.error.code}): " f"{result.error.message}",
            file=sys.stderr,
        )
        return 1
    print(result.welcome)
    return 0


def connect(name: str, label: str | None = None) -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        return asyncio.run(listener.run_listener(endpoint.host, endpoint.port, name, label))
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)


def send(to: str, text: str, from_name: str | None = None) -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_send.send_direct_message(endpoint.host, endpoint.port, to, text, from_name)
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    return _send_result_code(result)


def broadcast(text: str, from_name: str | None = None) -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(
            core_send.broadcast_message(endpoint.host, endpoint.port, text, from_name)
        )
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    return _send_result_code(result)


def list_sessions() -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(core_list.list_sessions(endpoint.host, endpoint.port))
    except SystemExit as exc:
        return _system_exit_code(exc)
    except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
        return _expected_error_code(exc)
    print(result.raw_response)
    return 0


def shutdown() -> int:
    try:
        endpoint = resolve_endpoint(allow_discovery=True)
        result = asyncio.run(core_shutdown.shutdown_server(endpoint.host, endpoint.port))
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
    return {
        "state": server.state,
        "host": server.host,
        "port": server.port,
        "configured_host": server.configured_host,
        "configured_port": server.configured_port,
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
    }


def status_json() -> str:
    return json.dumps(status())
