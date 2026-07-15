"""Private local Unix-domain socket control bridge.

Short-lived adapter commands (``subscribe``, ``unsubscribe``) talk to the
matching live agent listener through a local Unix-domain socket instead of
opening a new agent or control identity on the bus. One newline-delimited
JSON request and response are exchanged per connection.

The bridge is strictly local and private: it never carries the shared server
secret and never accepts anything but ``subscribe`` and ``unsubscribe``
requests. Each endpoint is derived from the adapter, normalized endpoint,
and routing name so distinct listeners never collide on the socket path.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

CONTROL_DIR_NAME = "control"
CONTROL_TIMEOUT_S = 2.0
CONTROL_MAX_REQUEST_BYTES = 64 * 1024
SUPPORTED_OPS = frozenset({"subscribe", "unsubscribe"})

#: StreamReader buffer limit set one byte above the request cap so a request at
#: or below the cap is read in full and checked explicitly, while a genuinely
#: oversized line raises ``LimitOverrunError`` before the length check.
_READ_LIMIT = CONTROL_MAX_REQUEST_BYTES + 1

#: Exactly the request keys the bridge accepts. Any other key is rejected so a
#: compromised or buggy command cannot exfiltrate state through the bridge.
_REQUEST_KEYS = frozenset({"op", "channel"})

#: Amount of the SHA-256 digest carried in the socket filename so the path
#: stays bounded regardless of name length.
_SOCKET_HASH_LEN = 16


class ControlError(Exception):
    """Local control-bridge failure mapped to a clean stderr diagnostic."""


RequestHandler = Callable[[str, str], Awaitable[dict[str, object]]]


def _normalize_host(host: str) -> str:
    return host.strip().lower()


def control_dir(base_data_dir: Path) -> Path:
    """Return the ``control/`` child of an adapter data directory (mode 0700).

    Permission failures are surfaced rather than swallowed: a control
    directory that cannot be locked down to ``0700`` must not be used.
    """
    path = base_data_dir / CONTROL_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def control_socket_path(
    adapter: str,
    host: str,
    port: int,
    name: str,
    base_data_dir: Path,
) -> Path:
    """Derive a bounded, collision-free socket path for one listener identity.

    Surfaces directory setup/permission failures to the caller instead of
    returning a path whose parent directory could not be secured.
    """
    digest = hashlib.sha256()
    digest.update(adapter.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(_normalize_host(host).encode("utf-8"))
    digest.update(b"\x00")
    digest.update(str(port).encode("utf-8"))
    digest.update(b"\x00")
    digest.update(name.encode("utf-8"))
    suffix = digest.hexdigest()[:_SOCKET_HASH_LEN]
    return control_dir(base_data_dir) / f"control-{adapter}-{suffix}.sock"


def _local_error(code: str, message: str) -> dict[str, object]:
    return {"op": "error", "code": code, "message": message}


async def _write_line(writer: asyncio.StreamWriter, payload: dict[str, object]) -> None:
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    writer.write(data)
    await asyncio.wait_for(writer.drain(), timeout=CONTROL_TIMEOUT_S)


async def probe_alive(path: Path) -> bool:
    """Return True when a listener is accepting connections at ``path``."""
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(str(path), limit=_READ_LIMIT),
            timeout=CONTROL_TIMEOUT_S,
        )
    except (FileNotFoundError, ConnectionRefusedError, TimeoutError, OSError):
        return False
    try:
        writer.close()
        try:
            await writer.wait_closed()
        except (OSError, asyncio.CancelledError):
            pass
    except OSError:
        pass
    return True


class ControlServer:
    """Listener-side Unix-domain control socket bound to one live session.

    A single server owns its socket; on startup it removes a pre-existing
    socket file only after a failed liveness probe, and on shutdown it unlinks
    the endpoint only if it still owns it. Setup/permission failures fail
    closed: the server is not exposed and control is reported as unavailable
    rather than left in a permissive state or allowed to break the listener.
    """

    def __init__(self, path: Path, handle: RequestHandler) -> None:
        self._path = path
        self._handle = handle
        self._server: asyncio.Server | None = None
        self._inode: int | None = None
        self._dev: int | None = None

    async def start(self) -> bool:
        """Bind the control socket securely.

        Returns False (control unavailable) if a live endpoint already owns the
        socket, or if binding or securing the socket fails. On a permission
        failure after binding, the server is closed and the just-created endpoint
        is removed so no permissive socket is ever exposed.
        """
        if self._path.exists():
            if await probe_alive(self._path):
                return False
            try:
                self._path.unlink()
            except OSError:
                return False
        try:
            self._server = await asyncio.start_unix_server(
                self._handle_connection, path=str(self._path), limit=_READ_LIMIT
            )
        except OSError:
            self._server = None
            return False
        # Capture the just-bound endpoint's identity immediately so setup-time
        # cleanup only unlinks the endpoint this server created, even though full
        # ownership is only recorded after chmod/stat succeed.
        bound_inode: int | None
        bound_dev: int | None
        try:
            bound_stat = self._path.stat()
            bound_inode = bound_stat.st_ino
            bound_dev = bound_stat.st_dev
        except OSError:
            await self._close_server()
            return False
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            await self._close_server()
            await self._unlink_owned(bound_inode, bound_dev)
            return False
        try:
            stat = self._path.stat()
        except OSError:
            await self._close_server()
            await self._unlink_owned(bound_inode, bound_dev)
            return False
        # The endpoint still exists and is still the one we bound. Confirm
        # it hasn't been replaced out from under us before accepting ownership.
        if stat.st_ino != bound_inode or stat.st_dev != bound_dev:
            await self._close_server()
            return False
        self._inode = stat.st_ino
        self._dev = stat.st_dev
        return True

    async def _close_server(self) -> None:
        server = self._server
        self._server = None
        if server is not None:
            server.close()
            try:
                await server.wait_closed()
            except (OSError, asyncio.CancelledError):
                pass

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            try:
                raw = await asyncio.wait_for(reader.readline(), timeout=CONTROL_TIMEOUT_S)
            except TimeoutError:
                return
            except (asyncio.LimitOverrunError, ValueError):
                # A genuinely oversized line raises before the length check.
                await _write_line(
                    writer, _local_error("REQUEST_TOO_LARGE", "control request too large")
                )
                return
            if not raw:
                return
            if len(raw) > CONTROL_MAX_REQUEST_BYTES:
                await _write_line(
                    writer, _local_error("REQUEST_TOO_LARGE", "control request too large")
                )
                return
            try:
                payload: object = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                await _write_line(writer, _local_error("BAD_REQUEST", "malformed control request"))
                return
            if not isinstance(payload, dict):
                await _write_line(
                    writer, _local_error("BAD_REQUEST", "control request must be an object")
                )
                return
            if set(payload.keys()) != _REQUEST_KEYS:
                await _write_line(
                    writer,
                    _local_error("BAD_REQUEST", "control request must contain only op and channel"),
                )
                return
            op = payload.get("op")
            channel = payload.get("channel")
            if not isinstance(op, str) or op not in SUPPORTED_OPS:
                await _write_line(writer, _local_error("BAD_OP", "unsupported control op"))
                return
            if not isinstance(channel, str) or not channel:
                await _write_line(writer, _local_error("BAD_CHANNEL", "channel required"))
                return
            try:
                response = await asyncio.wait_for(
                    self._handle(op, channel), timeout=CONTROL_TIMEOUT_S
                )
            except TimeoutError:
                response = _local_error("TIMEOUT", "listener did not respond in time")
            except Exception as exc:  # listener-side failure, never propagate as traceback
                response = _local_error("LISTENER_UNAVAILABLE", str(exc))
            await _write_line(writer, response)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (OSError, asyncio.CancelledError, BrokenPipeError):
                pass

    async def stop(self) -> None:
        await self._close_server()
        await self._unlink_owned(self._inode, self._dev)
        self._inode = None
        self._dev = None

    async def _unlink_owned(self, inode: int | None, dev: int | None) -> None:
        """Unlink the endpoint only if its identity still matches.

        Used by both normal shutdown and setup-time failure cleanup so a
        server never removes an endpoint it no longer owns (replacement race).
        """
        if inode is None or dev is None:
            return
        try:
            stat = self._path.stat()
        except OSError:
            return
        if stat.st_ino == inode and stat.st_dev == dev:
            try:
                self._path.unlink()
            except OSError:
                pass


async def request(
    adapter: str,
    host: str,
    port: int,
    name: str,
    base_data_dir: Path,
    op: str,
    channel: str,
) -> dict[str, object]:
    """Send one control request to the listener owning ``name``'s socket.

    Path/setup, connect, read, and decode failures are converted to clean
    ``ControlError`` diagnostics; oversized or malformed responses raise rather
    than returning partial data.
    """
    try:
        path = control_socket_path(adapter, host, port, name, base_data_dir)
    except OSError as exc:
        raise ControlError(f"control socket unavailable: {exc}") from exc
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(str(path), limit=_READ_LIMIT),
            timeout=CONTROL_TIMEOUT_S,
        )
    except FileNotFoundError as exc:
        raise ControlError("not connected; start the listener first") from exc
    except ConnectionRefusedError as exc:
        raise ControlError("listener not reachable; reconnecting or not running") from exc
    except TimeoutError as exc:
        raise ControlError("timed out connecting to listener") from exc
    except OSError as exc:
        raise ControlError(f"listener control connection failed: {exc}") from exc

    try:
        request_payload = json.dumps({"op": op, "channel": channel}) + "\n"
        writer.write(request_payload.encode("utf-8"))
        try:
            await asyncio.wait_for(writer.drain(), timeout=CONTROL_TIMEOUT_S)
        except TimeoutError as exc:
            raise ControlError("timed out sending control request") from exc
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=CONTROL_TIMEOUT_S)
        except TimeoutError as exc:
            raise ControlError("timed out waiting for listener response") from exc
        except (asyncio.LimitOverrunError, ValueError) as exc:
            raise ControlError("oversized response from listener") from exc
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except (OSError, asyncio.CancelledError, BrokenPipeError):
            pass

    if not raw:
        raise ControlError("no response from listener")
    if len(raw) > CONTROL_MAX_REQUEST_BYTES:
        raise ControlError("oversized response from listener")
    try:
        payload: object = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ControlError("malformed response from listener") from exc
    if not isinstance(payload, dict):
        raise ControlError("response from listener must be an object")
    return {str(key): value for key, value in payload.items()}
