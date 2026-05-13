"""Long-running Monitor listener for Claude Code sessions."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import secrets
import signal
import sys
import uuid
from pathlib import Path
from typing import TextIO

import websockets

from inter_agent.adapters.claude import formatting, state
from inter_agent.core.client import iter_client_frames
from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    load_or_create_token,
    verify_server_identity,
)

RECONNECT_BACKOFF_MIN_S = 0.25
RECONNECT_BACKOFF_MAX_S = 4.0
RECONNECT_JITTER_FRAC = 0.2
PING_INTERVAL_S = 15

log = logging.getLogger("inter-agent.claude.listener")


def _print_line(line: str, out: TextIO) -> None:
    """Emit a single notification line to stdout, flushed."""
    out.write(line + "\n")
    out.flush()


def _auto_name_from_cwd() -> str:
    """Derive a routing name from the current working directory."""
    basename = Path.cwd().name
    name = "".join(c for c in basename.lower() if c.isalnum() or c == "-")
    name = name.strip("-")
    if not name:
        return "claude"
    return name[:40]


class Listener:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        name: str = "",
        label: str | None = None,
        session_id: str | None = None,
        output: TextIO | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.label = label
        self.session_id = session_id or str(uuid.uuid4())
        self.nonce = secrets.token_urlsafe(16)
        self.output = output or sys.stdout
        self._stop = asyncio.Event()
        self._lock_fd: int | None = None
        self._connect_task: asyncio.Task[None] | None = None

    def stop(self) -> None:
        self._stop.set()
        t = self._connect_task
        if t is not None and not t.done():
            t.cancel()

    async def run(self) -> int:
        ppid = state._resolve_listener_key()
        self._lock_fd = state.acquire_lock(ppid)
        if self._lock_fd is None:
            existing = state.read_session_state(ppid)
            if existing:
                _print_line(
                    "[inter-agent] another monitor for this session is already running "
                    f"— name={existing.get('name', '')!r}, "
                    f"listener_pid={existing.get('listener_pid', '')}, "
                    f"session_id={existing.get('session_id', '')}; exiting",
                    self.output,
                )
            else:
                _print_line(
                    "[inter-agent] another monitor for this session is already running — exiting",
                    self.output,
                )
            return 0

        try:
            backoff = RECONNECT_BACKOFF_MIN_S
            while not self._stop.is_set():
                if not verify_server_identity(self.host, self.port):
                    _print_line(
                        "[inter-agent] server identity check failed; " "refusing to connect",
                        self.output,
                    )
                    self._stop.set()
                    break

                self._connect_task = asyncio.create_task(self._connect_and_serve(ppid))
                try:
                    await self._connect_task
                    backoff = RECONNECT_BACKOFF_MIN_S
                except asyncio.CancelledError:
                    pass
                except (ConnectionRefusedError, OSError) as exc:
                    log.info("connect failed: %s", exc)
                except websockets.InvalidHandshake as exc:
                    _print_line(
                        f"[inter-agent] connected to a non-inter-agent service: {exc}",
                        self.output,
                    )
                    return 1
                except websockets.ConnectionClosed:
                    pass
                finally:
                    self._connect_task = None

                if self._stop.is_set():
                    break

                jitter = backoff * RECONNECT_JITTER_FRAC
                delay = backoff + random.uniform(-jitter, jitter)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except TimeoutError:
                    pass
                backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX_S)

            return 0
        finally:
            state.delete_session_state(ppid)
            if self._lock_fd is not None:
                state.release_lock(self._lock_fd)

    async def _connect_and_serve(self, ppid: int) -> None:
        token = load_or_create_token()
        async for raw in iter_client_frames(self.host, self.port, self.name, self.label):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            op = payload.get("op")
            if op == "welcome":
                state.write_session_state(
                    ppid,
                    {
                        "session_id": self.session_id,
                        "name": self.name,
                        "label": self.label,
                        "token": token,
                        "nonce": self.nonce,
                        "listener_pid": os.getpid(),
                        "host": self.host,
                        "port": self.port,
                    },
                )
                continue

            if op == "error":
                code = payload.get("code", "")
                message = payload.get("message", "")
                _print_line(
                    f"[inter-agent] connection error: {code}: {message}",
                    self.output,
                )
                continue

            if op == "msg":
                msg_id = payload.get("msg_id", "")
                from_name = payload.get("from_name") or payload.get("from", "unknown")
                text = payload.get("text", "")
                to = payload.get("to")
                if not isinstance(text, str):
                    continue

                line = formatting.format_notification(
                    str(msg_id), str(from_name), text, str(to) if to else None
                )
                _print_line(line, self.output)

                # Write continuation pointer for truncated messages
                if "truncated=" in line:
                    sanitized = formatting.sanitize_for_stdout(text)
                    _, _, full_len = formatting.truncate_for_stdout(sanitized)
                    log_path = state.messages_log_path()
                    _write_to_messages_log(msg_id, from_name, text, log_path)
                    _print_line(
                        formatting.format_truncation_pointer(str(msg_id), full_len, log_path),
                        self.output,
                    )
                continue

            if op == "pong":
                continue

            if log.isEnabledFor(logging.DEBUG):
                log.debug("unhandled op: %s", op)


def _write_to_messages_log(msg_id: str, from_name: str, text: str, log_path: Path) -> None:
    """Append the full message to the messages log for continuation lookup."""
    try:
        record = json.dumps(
            {"msg_id": msg_id, "from_name": from_name, "text": text},
            ensure_ascii=False,
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(record + "\n")
    except OSError:
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-claude listen")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--name", default="")
    parser.add_argument("--label")
    parser.add_argument("--session-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    name = args.name
    if not name:
        name = _auto_name_from_cwd()
        _print_line(
            f"[inter-agent] no --name given; auto-named {name!r} from cwd",
            sys.stdout,
        )

    listener = Listener(
        host=args.host,
        port=args.port,
        name=name,
        label=args.label,
        session_id=args.session_id,
    )

    loop = asyncio.new_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, listener.stop)
        except NotImplementedError:
            pass
    try:
        return loop.run_until_complete(listener.run())
    finally:
        loop.close()


if __name__ == "__main__":
    raise SystemExit(main())
