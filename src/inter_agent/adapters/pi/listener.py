"""Long-running Pi listener with automatic reconnection.

The Pi extension spawns this listener as a child process. It connects to the
inter-agent bus as an agent session, prints server frames to stdout (one JSON
object per line), and reconnects with bounded backoff when the connection
drops. The server is auto-started if it is not running.

The extension reads stdout frames: ``welcome`` marks the listener ready,
``msg`` frames are delivered as notifications, and ``error`` frames indicate
permanent connection rejections.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import socket
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import TextIO, cast

import websockets

from inter_agent.core.auth import client_handshake
from inter_agent.core.client import build_hello
from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    resolve_endpoint,
    resolve_shared_secret,
)
from inter_agent.core.transport import client_ssl_context, websocket_uri

RECONNECT_BACKOFF_MIN_S = 0.5
RECONNECT_BACKOFF_MAX_S = 4.0
RECONNECT_JITTER_FRAC = 0.2
RECONNECT_DEADLINE_S = 60.0
AUTO_STARTED_SERVER_IDLE_TIMEOUT_S = 300

# Server error codes that won't resolve by reconnecting.
_PERMANENT_ERROR_CODES = frozenset(
    {
        "AUTH_FAILED",
        "BAD_LABEL",
        "BAD_NAME",
        "BAD_ROLE",
        "BAD_SESSION",
        "NAME_TAKEN",
        "SESSION_TAKEN",
        "TOO_MANY_CONNECTIONS",
    }
)

log = logging.getLogger("inter-agent.pi.listener")


class PermanentError(Exception):
    """Raised when the server returns an error that reconnecting cannot resolve."""


def endpoint_available(host: str, port: int) -> bool:
    """Return True when the configured TCP endpoint accepts connections."""
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def _print_frame(payload: str, output: TextIO) -> None:
    """Emit a single JSON frame to stdout, flushed."""
    output.write(payload + "\n")
    output.flush()


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _start_server(
    host: str,
    port: int,
    *,
    tls: bool = False,
    tls_cert_path: str | None = None,
    tls_key_path: str | None = None,
) -> subprocess.Popen[bytes] | None:
    """Start inter-agent-server as a child process with an explicit idle timeout."""
    try:
        args = [
            sys.executable,
            "-m",
            "inter_agent.core.server",
            "--host",
            host,
            "--port",
            str(port),
            "--idle-timeout",
            str(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S),
        ]
        if tls:
            args.append("--tls")
        else:
            args.append("--no-tls")
        if tls_cert_path:
            args.extend(["--tls-cert", tls_cert_path])
        if tls_key_path:
            args.extend(["--tls-key", tls_key_path])
        return subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None


async def _connect_and_stream(
    host: str,
    port: int,
    name: str,
    label: str | None,
    output: TextIO,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> None:
    """Connect once, print frames, and return when the connection closes.

    Raises PermanentError if the server rejects the connection with a
    permanent error code.
    """

    async def handle_first_frame(text: str) -> bool:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        if payload.get("op") == "error":
            code = payload.get("code", "")
            if isinstance(code, str) and code in _PERMANENT_ERROR_CODES:
                raise PermanentError(f"{code}: {payload.get('message', '')}")
            return True
        return False

    ssl_context = client_ssl_context(tls, data_dir, tls_cert_path)
    uri = websocket_uri(host, port, tls)
    connection = (
        websockets.connect(uri, ssl=ssl_context) if ssl_context else websockets.connect(uri)
    )
    async with connection as ws:
        hello = build_hello(os.getenv("INTER_AGENT_SESSION_ID", str(uuid.uuid4())), name, label)
        if hasattr(ws, "recv"):
            text = await client_handshake(ws, resolve_shared_secret().secret, hello)
        else:
            await ws.send(json.dumps(hello))
            iterator = cast(AsyncIterator[str], ws)
            text = await anext(iterator)
        _print_frame(text, output)
        if await handle_first_frame(text):
            return
        async for raw in ws:
            text = _text_frame(raw)
            _print_frame(text, output)


def _jittered_delay(backoff: float) -> float:
    jitter = backoff * RECONNECT_JITTER_FRAC
    return max(0.0, backoff + random.uniform(-jitter, jitter))


async def run_listener(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    name: str = "",
    label: str | None = None,
    output: TextIO | None = None,
    deadline_s: float = RECONNECT_DEADLINE_S,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
    tls_key_path: Path | None = None,
) -> int:
    """Run the listener with automatic reconnection and eventual give-up.

    Reconnects with bounded backoff while the connection is down. Gives up if
    a reconnection would land at or past ``deadline_s`` seconds from the first
    failure. Each successful connection resets the deadline, so a flapping
    server that connects intermittently does not give up.

    Returns 0 on clean shutdown, 1 on permanent error or give-up.
    """
    stream = output or sys.stdout
    backoff = RECONNECT_BACKOFF_MIN_S
    deadline: float | None = None
    server_started = False

    while True:
        # Ensure the server is running, auto-starting if needed.
        if not endpoint_available(host, port):
            if not server_started:
                proc = _start_server(
                    host,
                    port,
                    tls=tls,
                    tls_cert_path=str(tls_cert_path) if tls_cert_path is not None else None,
                    tls_key_path=str(tls_key_path) if tls_key_path is not None else None,
                )
                if proc is None:
                    print(
                        "[inter-agent] failed to auto-start server; giving up",
                        file=sys.stderr,
                    )
                    return 1
                server_started = True
                log.info("auto-started server pid %s", proc.pid)
            # Wait for the server to come up.
            ready = False
            for _ in range(30):
                if endpoint_available(host, port):
                    ready = True
                    break
                await asyncio.sleep(0.5)
            if not ready:
                if deadline is None:
                    deadline = asyncio.get_running_loop().time() + deadline_s
                if asyncio.get_running_loop().time() >= deadline:
                    print(
                        "[inter-agent] server did not become available; giving up",
                        file=sys.stderr,
                    )
                    return 1
                await asyncio.sleep(_jittered_delay(backoff))
                backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX_S)
                continue

        try:
            await _connect_and_stream(
                host,
                port,
                name,
                label,
                stream,
                tls=tls,
                data_dir=data_dir,
                tls_cert_path=tls_cert_path,
            )
            # Connection closed normally — reset and reconnect.
            backoff = RECONNECT_BACKOFF_MIN_S
            deadline = None
        except PermanentError:
            return 1
        except (ConnectionRefusedError, OSError, websockets.ConnectionClosed):
            pass

        if deadline is None:
            deadline = asyncio.get_running_loop().time() + deadline_s
        if asyncio.get_running_loop().time() >= deadline:
            print(
                "[inter-agent] giving up; could not reconnect within " f"{deadline_s:.0f}s",
                file=sys.stderr,
            )
            return 1

        await asyncio.sleep(_jittered_delay(backoff))
        backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX_S)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-pi connect")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--name", dest="name_option")
    parser.add_argument("--label")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--tls", dest="tls", action="store_true", default=None)
    parser.add_argument("--no-tls", dest="tls", action="store_false")
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    name = args.name_option or args.name
    if not name:
        parser.error("name is required")
    endpoint = resolve_endpoint(
        args.host,
        args.port,
        allow_discovery=True,
        tls=args.tls,
        tls_cert_path=args.tls_cert,
        tls_key_path=args.tls_key,
    )
    return asyncio.run(
        run_listener(
            endpoint.host,
            endpoint.port,
            name,
            args.label,
            tls=endpoint.tls,
            data_dir=endpoint.data_dir,
            tls_cert_path=endpoint.tls_cert_path,
            tls_key_path=endpoint.tls_key_path,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
