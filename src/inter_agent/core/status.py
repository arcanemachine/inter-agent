from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Literal

import websockets
from websockets.exceptions import WebSocketException

from inter_agent.core.shared import (
    control_hello,
    load_or_create_token,
    verify_server_identity_details,
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
    verification = verify_server_identity_details(host, port)
    if verification.ok:
        return None

    if verification.reason == "missing_metadata":
        return _status(
            "unavailable",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server identity not found",
        )
    if verification.reason == "process_not_running":
        return _status(
            "unavailable",
            host,
            port,
            identity_verified=False,
            reachable=False,
            message="server process is not running",
        )

    messages = {
        "invalid_metadata": "server identity metadata is invalid",
        "endpoint_mismatch": "server identity metadata does not match requested endpoint",
        "pid_metadata_mismatch": "server PID metadata does not match identity",
        "process_marker_mismatch": "server process marker does not match identity",
    }
    return _status(
        "identity_check_failed",
        host,
        port,
        identity_verified=False,
        reachable=False,
        message=messages.get(verification.reason, "server identity check failed"),
    )


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
