from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from collections.abc import Sequence

import websockets

from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    load_or_create_token,
    verify_server_identity,
)


def build_hello(token: str, session_id: str, name: str) -> dict[str, object]:
    return {
        "op": "hello",
        "token": token,
        "role": "agent",
        "session_id": session_id,
        "name": name,
        "capabilities": {},
    }


async def run_client(host: str, port: int, name: str) -> None:
    if not verify_server_identity(host, port):
        raise SystemExit("server identity check failed")
    token = load_or_create_token()
    session_id = os.getenv("INTER_AGENT_SESSION_ID", str(uuid.uuid4()))
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(json.dumps(build_hello(token, session_id, name)))
        print(await ws.recv())
        async for msg in ws:
            print(msg)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-connect")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--name", dest="name_option")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    name = args.name_option or args.name
    if not name:
        parser.error("name is required")
    asyncio.run(run_client(args.host, args.port, name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
