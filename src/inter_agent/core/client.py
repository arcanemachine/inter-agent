from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from collections.abc import AsyncGenerator, Sequence
from pathlib import Path
from typing import TextIO

import websockets

from inter_agent.core.auth import AuthError, AuthProtocolError, client_handshake
from inter_agent.core.auth import build_hello as build_auth_hello
from inter_agent.core.shared import resolve_endpoint, resolve_shared_secret
from inter_agent.core.transport import client_ssl_context, websocket_uri


def build_hello(
    session_id: str, name: str, label: str | None = None, client_nonce: str | None = None
) -> dict[str, object]:
    return build_auth_hello(
        role="agent",
        session_id=session_id,
        name=name,
        label=label,
        capabilities={},
        client_nonce=client_nonce,
    )


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


async def iter_client_frames(
    host: str,
    port: int,
    name: str,
    label: str | None = None,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> AsyncGenerator[str, None]:
    """Connect an agent session and yield raw server JSON frames.

    The first yielded frame is the server welcome response. Subsequent frames are
    peer messages or protocol responses received for the connected session.
    """
    secret = resolve_shared_secret().secret
    session_id = os.getenv("INTER_AGENT_SESSION_ID", str(uuid.uuid4()))
    hello = build_hello(session_id, name, label)
    ssl_context = client_ssl_context(tls, data_dir, tls_cert_path)
    async with websockets.connect(websocket_uri(host, port, tls), ssl=ssl_context) as ws:
        try:
            yield await client_handshake(ws, secret, hello)
        except AuthError as exc:
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
        async for msg in ws:
            yield _text_frame(msg)


async def run_client(
    host: str,
    port: int,
    name: str,
    label: str | None = None,
    output: TextIO | None = None,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> None:
    """Run the connect command behavior using typed inputs instead of argv."""
    stream = output or sys.stdout
    async for msg in iter_client_frames(
        host, port, name, label, tls=tls, data_dir=data_dir, tls_cert_path=tls_cert_path
    ):
        print(msg, file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-connect")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--name", dest="name_option")
    parser.add_argument("--label")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--tls", dest="tls", action="store_true", default=None)
    parser.add_argument("--no-tls", dest="tls", action="store_false")
    parser.add_argument("--tls-cert")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    name = args.name_option or args.name
    if not name:
        parser.error("name is required")
    endpoint = resolve_endpoint(
        args.host, args.port, allow_discovery=True, tls=args.tls, tls_cert_path=args.tls_cert
    )
    asyncio.run(
        run_client(
            endpoint.host,
            endpoint.port,
            name,
            args.label,
            tls=endpoint.tls,
            data_dir=endpoint.data_dir,
            tls_cert_path=endpoint.tls_cert_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
