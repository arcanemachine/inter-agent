from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass

import websockets
from websockets.asyncio.server import ServerConnection

from inter_agent.core.router import RouterMiddleware
from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    Limits,
    load_or_create_token,
    next_msg_id,
    utc_now,
    validate_name,
    write_server_identity,
)


@dataclass
class Conn:
    ws: ServerConnection
    session_id: str
    name: str
    role: str
    capabilities: dict[str, object]


class BusServer:
    def __init__(self, host: str, port: int, limits: Limits | None = None) -> None:
        self.host = host
        self.port = port
        self.token = load_or_create_token()
        self.limits = limits or Limits()
        self.registry: dict[str, Conn] = {}
        self.middlewares: list[RouterMiddleware] = []

    async def send_error(self, ws: ServerConnection, code: str, message: str) -> None:
        await ws.send(json.dumps({"op": "error", "code": code, "message": message}))

    async def handle(self, ws: ServerConnection) -> None:
        session_id = None
        try:
            raw = await ws.recv()
            hello = json.loads(raw)
            if hello.get("op") != "hello":
                await self.send_error(ws, "PROTOCOL_ERROR", "first op must be hello")
                return
            if hello.get("token") != self.token:
                await self.send_error(ws, "AUTH_FAILED", "invalid token")
                return
            role = hello.get("role")
            session_id = hello.get("session_id")
            name = hello.get("name")
            if role not in {"agent", "control"}:
                await self.send_error(ws, "BAD_ROLE", "role must be agent or control")
                return
            if not session_id or not isinstance(session_id, str):
                await self.send_error(ws, "BAD_SESSION", "missing session_id")
                return
            if role == "agent":
                if not validate_name(name):
                    await self.send_error(ws, "BAD_NAME", "invalid name")
                    return
                if any(c.name == name for c in self.registry.values()):
                    await self.send_error(ws, "NAME_TAKEN", "name already in use")
                    return

            conn = Conn(
                ws=ws,
                session_id=session_id,
                name=name or f"control-{session_id[:6]}",
                role=role,
                capabilities=hello.get("capabilities") or {},
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
                msg = json.loads(frame)
                op = msg.get("op")
                if op == "ping":
                    await ws.send(json.dumps({"op": "pong"}))
                elif op == "bye":
                    return
                elif op == "list":
                    sessions = [
                        {
                            "session_id": c.session_id,
                            "name": c.name,
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
                    await self.send_error(ws, "UNKNOWN_OP", f"unsupported op: {op}")
        except websockets.ConnectionClosed:
            pass
        finally:
            if session_id and session_id in self.registry:
                self.registry.pop(session_id, None)

    async def _apply_middlewares(self, sender: Conn, msg: dict[str, object]) -> None:
        for middleware in self.middlewares:
            await middleware.before_route(sender.session_id, msg)

    async def _route_send(self, sender: Conn, msg: dict[str, object]) -> None:
        await self._apply_middlewares(sender, msg)
        to = msg.get("to")
        text = msg.get("text")
        if not isinstance(text, str):
            await self.send_error(sender.ws, "BAD_TEXT", "text must be a string")
            return
        if len(text.encode()) > self.limits.direct_text_max:
            await self.send_error(sender.ws, "TEXT_TOO_LARGE", "direct message too large")
            return
        target = next((c for c in self.registry.values() if c.name == to), None)
        if not target:
            await self.send_error(sender.ws, "UNKNOWN_TARGET", f"unknown target: {to}")
            return
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
            await self.send_error(sender.ws, "BAD_TEXT", "text must be a string")
            return
        if len(text.encode()) > self.limits.broadcast_text_max:
            await self.send_error(sender.ws, "TEXT_TOO_LARGE", "broadcast message too large")
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
            target = next((c for c in self.registry.values() if c.name == msg.get("to")), None)
            if not target:
                await self.send_error(
                    sender.ws, "UNKNOWN_TARGET", f"unknown target: {msg.get('to')}"
                )
                return
            payload["to"] = target.name
            await target.ws.send(json.dumps(payload))
            return
        for conn in self.registry.values():
            if conn.session_id == sender.session_id or conn.role != "agent":
                continue
            await conn.ws.send(json.dumps(payload))


async def run_server(host: str, port: int) -> None:
    server = BusServer(host=host, port=port)
    write_server_identity(host, port)
    async with websockets.serve(
        server.handle, host=host, port=port, max_size=server.limits.frame_max
    ):
        await asyncio.Future()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port))


if __name__ == "__main__":
    main()
