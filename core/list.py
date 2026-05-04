from __future__ import annotations

import argparse
import asyncio
import json
import uuid

import websockets

from core.shared import (
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    asyncio.run(list_sessions(args.host, args.port))


if __name__ == "__main__":
    main()
