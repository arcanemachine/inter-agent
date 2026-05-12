from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass

import websockets
from websockets.asyncio.server import ServerConnection

from inter_agent.core.errors import ErrorCode
from inter_agent.core.router import RouterMiddleware
from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    Limits,
    ServerAlreadyRunningError,
    claim_server_state,
    load_or_create_token,
    next_msg_id,
    remove_server_state,
    utc_now,
    validate_name,
)


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
    def __init__(self, host: str, port: int, limits: Limits | None = None) -> None:
        self.host = host
        self.port = port
        self.token = load_or_create_token()
        self.limits = limits or Limits()
        self.registry: dict[str, Conn] = {}
        self.middlewares: list[RouterMiddleware] = []
        self.shutdown_event = asyncio.Event()

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
        try:
            raw = await ws.recv()
            hello = await self.read_object(ws, raw, "first frame")
            if hello is None:
                return
            if hello.get("op") != "hello":
                await self.send_error(ws, ErrorCode.PROTOCOL_ERROR, "first op must be hello")
                return
            if hello.get("token") != self.token:
                await self.send_error(ws, ErrorCode.AUTH_FAILED, "invalid token")
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

            role = role_value
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

            raw_capabilities = hello.get("capabilities")
            if not isinstance(raw_capabilities, dict):
                await self.send_error(
                    ws, ErrorCode.PROTOCOL_ERROR, "capabilities must be an object"
                )
                return
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
                            "channels": False,
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
                elif op == "list":
                    sessions = [
                        {
                            "session_id": c.session_id,
                            "name": c.name,
                            "label": c.label,
                        }
                        for c in self.registry.values()
                        if c.role == "agent"
                    ]
                    await ws.send(json.dumps({"op": "list_ok", "sessions": sessions}))
                elif op == "send":
                    await self._route_send(conn, msg)
                elif op == "broadcast":
                    await self._route_broadcast(conn, msg)
                elif op == "custom":
                    await self._route_custom(conn, msg)
                else:
                    await self.send_error(ws, ErrorCode.UNKNOWN_OP, f"unsupported op: {op}")
        except websockets.ConnectionClosed:
            pass
        finally:
            if session_id and session_id in self.registry:
                self.registry.pop(session_id, None)

    async def _apply_middlewares(self, sender: Conn, msg: dict[str, object]) -> None:
        for middleware in self.middlewares:
            await middleware.before_route(sender.session_id, msg)

    async def _handle_shutdown(self, sender: Conn) -> None:
        if sender.role != "control":
            await self.send_error(sender.ws, ErrorCode.BAD_ROLE, "shutdown requires control role")
            return
        await sender.ws.send(json.dumps({"op": "shutdown_ok"}))
        self.shutdown_event.set()

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
        await target.ws.send(
            json.dumps(
                {
                    "op": "msg",
                    "msg_id": next_msg_id(),
                    "from": sender.session_id,
                    "from_name": sender.name,
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
        payload = json.dumps(
            {
                "op": "msg",
                "msg_id": next_msg_id(),
                "from": sender.session_id,
                "from_name": sender.name,
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
        payload = {
            "op": "msg",
            "msg_id": next_msg_id(),
            "from": sender.session_id,
            "from_name": sender.name,
            "custom_type": custom_type,
            "payload": msg.get("payload"),
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


async def run_server(host: str, port: int, limits: Limits | None = None) -> None:
    """Start the core WebSocket bus until the task is cancelled."""
    server = BusServer(host=host, port=port, limits=limits)
    identity = claim_server_state(host, port)
    try:
        async with websockets.serve(
            server.handle, host=host, port=port, max_size=server.limits.frame_max
        ):
            await server.shutdown_event.wait()
            await server.close_connections()
    finally:
        remove_server_state(host, port, identity.pid)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        asyncio.run(run_server(args.host, args.port))
    except ServerAlreadyRunningError as exc:
        raise SystemExit(str(exc)) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
