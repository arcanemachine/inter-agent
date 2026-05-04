from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid

import websockets

from core.shared import DEFAULT_HOST, DEFAULT_PORT, load_or_create_token, verify_server_identity


async def send_message(host: str, port: int, to: str | None, text: str | None, custom_type: str | None, payload: str | None) -> None:
    if not verify_server_identity(host, port):
        raise SystemExit("server identity check failed")
    token = load_or_create_token()
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(
            json.dumps(
                {
                    "op": "hello",
                    "token": token,
                    "role": "control",
                    "session_id": f"ctl-{uuid.uuid4()}",
                    "name": "control",
                    "capabilities": {},
                }
            )
        )
        print(await ws.recv())
        if custom_type:
            msg = {"op": "custom", "custom_type": custom_type, "payload": json.loads(payload or "{}")}
            if to:
                msg["to"] = to
            await ws.send(json.dumps(msg))
        elif to:
            await ws.send(json.dumps({"op": "send", "to": to, "text": text or ""}))
        else:
            await ws.send(json.dumps({"op": "broadcast", "text": text or ""}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--to")
    parser.add_argument("--text")
    parser.add_argument("--custom-type")
    parser.add_argument("--payload")
    args = parser.parse_args()
    asyncio.run(send_message(args.host, args.port, args.to, args.text, args.custom_type, args.payload))


if __name__ == "__main__":
    main()
