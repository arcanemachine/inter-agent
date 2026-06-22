from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import websockets
from websockets.exceptions import WebSocketException

from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-status")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--json", action="store_true", help="emit JSON status output")
    return parser


def _status_payload(status: ServerStatus) -> dict[str, object]:
    return {
        "state": status.state,
        "host": status.host,
        "port": status.port,
        "identity_verified": status.identity_verified,
        "reachable": status.reachable,
        "message": status.message,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    status = asyncio.run(check_server_status(args.host, args.port))
    if args.json:
        print(json.dumps(_status_payload(status)))
    else:
        print(f"state={status.state}")
        print(f"host={status.host}")
        print(f"port={status.port}")
        print(f"reachable={status.reachable}")
        print(f"identity_verified={status.identity_verified}")
        print(f"message={status.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
