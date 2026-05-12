from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from collections.abc import AsyncGenerator, Sequence
from typing import TextIO

import websockets

from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    load_or_create_token,
    verify_server_identity,
)


def build_hello(
    token: str, session_id: str, name: str, label: str | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "op": "hello",
        "token": token,
        "role": "agent",
        "session_id": session_id,
        "name": name,
        "capabilities": {},
    }
    if label is not None:
        payload["label"] = label
    return payload


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


async def iter_client_frames(
    host: str,
    port: int,
    name: str,
    label: str | None = None,
) -> AsyncGenerator[str, None]:
    """Connect an agent session and yield raw server JSON frames.

    The first yielded frame is the server welcome response. Subsequent frames are
    peer messages or protocol responses received for the connected session.
    """
    if not verify_server_identity(host, port):
        raise SystemExit("server identity check failed")
    token = load_or_create_token()
    session_id = os.getenv("INTER_AGENT_SESSION_ID", str(uuid.uuid4()))
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(json.dumps(build_hello(token, session_id, name, label)))
        yield _text_frame(await ws.recv())
        async for msg in ws:
            yield _text_frame(msg)


async def run_client(
    host: str,
    port: int,
    name: str,
    label: str | None = None,
    output: TextIO | None = None,
) -> None:
    """Run the connect command behavior using typed inputs instead of argv."""
    stream = output or sys.stdout
    async for msg in iter_client_frames(host, port, name, label):
        print(msg, file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-connect")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--name", dest="name_option")
    parser.add_argument("--label")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    name = args.name_option or args.name
    if not name:
        parser.error("name is required")
    asyncio.run(run_client(args.host, args.port, name, args.label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
