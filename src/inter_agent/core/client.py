from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from pathlib import Path
from typing import TextIO

import websockets
from websockets.asyncio.client import ClientConnection

from inter_agent.core.auth import AuthError, AuthProtocolError, client_handshake
from inter_agent.core.auth import build_hello as build_auth_hello
from inter_agent.core.shared import resolve_endpoint, resolve_shared_secret
from inter_agent.core.transport import client_ssl_context, websocket_uri


def build_hello(
    session_id: str, name: str, label: str | None = None, client_nonce: str | None = None
) -> dict[str, object]:
    return build_auth_hello(
        role="agent",
        session_id=session_id,
        name=name,
        label=label,
        capabilities={},
        client_nonce=client_nonce,
    )


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _json_object(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server response must be a JSON object")
    return {str(key): value for key, value in payload.items()}


async def iter_client_frames(
    host: str,
    port: int,
    name: str,
    label: str | None = None,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> AsyncGenerator[str, None]:
    """Connect an agent session and yield raw server JSON frames.

    The first yielded frame is the server welcome response. Subsequent frames are
    peer messages or protocol responses received for the connected session.
    """
    secret = resolve_shared_secret().secret
    session_id = os.getenv("INTER_AGENT_SESSION_ID", str(uuid.uuid4()))
    hello = build_hello(session_id, name, label)
    ssl_context = client_ssl_context(tls, data_dir, tls_cert_path)
    async with websockets.connect(websocket_uri(host, port, tls), ssl=ssl_context) as ws:
        try:
            yield await client_handshake(ws, secret, hello)
        except AuthError as exc:
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
        async for msg in ws:
            yield _text_frame(msg)


async def run_client(
    host: str,
    port: int,
    name: str,
    label: str | None = None,
    output: TextIO | None = None,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> None:
    """Run the connect command behavior using typed inputs instead of argv."""
    stream = output or sys.stdout
    async for msg in iter_client_frames(
        host, port, name, label, tls=tls, data_dir=data_dir, tls_cert_path=tls_cert_path
    ):
        print(msg, file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-connect")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--name", dest="name_option")
    parser.add_argument("--label")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--tls", dest="tls", action="store_true", default=None)
    parser.add_argument("--no-tls", dest="tls", action="store_false")
    parser.add_argument("--tls-cert")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    name = args.name_option or args.name
    if not name:
        parser.error("name is required")
    endpoint = resolve_endpoint(
        args.host, args.port, allow_discovery=True, tls=args.tls, tls_cert_path=args.tls_cert
    )
    asyncio.run(
        run_client(
            endpoint.host,
            endpoint.port,
            name,
            args.label,
            tls=endpoint.tls,
            data_dir=endpoint.data_dir,
            tls_cert_path=endpoint.tls_cert_path,
        )
    )
    return 0


_COMMAND_TIMEOUT = 0.1
_EOF = object()


class _PendingCommand:
    __slots__ = ("expected_ops", "future")

    def __init__(self, expected_ops: set[str], future: asyncio.Future[str]) -> None:
        self.expected_ops = expected_ops
        self.future = future


class AgentSession:
    """Persistent async agent connection with channel operations.

    ``async with AgentSession(...) as session:`` establishes a single agent
    session and yields inbound frames through ``async for frame in session:``.
    Subscribe, unsubscribe, and publish operations reuse the same connection
    and session identity.
    """

    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        label: str | None = None,
        *,
        tls: bool = False,
        data_dir: Path | None = None,
        tls_cert_path: Path | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.label = label
        self.tls = tls
        self.data_dir = data_dir
        self.tls_cert_path = tls_cert_path

        self._ws: ClientConnection | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._inbox: asyncio.Queue[str | object] = asyncio.Queue()
        self._command_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()
        self._pending: _PendingCommand | None = None
        self._closed = False
        self._eof_delivered = False

    async def __aenter__(self) -> AgentSession:
        secret = resolve_shared_secret().secret
        session_id = os.getenv("INTER_AGENT_SESSION_ID", str(uuid.uuid4()))
        hello = build_hello(session_id, self.name, self.label)
        ssl_context = client_ssl_context(self.tls, self.data_dir, self.tls_cert_path)
        self._ws = await websockets.connect(
            websocket_uri(self.host, self.port, self.tls), ssl=ssl_context
        )
        try:
            welcome = await client_handshake(self._ws, secret, hello)
        except AuthError as exc:
            await self._close()
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            await self._close()
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
        await self._inbox.put(welcome)
        self._reader_task = asyncio.create_task(self._reader_loop())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        await self._close()

    async def _close(self) -> None:
        self._closed = True
        ws = self._ws
        self._ws = None
        if ws is not None:
            await ws.close()
        task = self._reader_task
        self._reader_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._deliver_eof()

    async def _deliver_eof(self) -> None:
        async with self._state_lock:
            if self._eof_delivered:
                return
            self._eof_delivered = True
        await self._inbox.put(_EOF)

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iter_frames()

    async def _iter_frames(self) -> AsyncGenerator[str, None]:
        while True:
            item = await self._inbox.get()
            if item is _EOF:
                break
            yield item  # type: ignore[misc]

    async def _reader_loop(self) -> None:
        ws = self._ws
        if ws is None:
            return
        try:
            async for msg in ws:
                raw = _text_frame(msg)
                op = self._frame_op(raw)
                routed = False
                async with self._state_lock:
                    if self._pending is not None and op in self._pending.expected_ops:
                        if not self._pending.future.done():
                            self._pending.future.set_result(raw)
                        self._pending = None
                        routed = True
                if not routed:
                    await self._inbox.put(raw)
        except websockets.ConnectionClosed:
            pass
        except asyncio.CancelledError:
            raise
        finally:
            self._closed = True
            async with self._state_lock:
                if self._pending is not None and not self._pending.future.done():
                    self._pending.future.set_exception(ConnectionAbortedError("session closed"))
            await self._deliver_eof()

    @staticmethod
    def _frame_op(raw: str) -> str | None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        op = payload.get("op")
        return op if isinstance(op, str) else None

    async def _exchange(
        self,
        payload: dict[str, object],
        expected_ops: set[str],
        *,
        allow_timeout: bool = False,
    ) -> str | None:
        async with self._command_lock:
            future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
            async with self._state_lock:
                if self._closed:
                    raise RuntimeError("session closed")
                self._pending = _PendingCommand(expected_ops, future)
            try:
                ws = self._ws
                if ws is None:
                    raise RuntimeError("session closed")
                await ws.send(json.dumps(payload))
                if allow_timeout:
                    try:
                        return await asyncio.wait_for(future, timeout=_COMMAND_TIMEOUT)
                    except TimeoutError:
                        return None
                return await asyncio.wait_for(future, timeout=_COMMAND_TIMEOUT)
            finally:
                async with self._state_lock:
                    if self._pending is not None and self._pending.future is future:
                        self._pending = None

    async def subscribe(self, channel: str) -> dict[str, object]:
        """Subscribe to a channel and return the server's response."""
        raw = await self._exchange(
            {"op": "subscribe", "channel": channel}, {"subscribe_ok", "error"}
        )
        assert raw is not None
        return _json_object(raw)

    async def unsubscribe(self, channel: str) -> dict[str, object]:
        """Unsubscribe from a channel and return the server's response."""
        raw = await self._exchange(
            {"op": "unsubscribe", "channel": channel}, {"unsubscribe_ok", "error"}
        )
        assert raw is not None
        return _json_object(raw)

    async def publish(
        self, channel: str, text: str, from_name: str | None = None
    ) -> dict[str, object] | None:
        """Publish a message to a channel.

        Returns a parsed protocol error if one is received within the command
        timeout, otherwise ``None`` on success.
        """
        payload: dict[str, object] = {"op": "publish", "channel": channel, "text": text}
        if from_name is not None:
            payload["from_name"] = from_name
        raw = await self._exchange(payload, {"error"}, allow_timeout=True)
        if raw is None:
            return None
        return _json_object(raw)


if __name__ == "__main__":
    raise SystemExit(main())
