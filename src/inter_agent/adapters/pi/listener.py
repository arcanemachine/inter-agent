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
import subprocess
import sys
from collections.abc import Sequence
from typing import TextIO

import websockets

from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    load_or_create_token,
    verify_server_identity,
)

RECONNECT_BACKOFF_MIN_S = 0.25
RECONNECT_BACKOFF_MAX_S = 4.0
RECONNECT_JITTER_FRAC = 0.2
RECONNECT_MAX_ATTEMPTS = 20
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


def _print_frame(payload: str, output: TextIO) -> None:
    """Emit a single JSON frame to stdout, flushed."""
    output.write(payload + "\n")
    output.flush()


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _start_server() -> subprocess.Popen[bytes] | None:
    """Start inter-agent-server as a child process with an explicit idle timeout."""
    try:
        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "inter_agent.core.server",
                "--idle-timeout",
                str(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S),
            ],
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
) -> None:
    """Connect once, print frames, and return when the connection closes.

    Raises PermanentError if the server rejects the connection with a
    permanent error code.
    """
    token = load_or_create_token()
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        hello: dict[str, object] = {
            "op": "hello",
            "token": token,
            "role": "agent",
            "session_id": os.getenv("INTER_AGENT_SESSION_ID", name),
            "name": name,
            "capabilities": {},
        }
        if label is not None:
            hello["label"] = label
        await ws.send(json.dumps(hello))

        first = True
        async for raw in ws:
            text = _text_frame(raw)
            _print_frame(text, output)

            if first:
                first = False
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if payload.get("op") == "error":
                    code = payload.get("code", "")
                    if isinstance(code, str) and code in _PERMANENT_ERROR_CODES:
                        raise PermanentError(f"{code}: {payload.get('message', '')}")
                    return  # non-permanent error; let caller reconnect


async def run_listener(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    name: str = "",
    label: str | None = None,
    output: TextIO | None = None,
    max_attempts: int = RECONNECT_MAX_ATTEMPTS,
) -> int:
    """Run the listener with automatic reconnection and eventual give-up.

    Returns 0 on clean shutdown, 1 on permanent error or give-up.
    """
    stream = output or sys.stdout
    backoff = RECONNECT_BACKOFF_MIN_S
    attempts = 0
    server_started = False

    while attempts < max_attempts:
        # Ensure the server is running, auto-starting if needed.
        if not verify_server_identity(host, port):
            if not server_started:
                proc = _start_server()
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
                if verify_server_identity(host, port):
                    ready = True
                    break
                await asyncio.sleep(0.5)
            if not ready:
                attempts += 1
                if attempts >= max_attempts:
                    print(
                        "[inter-agent] server did not become available; giving up",
                        file=sys.stderr,
                    )
                    return 1
                await _backoff_sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX_S)
                continue

        try:
            await _connect_and_stream(host, port, name, label, stream)
            # Connection closed normally — reset backoff and reconnect.
            backoff = RECONNECT_BACKOFF_MIN_S
            attempts = 0
        except PermanentError:
            return 1
        except (ConnectionRefusedError, OSError, websockets.ConnectionClosed):
            pass

        attempts += 1
        if attempts >= max_attempts:
            print(
                f"[inter-agent] giving up after {attempts} reconnect attempts",
                file=sys.stderr,
            )
            return 1

        await _backoff_sleep(backoff)
        backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX_S)

    return 1


async def _backoff_sleep(backoff: float) -> None:
    jitter = backoff * RECONNECT_JITTER_FRAC
    delay = backoff + random.uniform(-jitter, jitter)
    await asyncio.sleep(max(0.0, delay))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-pi connect")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--name", dest="name_option")
    parser.add_argument("--label")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    name = args.name_option or args.name
    if not name:
        parser.error("name is required")
    return asyncio.run(run_listener(args.host, args.port, name, args.label))


if __name__ == "__main__":
    raise SystemExit(main())
