from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

import websockets
from websockets.exceptions import WebSocketException

from inter_agent.core.auth import AuthError, AuthProtocolError, client_handshake
from inter_agent.core.config import EndpointResolution
from inter_agent.core.shared import control_hello, resolve_endpoint, resolve_shared_secret

StatusState = Literal[
    "available",
    "unavailable",
    "auth_failed",
    "protocol_mismatch",
]


@dataclass(frozen=True)
class CoreCommandStatus:
    """Static command capabilities exposed to host adapters."""

    list_supported: bool


@dataclass(frozen=True)
class ServerStatus:
    """Live server status for command adapters."""

    state: StatusState
    host: str
    port: int
    reachable: bool
    message: str
    configured_host: str | None = None
    configured_port: int | None = None
    host_source: str | None = None
    port_source: str | None = None
    data_dir: str | None = None
    data_dir_source: str | None = None
    config_path: str | None = None
    hints: tuple[str, ...] = ()


def command_status() -> CoreCommandStatus:
    """Return core command capabilities that do not require a live server."""
    return CoreCommandStatus(list_supported=True)


def _status(
    state: StatusState,
    host: str,
    port: int,
    *,
    reachable: bool,
    message: str,
) -> ServerStatus:
    return ServerStatus(
        state=state,
        host=host,
        port=port,
        reachable=reachable,
        message=message,
    )


def _json_object(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server response must be a JSON object")
    return {str(key): value for key, value in payload.items()}


async def _probe_server(host: str, port: int, secret: str) -> ServerStatus:
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        response_raw = await client_handshake(ws, secret, control_hello(f"status-{uuid.uuid4()}"))

    response = _json_object(response_raw)
    op = response.get("op")
    if op == "welcome":
        return _status(
            "available",
            host,
            port,
            reachable=True,
            message="server available",
        )
    if op == "error" and response.get("code") == "AUTH_FAILED":
        return _status(
            "auth_failed",
            host,
            port,
            reachable=True,
            message="server authentication failed",
        )
    return _status(
        "protocol_mismatch",
        host,
        port,
        reachable=True,
        message="server returned an unexpected status response",
    )


async def check_server_status(host: str, port: int, timeout: float = 0.5) -> ServerStatus:
    """Probe the live WebSocket endpoint with the resolved shared secret."""
    try:
        secret = resolve_shared_secret().secret
        return await asyncio.wait_for(_probe_server(host, port, secret), timeout=timeout)
    except AuthError:
        return _status(
            "auth_failed",
            host,
            port,
            reachable=True,
            message="server authentication failed",
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, AuthProtocolError):
        return _status(
            "protocol_mismatch",
            host,
            port,
            reachable=True,
            message="server returned an invalid status response",
        )
    except (OSError, TimeoutError, WebSocketException):
        return _status(
            "unavailable",
            host,
            port,
            reachable=False,
            message="server connection failed",
        )


def _hints(status: ServerStatus) -> tuple[str, ...]:
    if status.state == "unavailable":
        return ("start inter-agent-server or check INTER_AGENT_HOST and INTER_AGENT_PORT",)
    return ()


async def check_resolved_server_status(
    resolution: EndpointResolution, timeout: float = 0.5
) -> ServerStatus:
    """Check status and attach endpoint/config diagnostics."""
    status = await check_server_status(resolution.host, resolution.port, timeout=timeout)
    status = replace(
        status,
        configured_host=resolution.configured_host,
        configured_port=resolution.configured_port,
        host_source=resolution.host_source,
        port_source=resolution.port_source,
        data_dir=str(resolution.data_dir),
        data_dir_source=resolution.data_dir_source,
        config_path=str(resolution.config_path) if resolution.config_path is not None else None,
    )
    return replace(status, hints=_hints(status))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-status")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--json", action="store_true", help="emit JSON status output")
    return parser


def _status_payload(status: ServerStatus) -> dict[str, object]:
    return {
        "state": status.state,
        "host": status.host,
        "port": status.port,
        "configured_host": status.configured_host,
        "configured_port": status.configured_port,
        "host_source": status.host_source,
        "port_source": status.port_source,
        "data_dir": status.data_dir,
        "data_dir_source": status.data_dir_source,
        "config_path": status.config_path,
        "hints": list(status.hints),
        "reachable": status.reachable,
        "message": status.message,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    endpoint = resolve_endpoint(args.host, args.port, allow_discovery=True)
    status = asyncio.run(check_resolved_server_status(endpoint))
    if args.json:
        print(json.dumps(_status_payload(status)))
    else:
        print(f"state={status.state}")
        print(f"host={status.host}")
        print(f"port={status.port}")
        print(f"reachable={status.reachable}")
        print(f"configured_host={status.configured_host}")
        print(f"configured_port={status.configured_port}")
        print(f"host_source={status.host_source}")
        print(f"port_source={status.port_source}")
        print(f"data_dir={status.data_dir}")
        print(f"data_dir_source={status.data_dir_source}")
        print(f"config_path={status.config_path or ''}")
        print(f"message={status.message}")
        for hint in status.hints:
            print(f"hint={hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
