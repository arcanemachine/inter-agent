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


async def send_message(
    host: str,
    port: int,
    to: str | None,
    text: str | None,
    custom_type: str | None,
    payload: str | None,
) -> None:
    if not verify_server_identity(host, port):
        raise SystemExit("server identity check failed")
    token = load_or_create_token()
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(json.dumps(control_hello(token, f"ctl-{uuid.uuid4()}")))
        print(await ws.recv())
        if custom_type:
            msg: dict[str, object] = {
                "op": "custom",
                "custom_type": custom_type,
                "payload": json.loads(payload or "{}"),
            }
            if to:
                msg["to"] = to
            await ws.send(json.dumps(msg))
        elif to:
            await ws.send(json.dumps({"op": "send", "to": to, "text": text or ""}))
        else:
            await ws.send(json.dumps({"op": "broadcast", "text": text or ""}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-send")
    parser.add_argument("to", nargs="?")
    parser.add_argument("text", nargs="?")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--to", dest="to_option")
    parser.add_argument("--text", dest="text_option")
    parser.add_argument("--custom-type")
    parser.add_argument("--payload")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    to = args.to_option or args.to
    text = args.text_option if args.text_option is not None else args.text
    asyncio.run(send_message(args.host, args.port, to, text, args.custom_type, args.payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
