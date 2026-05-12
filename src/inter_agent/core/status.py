from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from typing import Literal

import websockets
from websockets.exceptions import WebSocketException

from inter_agent.core.shared import (
    control_hello,
    identity_path,
    load_or_create_token,
)

StatusState = Literal[
    "available",
    "unavailable",
    "identity_check_failed",
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
    identity_verified: bool
    reachable: bool
    message: str


def command_status() -> CoreCommandStatus:
    """Return core command capabilities that do not require a live server."""
    return CoreCommandStatus(list_supported=True)


def _status(
    state: StatusState,
    host: str,
    port: int,
    *,
    identity_verified: bool,
    reachable: bool,
    message: str,
) -> ServerStatus:
    return ServerStatus(
        state=state,
        host=host,
        port=port,
        identity_verified=identity_verified,
        reachable=reachable,
        message=message,
    )


def _identity_failure(host: str, port: int) -> ServerStatus | None:
    path = identity_path(port)
    if not path.exists():
        return _status(
            "unavailable",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server identity not found",
        )

    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _status(
            "identity_check_failed",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server identity metadata is invalid",
        )

    if not isinstance(payload, dict):
        return _status(
            "identity_check_failed",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server identity metadata is invalid",
        )

    identity_host = payload.get("host")
    identity_port = payload.get("port")
    if identity_host != host or identity_port != port:
        return _status(
            "identity_check_failed",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server identity metadata does not match requested endpoint",
        )

    pid_value = payload.get("pid")
    try:
        if not isinstance(pid_value, (int, str)):
            raise ValueError
        pid = int(pid_value)
    except ValueError:
        return _status(
            "identity_check_failed",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server identity metadata is invalid",
        )

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return _status(
            "unavailable",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server process is not running",
        )
    except PermissionError:
        return _status(
            "identity_check_failed",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server identity process is not accessible",
        )

    return None


async def _probe_server(host: str, port: int, token: str) -> ServerStatus:
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(json.dumps(control_hello(token, f"status-{uuid.uuid4()}")))
        response: object = json.loads(await ws.recv())

    if not isinstance(response, dict):
        return _status(
            "protocol_mismatch",
            host,
            port,
            identity_verified=True,
            reachable=True,
            message="server returned an invalid status response",
        )

    op = response.get("op")
    if op == "welcome":
        return _status(
            "available",
            host,
            port,
            identity_verified=True,
            reachable=True,
            message="server available",
        )
    if op == "error" and response.get("code") == "AUTH_FAILED":
        return _status(
            "auth_failed",
            host,
            port,
            identity_verified=True,
            reachable=True,
            message="server authentication failed",
        )
    return _status(
        "protocol_mismatch",
        host,
        port,
        identity_verified=True,
        reachable=True,
        message="server returned an unexpected status response",
    )


async def check_server_status(host: str, port: int, timeout: float = 0.5) -> ServerStatus:
    """Check server identity metadata and probe the live WebSocket endpoint."""
    identity_failure = _identity_failure(host, port)
    if identity_failure is not None:
        return identity_failure

    try:
        return await asyncio.wait_for(
            _probe_server(host, port, load_or_create_token()),
            timeout=timeout,
        )
    except (OSError, TimeoutError, WebSocketException):
        return _status(
            "unavailable",
            host,
            port,
            identity_verified=True,
            reachable=False,
            message="server connection failed",
        )
