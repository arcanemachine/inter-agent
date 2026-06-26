from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

import websockets

from inter_agent.core.auth import AuthError, AuthProtocolError, client_handshake
from inter_agent.core.shared import control_hello, resolve_endpoint, resolve_shared_secret


@dataclass(frozen=True)
class ShutdownResult:
    """Result returned after requesting server shutdown."""

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


async def shutdown_server(host: str, port: int) -> ShutdownResult:
    """Request authenticated shutdown through a control connection."""
    secret = resolve_shared_secret().secret
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        try:
            _ = await client_handshake(ws, secret, control_hello(f"shutdown-{uuid.uuid4()}"))
        except AuthError as exc:
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
        await ws.send(json.dumps({"op": "shutdown"}))
        response = _text_frame(await ws.recv())
        return ShutdownResult(response=response, response_payload=_json_object(response))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-shutdown")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    endpoint = resolve_endpoint(args.host, args.port, allow_discovery=True)
    result = asyncio.run(shutdown_server(endpoint.host, endpoint.port))
    print(result.response)
    return 0 if result.response_payload.get("op") == "shutdown_ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
