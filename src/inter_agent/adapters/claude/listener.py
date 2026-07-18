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
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import TextIO

import websockets

from inter_agent.adapters import control
from inter_agent.adapters.claude import formatting, state
from inter_agent.core.client import AgentSession
from inter_agent.core.shared import DEFAULT_HOST, DEFAULT_PORT, resolve_endpoint

RECONNECT_BACKOFF_MIN_S = 0.5
RECONNECT_BACKOFF_MAX_S = 4.0
RECONNECT_JITTER_FRAC = 0.2
RECONNECT_DEADLINE_S = 60.0
PING_INTERVAL_S = 15
AUTO_STARTED_SERVER_IDLE_TIMEOUT_S = 300
RECEIVE_DEDUP_WINDOW_S = 60.0
MAX_NAME_LEN = 40
NAME_TAKEN_RETRY_SUFFIX = "-2"

# Server error codes that won't resolve by reconnecting with the same name.
# NAME_TAKEN gets one adapter-level retry under a suffixed name in run().
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

log = logging.getLogger("inter-agent.claude.listener")


def endpoint_available(host: str, port: int) -> bool:
    """Return True when the configured TCP endpoint accepts connections."""
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


class PermanentError(Exception):
    """Raised when the server returns an error that reconnecting cannot resolve."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


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
    return name[:MAX_NAME_LEN]


def _retry_name(name: str) -> str:
    """Return a single NAME_TAKEN retry name with a valid max length."""
    base_len = MAX_NAME_LEN - len(NAME_TAKEN_RETRY_SUFFIX)
    base = name[:base_len].rstrip("-") or "claude"
    return f"{base}{NAME_TAKEN_RETRY_SUFFIX}"


class Listener:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        name: str = "",
        label: str | None = None,
        session_id: str | None = None,
        output: TextIO | None = None,
        tls: bool = False,
        data_dir: Path | None = None,
        tls_cert_path: Path | None = None,
        tls_key_path: Path | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.tls = tls
        self.data_dir = data_dir
        self.tls_cert_path = tls_cert_path
        self.tls_key_path = tls_key_path
        self.name = name
        self.label = label
        self.session_id = session_id or str(uuid.uuid4())
        self.nonce = secrets.token_urlsafe(16)
        self.output = output or sys.stdout
        self._stop = asyncio.Event()
        self._lock_fd: int | None = None
        self._connect_task: asyncio.Task[None] | None = None
        self._server_proc: subprocess.Popen[bytes] | None = None
        self._recent_msg_ids: dict[str, float] = {}
        self._session: AgentSession | None = None
        self._desired_channels: set[str] = set()
        self._control_server: control.ControlServer | None = None

    def stop(self) -> None:
        self._stop.set()
        t = self._connect_task
        if t is not None and not t.done():
            t.cancel()
        # Do not kill self._server_proc here — the auto-started server's
        # idle timeout handles shutdown when no connections remain.

    def _start_server(self) -> subprocess.Popen[bytes] | None:
        """Start inter-agent-server as a child process.

        The auto-started server receives an explicit idle timeout and
        shuts itself down once all connections are gone. The listener
        never sends this process a signal — it owns its own lifecycle.
        """
        try:
            args = [
                sys.executable,
                "-m",
                "inter_agent.core.server",
                "--host",
                self.host,
                "--port",
                str(self.port),
                "--idle-timeout",
                str(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S),
            ]
            if self.tls:
                args.append("--tls")
            else:
                args.append("--no-tls")
            if self.tls_cert_path is not None:
                args.extend(["--tls-cert", str(self.tls_cert_path)])
            if self.tls_key_path is not None:
                args.extend(["--tls-key", str(self.tls_key_path)])
            return subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            _print_line(
                f"[inter-agent] failed to start server: {exc}",
                self.output,
            )
            return None

    async def run(self) -> int:
        ppid = state._resolve_listener_key()
        self._lock_fd = state.acquire_lock(ppid)
        if self._lock_fd is None:
            existing = state.read_session_state(ppid)
            if existing:
                existing_name = str(existing.get("name", ""))
                if existing_name == self.name:
                    _print_line(
                        f'[inter-agent] already connected as "{existing_name}"; '
                        "no new listener started.",
                        self.output,
                    )
                else:
                    _print_line(
                        "[inter-agent] another listener is already running "
                        f'as "{existing_name}"; disconnect before connecting as '
                        f'"{self.name}". No new listener started.',
                        self.output,
                    )
            else:
                _print_line(
                    "[inter-agent] another listener is already starting or running; "
                    "no new listener started.",
                    self.output,
                )
            return 0

        try:
            # Auto-start server if the configured endpoint is unavailable.
            if not endpoint_available(self.host, self.port):
                self._server_proc = self._start_server()
                if self._server_proc is None:
                    return 1
                _print_line(
                    f"[inter-agent] started server (pid {self._server_proc.pid})",
                    self.output,
                )
                for _ in range(30):
                    if self._stop.is_set():
                        return 0
                    if endpoint_available(self.host, self.port):
                        break
                    await asyncio.sleep(0.5)
                else:
                    _print_line(
                        "[inter-agent] server did not become available in time",
                        self.output,
                    )
                    return 1

            backoff = RECONNECT_BACKOFF_MIN_S
            deadline: float | None = None
            name_retry_used = False
            while not self._stop.is_set():
                self._connect_task = asyncio.create_task(self._connect_and_serve(ppid))
                try:
                    await self._connect_task
                    backoff = RECONNECT_BACKOFF_MIN_S
                    deadline = None
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
                except PermanentError as exc:
                    if exc.code == "NAME_TAKEN" and not name_retry_used:
                        old_name = self.name
                        self.name = _retry_name(old_name)
                        name_retry_used = True
                        _print_line(
                            f'[inter-agent] name "{old_name}" is already in use; '
                            f'retrying as "{self.name}".',
                            self.output,
                        )
                        backoff = RECONNECT_BACKOFF_MIN_S
                        deadline = None
                        continue
                    if exc.code == "NAME_TAKEN":
                        _print_line(
                            f'[inter-agent] name "{self.name}" is already in use after retry. '
                            "Run 'inter-agent-claude list' and reconnect with a unique name.",
                            self.output,
                        )
                    else:
                        _print_line(
                            f"[inter-agent] permanent error — giving up: {exc}",
                            self.output,
                        )
                    return 1
                except websockets.ConnectionClosed:
                    pass
                finally:
                    self._connect_task = None

                if self._stop.is_set():
                    break

                if deadline is None:
                    deadline = asyncio.get_running_loop().time() + RECONNECT_DEADLINE_S
                if asyncio.get_running_loop().time() >= deadline:
                    _print_line(
                        "[inter-agent] could not reconnect within "
                        f"{RECONNECT_DEADLINE_S:.0f}s; giving up",
                        self.output,
                    )
                    return 1

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
            # An explicit shutdown never carries subscriptions forward.
            self._desired_channels.clear()

    def _is_duplicate_msg_id(self, msg_id: str) -> bool:
        """Return True if this listener recently emitted the message ID."""
        if not msg_id:
            return False
        now = time.monotonic()
        cutoff = now - RECEIVE_DEDUP_WINDOW_S
        self._recent_msg_ids = {
            recent_id: seen_at
            for recent_id, seen_at in self._recent_msg_ids.items()
            if seen_at >= cutoff
        }
        if msg_id in self._recent_msg_ids:
            return True
        self._recent_msg_ids[msg_id] = now
        return False

    async def _handle_control_request(self, op: str, channel: str) -> dict[str, object]:
        session = self._session
        if session is None:
            return {"op": "error", "code": "NOT_CONNECTED", "message": "listener not connected"}
        try:
            if op == "subscribe":
                response = await session.subscribe(channel)
                if response.get("op") == "subscribe_ok":
                    self._desired_channels.add(channel)
                return response
            response = await session.unsubscribe(channel)
            if response.get("op") == "unsubscribe_ok":
                self._desired_channels.discard(channel)
            return response
        except Exception as exc:
            return {"op": "error", "code": "LISTENER_UNAVAILABLE", "message": str(exc)}

    def _control_socket_path(self) -> Path:
        return control.control_socket_path(
            "claude", self.host, self.port, self.name, state.claude_data_dir()
        )

    async def _connect_and_serve(self, ppid: int) -> None:
        async with AgentSession(
            self.host,
            self.port,
            self.name,
            self.label,
            tls=self.tls,
            data_dir=self.data_dir,
            tls_cert_path=self.tls_cert_path,
        ) as session:
            self._session = session
            self._control_server = None
            try:
                async for raw in session:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    op = payload.get("op")
                    if op == "welcome":
                        await self._on_welcome(ppid)
                        continue

                    if op == "error":
                        code = payload.get("code", "")
                        message = payload.get("message", "")
                        if isinstance(code, str) and code == "NAME_TAKEN":
                            raise PermanentError(code, message)
                        _print_line(
                            f"[inter-agent] connection error: {code}: {message}",
                            self.output,
                        )
                        if isinstance(code, str) and code in _PERMANENT_ERROR_CODES:
                            raise PermanentError(code, message)
                        continue

                    if op == "msg":
                        self._on_msg(payload)
                        continue

                    if op == "pong":
                        continue

                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("unhandled op: %s", op)
            finally:
                if self._control_server is not None:
                    await self._control_server.stop()
                    self._control_server = None
                self._session = None

    async def _on_welcome(self, ppid: int) -> None:
        # Reapply the desired subscription set before reporting readiness so a
        # transient reconnect does not silently drop subscriptions.
        for channel in sorted(self._desired_channels):
            session = self._session
            if session is None:
                break
            try:
                await session.subscribe(channel)
            except Exception:
                pass
        # Bind the local control socket. Failures fail closed: the listener
        # stays usable and reports control as unavailable rather than entering
        # a reconnect loop or leaving a permissive socket behind.
        try:
            socket_path = self._control_socket_path()
        except OSError:
            _print_line(
                "[inter-agent] control socket unavailable; " "subscribe/unsubscribe unavailable",
                self.output,
            )
            socket_path = None
        if socket_path is not None:
            self._control_server = control.ControlServer(socket_path, self._handle_control_request)
            started = await self._control_server.start()
            if not started:
                _print_line(
                    "[inter-agent] control socket unavailable; "
                    "subscribe/unsubscribe unavailable",
                    self.output,
                )
                await self._control_server.stop()
                self._control_server = None
        state.write_session_state(
            ppid,
            {
                "session_id": self.session_id,
                "name": self.name,
                "label": self.label,
                "nonce": self.nonce,
                "listener_pid": os.getpid(),
                "host": self.host,
                "port": self.port,
                "scheme": "wss" if self.tls else "ws",
                "tls": self.tls,
            },
        )
        _print_line(
            f'[inter-agent] connected as "{self.name}"',
            self.output,
        )

    def _on_msg(self, payload: dict[str, object]) -> None:
        msg_id = str(payload.get("msg_id", ""))
        if self._is_duplicate_msg_id(msg_id):
            return
        raw_from = payload.get("from_name") or payload.get("from", "unknown")
        from_name = str(raw_from)
        text = payload.get("text", "")
        to = payload.get("to")
        channel = payload.get("channel")
        if not isinstance(text, str):
            return
        if isinstance(channel, str) and from_name == self.name:
            return

        line = formatting.format_notification(
            msg_id,
            from_name,
            text,
            str(to) if to else None,
            str(channel) if isinstance(channel, str) else None,
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


def _write_to_messages_log(msg_id: str, from_name: str, text: str, log_path: Path) -> None:
    """Append the full message to the bounded messages log."""
    state.append_message_record(msg_id, from_name, text, path=log_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-claude listen")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--name", default="")
    parser.add_argument("--label")
    parser.add_argument("--session-id")
    parser.add_argument("--tls", dest="tls", action="store_true", default=None)
    parser.add_argument("--no-tls", dest="tls", action="store_false")
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
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

    endpoint = resolve_endpoint(
        args.host,
        args.port,
        allow_discovery=True,
        tls=args.tls,
        tls_cert_path=args.tls_cert,
        tls_key_path=args.tls_key,
    )
    listener = Listener(
        host=endpoint.host,
        port=endpoint.port,
        name=name,
        label=args.label,
        session_id=args.session_id,
        tls=endpoint.tls,
        data_dir=endpoint.data_dir,
        tls_cert_path=endpoint.tls_cert_path,
        tls_key_path=endpoint.tls_key_path,
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
