from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import websockets

from inter_agent.core.auth import AuthError, AuthProtocolError, client_handshake
from inter_agent.core.shared import control_hello, resolve_endpoint, resolve_shared_secret
from inter_agent.core.transport import client_ssl_context, websocket_uri


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


async def list_sessions(
    host: str,
    port: int,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> ListResult:
    """Return connected agent sessions through a control connection."""
    secret = resolve_shared_secret().secret
    ssl_context = client_ssl_context(tls, data_dir, tls_cert_path)
    async with websockets.connect(websocket_uri(host, port, tls), ssl=ssl_context) as ws:
        try:
            _ = await client_handshake(ws, secret, control_hello(f"ctl-{uuid.uuid4()}"))
        except AuthError as exc:
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
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
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--tls", dest="tls", action="store_true", default=None)
    parser.add_argument("--no-tls", dest="tls", action="store_false")
    parser.add_argument("--tls-cert")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    endpoint = resolve_endpoint(
        args.host, args.port, allow_discovery=True, tls=args.tls, tls_cert_path=args.tls_cert
    )
    result = asyncio.run(
        list_sessions(
            endpoint.host,
            endpoint.port,
            tls=endpoint.tls,
            data_dir=endpoint.data_dir,
            tls_cert_path=endpoint.tls_cert_path,
        )
    )
    print(result.raw_response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
