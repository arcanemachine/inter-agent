from __future__ import annotations

import argparse
import asyncio
import http
import json
import signal
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import websockets
from websockets.asyncio.server import ServerConnection
from websockets.http11 import Request, Response

from inter_agent.core.auth import build_auth_challenge, client_nonce_from_hello, verify_client_proof
from inter_agent.core.errors import ErrorCode
from inter_agent.core.router import RouterMiddleware
from inter_agent.core.shared import (
    Limits,
    next_msg_id,
    resolve_endpoint,
    resolve_shared_secret,
    utc_now,
    validate_channel_name,
    validate_name,
)
from inter_agent.core.tls import TlsConfigError, build_server_ssl_context

DEFAULT_IDLE_TIMEOUT_S: float | None = None


@dataclass
class Conn:
    ws: ServerConnection
    session_id: str
    name: str
    role: str
    label: str | None
    capabilities: dict[str, object]


@dataclass(frozen=True)
class TargetResolution:
    target: Conn | None
    error_code: ErrorCode | None = None
    message: str | None = None


class BusServer:
    def __init__(
        self,
        host: str,
        port: int,
        limits: Limits | None = None,
        idle_timeout_s: float | None = DEFAULT_IDLE_TIMEOUT_S,
    ) -> None:
        self.host = host
        self.port = port
        self.secret = resolve_shared_secret().secret
        self.limits = limits or Limits()
        self.registry: dict[str, Conn] = {}
        self.channels: dict[str, set[str]] = {}
        self.subscriptions: dict[str, set[str]] = {}
        self.middlewares: list[RouterMiddleware] = []
        self.shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._idle_timeout = idle_timeout_s
        self._idle_timer: asyncio.Task[None] | None = None

    def _cancel_idle_timer(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

    def _schedule_idle_timer(self) -> None:
        if self._idle_timeout is None or self._idle_timeout <= 0:
            return
        self._cancel_idle_timer()
        self._idle_timer = asyncio.create_task(self._start_idle_timer())

    async def _start_idle_timer(self) -> None:
        """Shut down after idle_timeout seconds with no connections when configured."""
        timeout = self._idle_timeout
        if timeout is None or timeout <= 0:
            return
        try:
            # Use a CancelledError check below rather than watching shutdown_event,
            # so we don't race with an external shutdown_set + new connection.
            await asyncio.sleep(timeout)
        except asyncio.CancelledError:
            return
        # If we weren't cancelled, nobody reconnected — time to stop.
        self.shutdown_event.set()

    async def send_error(self, ws: ServerConnection, code: ErrorCode, message: str) -> None:
        await ws.send(json.dumps({"op": "error", "code": code.value, "message": message}))

    async def read_object(
        self, ws: ServerConnection, raw: str | bytes, frame_name: str
    ) -> dict[str, object] | None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            await self.send_error(ws, ErrorCode.PROTOCOL_ERROR, f"{frame_name} must be valid JSON")
            return None
        if not isinstance(payload, dict):
            await self.send_error(ws, ErrorCode.PROTOCOL_ERROR, f"{frame_name} must be an object")
            return None
        return {str(key): value for key, value in payload.items()}

    async def handle(self, ws: ServerConnection) -> None:
        session_id = None
        self._cancel_idle_timer()
        try:
            raw = await ws.recv()
            hello = await self.read_object(ws, raw, "first frame")
            if hello is None:
                return
            if hello.get("op") != "hello":
                await self.send_error(ws, ErrorCode.PROTOCOL_ERROR, "first op must be hello")
                return

            client_nonce = client_nonce_from_hello(hello)
            if client_nonce is None:
                await self.send_error(ws, ErrorCode.AUTH_FAILED, "invalid auth")
                return
            challenge = build_auth_challenge(
                self.secret,
                client_nonce=client_nonce,
                hello=hello,
            )
            await ws.send(json.dumps(challenge))
            response_raw = await ws.recv()
            response = await self.read_object(ws, response_raw, "auth_response")
            if response is None:
                return
            if response.get("op") != "auth_response":
                await self.send_error(ws, ErrorCode.AUTH_FAILED, "invalid auth response")
                return
            client_proof_value = response.get("client_proof")
            server_nonce_value = challenge.get("server_nonce")
            if not isinstance(client_proof_value, str) or not isinstance(server_nonce_value, str):
                await self.send_error(ws, ErrorCode.AUTH_FAILED, "invalid auth response")
                return
            if not verify_client_proof(
                client_proof_value,
                self.secret,
                client_nonce=client_nonce,
                server_nonce=server_nonce_value,
                hello=hello,
            ):
                await self.send_error(ws, ErrorCode.AUTH_FAILED, "invalid auth")
                return

            role_value = hello.get("role")
            session_id_value = hello.get("session_id")
            name_value = hello.get("name")
            label_value = hello.get("label")
            if label_value is not None and not isinstance(label_value, str):
                await self.send_error(ws, ErrorCode.BAD_LABEL, "label must be a string or null")
                return
            if not isinstance(role_value, str) or role_value not in {"agent", "control"}:
                await self.send_error(ws, ErrorCode.BAD_ROLE, "role must be agent or control")
                return
            if not session_id_value or not isinstance(session_id_value, str):
                await self.send_error(ws, ErrorCode.BAD_SESSION, "missing session_id")
                return
            raw_capabilities = hello.get("capabilities")
            if not isinstance(raw_capabilities, dict):
                await self.send_error(
                    ws, ErrorCode.PROTOCOL_ERROR, "capabilities must be an object"
                )
                return

            role = role_value
            async with self._lock:
                if session_id_value in self.registry:
                    await self.send_error(ws, ErrorCode.SESSION_TAKEN, "session_id already active")
                    return
                if len(self.registry) >= self.limits.connection_max:
                    await self.send_error(
                        ws, ErrorCode.TOO_MANY_CONNECTIONS, "connection limit reached"
                    )
                    return
                session_id = session_id_value
                label = label_value
                if role == "agent":
                    if not validate_name(name_value):
                        await self.send_error(ws, ErrorCode.BAD_NAME, "invalid name")
                        return
                    assert isinstance(name_value, str)
                    assigned_name = name_value
                    if any(c.name == assigned_name for c in self.registry.values()):
                        await self.send_error(ws, ErrorCode.NAME_TAKEN, "name already in use")
                        return
                elif isinstance(name_value, str) and name_value:
                    assigned_name = name_value
                else:
                    assigned_name = f"control-{session_id[:6]}"

                capabilities = {str(key): value for key, value in raw_capabilities.items()}
                conn = Conn(
                    ws=ws,
                    session_id=session_id,
                    name=assigned_name,
                    role=role,
                    label=label,
                    capabilities=capabilities,
                )
                self.registry[session_id] = conn
            await ws.send(
                json.dumps(
                    {
                        "op": "welcome",
                        "session_id": session_id,
                        "assigned_name": conn.name,
                        "capabilities": {
                            "core": {"version": "0.1"},
                            "channels": True,
                            "rate_limit": False,
                        },
                    }
                )
            )

            async for frame in ws:
                msg = await self.read_object(ws, frame, "frame")
                if msg is None:
                    return
                op = msg.get("op")
                if op == "ping":
                    await ws.send(json.dumps({"op": "pong"}))
                elif op == "bye":
                    return
                elif op == "shutdown":
                    await self._handle_shutdown(conn)
                elif op == "kick":
                    await self._handle_kick(conn, msg)
                elif op == "list":
                    sessions = [
                        {
                            "session_id": c.session_id,
                            "name": c.name,
                            "label": c.label,
                        }
                        for c in sorted(self.registry.values(), key=lambda conn: conn.name)
                        if c.role == "agent"
                    ]
                    await ws.send(json.dumps({"op": "list_ok", "sessions": sessions}))
                elif op == "send":
                    await self._route_send(conn, msg)
                elif op == "broadcast":
                    await self._route_broadcast(conn, msg)
                elif op == "custom":
                    await self._route_custom(conn, msg)
                elif op == "subscribe":
                    await self._route_subscribe(conn, msg)
                elif op == "unsubscribe":
                    await self._route_unsubscribe(conn, msg)
                elif op == "publish":
                    await self._route_publish(conn, msg)
                elif op == "channels":
                    await self._route_channels(conn, msg)
                else:
                    await self.send_error(ws, ErrorCode.UNKNOWN_OP, f"unsupported op: {op}")
        except websockets.ConnectionClosed:
            pass
        finally:
            if session_id:
                await self._cleanup_session_subscriptions(session_id)
                if session_id in self.registry:
                    self.registry.pop(session_id, None)
            if not self.registry:
                self._schedule_idle_timer()

    async def _apply_middlewares(self, sender: Conn, msg: dict[str, object]) -> None:
        for middleware in self.middlewares:
            await middleware.before_route(sender.session_id, msg)

    async def _handle_shutdown(self, sender: Conn) -> None:
        if sender.role != "control":
            await self.send_error(sender.ws, ErrorCode.BAD_ROLE, "shutdown requires control role")
            return
        await sender.ws.send(json.dumps({"op": "shutdown_ok"}))
        self.shutdown_event.set()

    async def _handle_kick(self, sender: Conn, msg: dict[str, object]) -> None:
        """Force-disconnect a registered session by name or session_id.

        Control-only. Used to clear ghost or unwanted sessions without
        restarting the whole server. Not exposed through host extension tools.
        """
        if sender.role != "control":
            await self.send_error(sender.ws, ErrorCode.BAD_ROLE, "kick requires control role")
            return

        target_name = msg.get("name")
        target_session_id = msg.get("session_id")
        target: Conn | None = None
        async with self._lock:
            if isinstance(target_session_id, str) and target_session_id:
                target = self.registry.get(target_session_id)
            elif isinstance(target_name, str) and target_name:
                target = next(
                    (c for c in self.registry.values() if c.name == target_name),
                    None,
                )
            else:
                await self.send_error(
                    sender.ws, ErrorCode.PROTOCOL_ERROR, "kick requires name or session_id"
                )
                return

            if target is None:
                await self.send_error(sender.ws, ErrorCode.UNKNOWN_TARGET, "unknown target")
                return

            # Kick targets only registered agent-role sessions. A control-role
            # connection is rejected without being closed.
            if target.role != "agent":
                await self.send_error(
                    sender.ws, ErrorCode.BAD_ROLE, "kick targets agent sessions only"
                )
                return

            # Remove before closing so the target's own handler finally block
            # sees the session already gone and does not double-remove. Late
            # cleanup by session_id cannot clobber a newer same-name connection
            # claimed under a different session_id.
            self.registry.pop(target.session_id, None)
            for channel in list(self.subscriptions.pop(target.session_id, [])):
                self.channels[channel].discard(target.session_id)
                if not self.channels[channel]:
                    self.channels.pop(channel, None)
            await sender.ws.send(
                json.dumps(
                    {
                        "op": "kick_ok",
                        "name": target.name,
                        "session_id": target.session_id,
                    }
                )
            )

        # Signal the target that it was removed, then close. Both are best
        # effort: a target that raced closed first must not unwind the control
        # request. The KICKED message carries no controller identity, secret, or
        # private session metadata.
        try:
            await self.send_error(target.ws, ErrorCode.KICKED, "removed by kick")
        except websockets.ConnectionClosed:
            pass
        try:
            await target.ws.close(code=1000, reason="kicked")
        except websockets.ConnectionClosed:
            pass
        if not self.registry:
            self._schedule_idle_timer()

    async def close_connections(self) -> None:
        for conn in list(self.registry.values()):
            await conn.ws.close(code=1001, reason="server shutdown")

    def _resolve_target(self, target_name: object) -> TargetResolution:
        if not isinstance(target_name, str) or not target_name:
            return TargetResolution(
                target=None,
                error_code=ErrorCode.UNKNOWN_TARGET,
                message=f"unknown target: {target_name}",
            )

        exact = next((c for c in self.registry.values() if c.name == target_name), None)
        if exact is not None:
            return TargetResolution(target=exact)

        prefix_matches = [c for c in self.registry.values() if c.name.startswith(target_name)]
        if len(prefix_matches) == 1:
            return TargetResolution(target=prefix_matches[0])
        if len(prefix_matches) > 1:
            return TargetResolution(
                target=None,
                error_code=ErrorCode.AMBIGUOUS_TARGET,
                message=f"ambiguous target: {target_name}",
            )
        return TargetResolution(
            target=None,
            error_code=ErrorCode.UNKNOWN_TARGET,
            message=f"unknown target: {target_name}",
        )

    async def _send_resolution_error(self, sender: Conn, resolution: TargetResolution) -> None:
        if resolution.error_code is None or resolution.message is None:
            raise RuntimeError("target resolution did not include an error")
        await self.send_error(sender.ws, resolution.error_code, resolution.message)

    async def _route_send(self, sender: Conn, msg: dict[str, object]) -> None:
        await self._apply_middlewares(sender, msg)
        to = msg.get("to")
        text = msg.get("text")
        if not isinstance(text, str):
            await self.send_error(sender.ws, ErrorCode.BAD_TEXT, "text must be a string")
            return
        if len(text.encode()) > self.limits.direct_text_max:
            await self.send_error(sender.ws, ErrorCode.TEXT_TOO_LARGE, "direct message too large")
            return
        resolution = self._resolve_target(to)
        if resolution.target is None:
            await self._send_resolution_error(sender, resolution)
            return
        target = resolution.target
        from_name = msg.get("from_name", sender.name)
        if not isinstance(from_name, str):
            await self.send_error(sender.ws, ErrorCode.BAD_FROM_NAME, "from_name must be a string")
            return
        await target.ws.send(
            json.dumps(
                {
                    "op": "msg",
                    "msg_id": next_msg_id(),
                    "from": sender.session_id,
                    "from_name": from_name,
                    "to": target.name,
                    "text": text,
                    "ts": utc_now(),
                }
            )
        )

    async def _route_broadcast(self, sender: Conn, msg: dict[str, object]) -> None:
        await self._apply_middlewares(sender, msg)
        text = msg.get("text")
        if not isinstance(text, str):
            await self.send_error(sender.ws, ErrorCode.BAD_TEXT, "text must be a string")
            return
        if len(text.encode()) > self.limits.broadcast_text_max:
            await self.send_error(
                sender.ws, ErrorCode.TEXT_TOO_LARGE, "broadcast message too large"
            )
            return
        from_name = msg.get("from_name", sender.name)
        if not isinstance(from_name, str):
            await self.send_error(sender.ws, ErrorCode.BAD_FROM_NAME, "from_name must be a string")
            return
        payload = json.dumps(
            {
                "op": "msg",
                "msg_id": next_msg_id(),
                "from": sender.session_id,
                "from_name": from_name,
                "text": text,
                "ts": utc_now(),
            }
        )
        for conn in self.registry.values():
            if conn.session_id == sender.session_id or conn.role != "agent":
                continue
            await conn.ws.send(payload)

    async def _route_custom(self, sender: Conn, msg: dict[str, object]) -> None:
        await self._apply_middlewares(sender, msg)
        custom_type = msg.get("custom_type")
        if not isinstance(custom_type, str) or not custom_type:
            await self.send_error(sender.ws, ErrorCode.BAD_CUSTOM_TYPE, "custom_type required")
            return
        if len(custom_type.encode()) > self.limits.custom_type_max:
            await self.send_error(sender.ws, ErrorCode.BAD_CUSTOM_TYPE, "custom_type too large")
            return
        custom_payload = msg.get("payload")
        custom_payload_size = len(json.dumps(custom_payload, ensure_ascii=False).encode())
        if custom_payload_size > self.limits.custom_payload_max:
            await self.send_error(
                sender.ws, ErrorCode.CUSTOM_PAYLOAD_TOO_LARGE, "custom payload too large"
            )
            return
        payload = {
            "op": "msg",
            "msg_id": next_msg_id(),
            "from": sender.session_id,
            "from_name": sender.name,
            "custom_type": custom_type,
            "payload": custom_payload,
            "ts": utc_now(),
        }
        if msg.get("to"):
            resolution = self._resolve_target(msg.get("to"))
            if resolution.target is None:
                await self._send_resolution_error(sender, resolution)
                return
            target = resolution.target
            payload["to"] = target.name
            await target.ws.send(json.dumps(payload))
            return
        for conn in self.registry.values():
            if conn.session_id == sender.session_id or conn.role != "agent":
                continue
            await conn.ws.send(json.dumps(payload))

    async def _cleanup_session_subscriptions(self, session_id: str) -> None:
        async with self._lock:
            for channel in list(self.subscriptions.get(session_id, [])):
                self.channels[channel].discard(session_id)
                if not self.channels[channel]:
                    self.channels.pop(channel, None)
            self.subscriptions.pop(session_id, None)

    def _validate_channel_name(self, channel: object) -> str | None:
        if not validate_channel_name(channel, self.limits.channel_name_max):
            return None
        return str(channel)

    async def _route_subscribe(self, sender: Conn, msg: dict[str, object]) -> None:
        if sender.role != "agent":
            await self.send_error(sender.ws, ErrorCode.BAD_ROLE, "subscribe requires agent role")
            return
        channel = self._validate_channel_name(msg.get("channel"))
        if channel is None:
            await self.send_error(sender.ws, ErrorCode.BAD_CHANNEL, "invalid channel name")
            return
        async with self._lock:
            session_subs = self.subscriptions.setdefault(sender.session_id, set())
            if channel in session_subs:
                await sender.ws.send(json.dumps({"op": "subscribe_ok", "channel": channel}))
                return
            if len(session_subs) >= self.limits.subscriptions_max:
                await self.send_error(
                    sender.ws, ErrorCode.CHANNEL_LIMIT_REACHED, "subscription limit reached"
                )
                return
            is_new_channel = channel not in self.channels
            if is_new_channel and len(self.channels) >= self.limits.channels_max:
                await self.send_error(
                    sender.ws, ErrorCode.CHANNEL_LIMIT_REACHED, "server channel limit reached"
                )
                return
            session_subs.add(channel)
            self.channels.setdefault(channel, set()).add(sender.session_id)
            await sender.ws.send(json.dumps({"op": "subscribe_ok", "channel": channel}))

    async def _route_unsubscribe(self, sender: Conn, msg: dict[str, object]) -> None:
        if sender.role != "agent":
            await self.send_error(sender.ws, ErrorCode.BAD_ROLE, "unsubscribe requires agent role")
            return
        channel = self._validate_channel_name(msg.get("channel"))
        if channel is None:
            await self.send_error(sender.ws, ErrorCode.BAD_CHANNEL, "invalid channel name")
            return
        async with self._lock:
            session_subs = self.subscriptions.get(sender.session_id, set())
            if channel not in session_subs:
                await self.send_error(sender.ws, ErrorCode.NOT_SUBSCRIBED, "not subscribed")
                return
            session_subs.discard(channel)
            if not session_subs:
                self.subscriptions.pop(sender.session_id, None)
            self.channels[channel].discard(sender.session_id)
            if not self.channels[channel]:
                self.channels.pop(channel, None)
            await sender.ws.send(json.dumps({"op": "unsubscribe_ok", "channel": channel}))

    async def _route_publish(self, sender: Conn, msg: dict[str, object]) -> None:
        if sender.role not in {"agent", "control"}:
            await self.send_error(
                sender.ws, ErrorCode.BAD_ROLE, "publish requires agent or control role"
            )
            return
        channel = self._validate_channel_name(msg.get("channel"))
        if channel is None:
            await self.send_error(sender.ws, ErrorCode.BAD_CHANNEL, "invalid channel name")
            return
        text = msg.get("text")
        if not isinstance(text, str):
            await self.send_error(sender.ws, ErrorCode.BAD_TEXT, "text must be a string")
            return
        if len(text.encode()) > self.limits.broadcast_text_max:
            await self.send_error(sender.ws, ErrorCode.TEXT_TOO_LARGE, "publish text too large")
            return
        async with self._lock:
            subscribers = self.channels.get(channel)
            if not subscribers:
                await self.send_error(sender.ws, ErrorCode.UNKNOWN_CHANNEL, "unknown channel")
                return
            from_name = msg.get("from_name", sender.name)
            if not isinstance(from_name, str):
                await self.send_error(
                    sender.ws, ErrorCode.BAD_FROM_NAME, "from_name must be a string"
                )
                return
            payload = json.dumps(
                {
                    "op": "msg",
                    "msg_id": next_msg_id(),
                    "from": sender.session_id,
                    "from_name": from_name,
                    "channel": channel,
                    "text": text,
                    "ts": utc_now(),
                }
            )
            for session_id in subscribers:
                if session_id == sender.session_id:
                    continue
                conn = self.registry.get(session_id)
                if conn is not None:
                    await conn.ws.send(payload)

    async def _route_channels(self, sender: Conn, msg: dict[str, object]) -> None:
        del msg
        if sender.role != "control":
            await self.send_error(sender.ws, ErrorCode.BAD_ROLE, "channels requires control role")
            return
        async with self._lock:
            result: list[dict[str, object]] = []
            for channel in sorted(self.channels):
                subscriber_ids = sorted(self.channels[channel])
                names = sorted(
                    self.registry[sid].name for sid in subscriber_ids if sid in self.registry
                )
                result.append({"name": channel, "subscribers": names})
            await sender.ws.send(json.dumps({"op": "channels_ok", "channels": result}))


def _is_websocket_upgrade(request: Request) -> bool:
    """Return True when ``request`` carries a valid WebSocket upgrade."""
    connection = [
        token.strip().lower()
        for value in request.headers.get_all("Connection")
        for token in value.split(",")
    ]
    if "upgrade" not in connection:
        return False
    upgrade = [value.strip().lower() for value in request.headers.get_all("Upgrade")]
    return upgrade == ["websocket"]


async def _process_request(connection: ServerConnection, request: Request) -> Response | None:
    """Serve a friendly HTTP response for non-WebSocket requests.

    Plain HTTP probes (e.g. ``curl http://host:port``) would otherwise make
    the underlying library raise ``InvalidUpgrade`` and log a noisy traceback.
    Returning a ``Response`` short-circuits the handshake before that happens
    and keeps the server log quiet. WebSocket upgrades fall through to the
    normal handshake by returning ``None``.
    """
    if _is_websocket_upgrade(request):
        return None
    headers = websockets.datastructures.Headers()
    headers["Upgrade"] = "websocket"
    headers["Content-Type"] = "text/plain; charset=utf-8"
    body = b"This is an inter-agent WebSocket server.\n" b"Use a WebSocket client to connect.\n"
    return Response(
        http.HTTPStatus.UPGRADE_REQUIRED,
        http.HTTPStatus.UPGRADE_REQUIRED.phrase,
        headers,
        body,
    )


async def run_server(
    host: str,
    port: int,
    limits: Limits | None = None,
    idle_timeout_s: float | None = DEFAULT_IDLE_TIMEOUT_S,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
    tls_key_path: Path | None = None,
) -> None:
    """Start the core WebSocket bus until the task is cancelled."""
    server = BusServer(host=host, port=port, limits=limits, idle_timeout_s=idle_timeout_s)
    ssl_context = None
    if tls:
        if data_dir is None:
            raise TlsConfigError("TLS server startup requires a data directory")
        ssl_context = build_server_ssl_context(
            data_dir,
            host,
            tls_cert_path,
            tls_key_path,
        )
    print(f"Starting inter-agent-server on {'wss' if tls else 'ws'}://{host}:{port}...")

    def _request_shutdown() -> None:
        print("\nShutting down inter-agent-server...")
        server.shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except (NotImplementedError, ValueError):
            pass  # Signal not supported on this platform

    try:
        async with websockets.serve(
            server.handle,
            host=host,
            port=port,
            max_size=server.limits.frame_max,
            process_request=_process_request,
            ssl=ssl_context,
        ):
            if not server.registry:
                server._schedule_idle_timer()
            await server.shutdown_event.wait()
            server._cancel_idle_timer()
            await server.close_connections()
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, ValueError):
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-server")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--tls", dest="tls", action="store_true", default=None)
    parser.add_argument("--no-tls", dest="tls", action="store_false")
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=None,
        help="shut down after N seconds with no connections (default: disabled; 0 disables)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    endpoint = resolve_endpoint(
        args.host,
        args.port,
        tls=args.tls,
        tls_cert_path=args.tls_cert,
        tls_key_path=args.tls_key,
    )
    try:
        asyncio.run(
            run_server(
                endpoint.host,
                endpoint.port,
                idle_timeout_s=args.idle_timeout,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
                tls_key_path=endpoint.tls_key_path,
            )
        )
    except TlsConfigError as exc:
        raise SystemExit(f"could not start inter-agent-server TLS: {exc}") from exc
    except OSError as exc:
        message = f"could not start inter-agent-server on {endpoint.host}:{endpoint.port}: {exc}"
        raise SystemExit(message) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
