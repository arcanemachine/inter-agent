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
    identity_failure_message,
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

    state: StatusState = (
        "unavailable"
        if verification.reason in ("missing_metadata", "process_not_running")
        else "identity_check_failed"
    )
    return _status(
        state,
        host,
        port,
        identity_verified=False,
        reachable=False,
        message=identity_failure_message(verification.reason),
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
