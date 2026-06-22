from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

import websockets

from inter_agent.core.shared import (
    control_hello,
    identity_failure_message,
    load_or_create_token,
    resolve_endpoint,
    verify_server_identity_details,
)


@dataclass(frozen=True)
class KickResult:
    """Result returned after requesting a session kick."""

    response: str
    response_payload: dict[str, object]


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _json_object(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server response must be a JSON object")
    return {str(key): value for key, value in payload.items()}


async def kick_session(
    host: str, port: int, *, name: str | None = None, session_id: str | None = None
) -> KickResult:
    """Force-disconnect a registered session through a control connection.

    Either ``name`` or ``session_id`` must be provided. ``name`` is unique for
    agent sessions because the server rejects duplicate agent names.
    """
    if not name and not session_id:
        raise ValueError("kick requires a name or session_id")
    verification = verify_server_identity_details(host, port)
    if not verification.ok:
        raise SystemExit(identity_failure_message(verification.reason))
    token = load_or_create_token()
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await ws.send(json.dumps(control_hello(token, f"kick-{uuid.uuid4()}")))
        _ = await ws.recv()
        msg: dict[str, object] = {"op": "kick"}
        if name:
            msg["name"] = name
        if session_id:
            msg["session_id"] = session_id
        await ws.send(json.dumps(msg))
        response = _text_frame(await ws.recv())
        return KickResult(response=response, response_payload=_json_object(response))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-kick")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--name", dest="name_option")
    parser.add_argument("--session-id")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    name = args.name_option or args.name
    endpoint = resolve_endpoint(args.host, args.port, allow_discovery=True)
    result = asyncio.run(
        kick_session(endpoint.host, endpoint.port, name=name, session_id=args.session_id)
    )
    print(result.response)
    return 0 if result.response_payload.get("op") == "kick_ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
