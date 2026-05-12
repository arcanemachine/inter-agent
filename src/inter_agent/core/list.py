from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

import websockets

from inter_agent.core.shared import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    control_hello,
    load_or_create_token,
    verify_server_identity,
)


@dataclass(frozen=True)
class SessionInfo:
    """Agent session returned by the core list operation."""

    session_id: str
    name: str
    label: str | None


@dataclass(frozen=True)
class ListResult:
    """Structured list command result plus the raw protocol response."""

    raw_response: str
    response: dict[str, object]
    sessions: tuple[SessionInfo, ...]


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _json_object(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server response must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def _parse_sessions(response: dict[str, object]) -> tuple[SessionInfo, ...]:
    sessions = response.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError("list response must include sessions")

    result: list[SessionInfo] = []
    for entry in sessions:
        if not isinstance(entry, dict):
            raise ValueError("list sessions must be objects")
        session_id = entry.get("session_id")
        name = entry.get("name")
        label = entry.get("label")
        if not isinstance(session_id, str) or not isinstance(name, str):
            raise ValueError("list sessions must include string session_id and name")
        if label is not None and not isinstance(label, str):
            raise ValueError("list session label must be a string or null")
        result.append(SessionInfo(session_id=session_id, name=name, label=label))
    return tuple(result)


async def list_sessions(host: str, port: int) -> ListResult:
    """Return connected agent sessions through a control connection."""
    if not verify_server_identity(host, port):
        raise SystemExit("server identity check failed")
    token = load_or_create_token()
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(json.dumps(control_hello(token, f"ctl-{uuid.uuid4()}")))
        _ = await ws.recv()
        await ws.send(json.dumps({"op": "list"}))
        raw_response = _text_frame(await ws.recv())
        response = _json_object(raw_response)
        return ListResult(
            raw_response=raw_response,
            response=response,
            sessions=_parse_sessions(response),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-list")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = asyncio.run(list_sessions(args.host, args.port))
    print(result.raw_response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
