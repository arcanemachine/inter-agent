from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Sequence

import websockets

from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    control_hello,
    load_or_create_token,
    verify_server_identity,
)


async def list_sessions(host: str, port: int) -> None:
    if not verify_server_identity(host, port):
        raise SystemExit("server identity check failed")
    token = load_or_create_token()
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(json.dumps(control_hello(token, f"ctl-{uuid.uuid4()}")))
        _ = await ws.recv()
        await ws.send(json.dumps({"op": "list"}))
        print(await ws.recv())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-list")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    asyncio.run(list_sessions(args.host, args.port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
