from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

import websockets
from websockets.asyncio.client import ClientConnection

from inter_agent.core.auth import AuthError, AuthProtocolError, client_handshake
from inter_agent.core.send import ProtocolErrorResult, SendResult
from inter_agent.core.shared import (
    Limits,
    control_hello,
    resolve_endpoint,
    resolve_shared_secret,
    validate_channel_name,
)
from inter_agent.core.transport import client_ssl_context, websocket_uri


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _json_object(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server response must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def _protocol_error_from_payload(
    raw: str, payload: dict[str, object]
) -> ProtocolErrorResult | None:
    if payload.get("op") != "error":
        return None
    code = payload.get("code")
    message = payload.get("message")
    return ProtocolErrorResult(
        code=code if isinstance(code, str) else "PROTOCOL_ERROR",
        message=message if isinstance(message, str) else "protocol error",
        raw=raw,
    )


async def _recv_protocol_error(ws: ClientConnection, timeout: float) -> ProtocolErrorResult | None:
    try:
        raw = _text_frame(await asyncio.wait_for(ws.recv(), timeout=timeout))
    except TimeoutError:
        return None

    response = _json_object(raw)
    return _protocol_error_from_payload(raw, response)


async def publish_to_channel(
    host: str,
    port: int,
    channel: str,
    text: str,
    from_name: str | None = None,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> SendResult:
    """Publish a text message to a channel through a control connection."""
    if not validate_channel_name(channel, Limits().channel_name_max):
        raise ValueError(f"invalid channel name: {channel!r}")
    secret = resolve_shared_secret().secret
    ssl_context = client_ssl_context(tls, data_dir, tls_cert_path)
    async with websockets.connect(websocket_uri(host, port, tls), ssl=ssl_context) as ws:
        try:
            welcome = await client_handshake(ws, secret, control_hello(f"pub-{uuid.uuid4()}"))
        except AuthError as exc:
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
        welcome_payload = _json_object(welcome)
        welcome_error = _protocol_error_from_payload(welcome, welcome_payload)
        if welcome_error is not None:
            return SendResult(welcome=welcome, welcome_payload=welcome_payload, error=welcome_error)
        outbound: dict[str, object] = {"op": "publish", "channel": channel, "text": text}
        if from_name:
            outbound["from_name"] = from_name
        await ws.send(json.dumps(outbound))
        return SendResult(
            welcome=welcome,
            welcome_payload=welcome_payload,
            error=await _recv_protocol_error(ws, 0.1),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-publish")
    parser.add_argument("channel")
    parser.add_argument("text")
    parser.add_argument("--from", dest="from_name")
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
    try:
        result = asyncio.run(
            publish_to_channel(
                endpoint.host,
                endpoint.port,
                args.channel,
                args.text,
                args.from_name,
                tls=endpoint.tls,
                data_dir=endpoint.data_dir,
                tls_cert_path=endpoint.tls_cert_path,
            )
        )
    except ValueError as exc:
        print(f"inter-agent: {exc}", file=sys.stderr)
        return 1
    if result.error is not None:
        print(
            f"inter-agent: publish failed ({result.error.code}): {result.error.message}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
