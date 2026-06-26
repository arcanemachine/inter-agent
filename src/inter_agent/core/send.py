from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

import websockets
from websockets.asyncio.client import ClientConnection

from inter_agent.core.auth import AuthError, AuthProtocolError, client_handshake
from inter_agent.core.shared import control_hello, resolve_endpoint, resolve_shared_secret


@dataclass(frozen=True)
class ProtocolErrorResult:
    """Protocol error received after sending an outbound payload."""

    code: str
    message: str
    raw: str


@dataclass(frozen=True)
class SendResult:
    """Result returned after a command connection sends one outbound payload."""

    welcome: str
    welcome_payload: dict[str, object]
    error: ProtocolErrorResult | None = None


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


def parse_custom_payload(payload: str | None) -> object:
    """Parse a CLI custom payload string into a JSON-compatible value."""
    if payload is None:
        return {}
    parsed: object = json.loads(payload)
    return parsed


async def _recv_protocol_error(ws: ClientConnection, timeout: float) -> ProtocolErrorResult | None:
    try:
        raw = _text_frame(await asyncio.wait_for(ws.recv(), timeout=timeout))
    except TimeoutError:
        return None

    response = _json_object(raw)
    return _protocol_error_from_payload(raw, response)


async def send_message(
    host: str,
    port: int,
    to: str | None,
    text: str | None,
    custom_type: str | None,
    payload: object | None,
    from_name: str | None = None,
    response_timeout: float = 0.1,
) -> SendResult:
    """Send a direct, broadcast, or custom message through a control connection."""
    secret = resolve_shared_secret().secret
    async with websockets.connect(f"ws://{host}:{port}") as ws:
        try:
            welcome = await client_handshake(ws, secret, control_hello(f"ctl-{uuid.uuid4()}"))
        except AuthError as exc:
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
        welcome_payload = _json_object(welcome)
        welcome_error = _protocol_error_from_payload(welcome, welcome_payload)
        if welcome_error is not None:
            return SendResult(welcome=welcome, welcome_payload=welcome_payload, error=welcome_error)
        if custom_type is not None:
            msg: dict[str, object] = {
                "op": "custom",
                "custom_type": custom_type,
                "payload": {} if payload is None else payload,
            }
            if to:
                msg["to"] = to
            if from_name:
                msg["from_name"] = from_name
            await ws.send(json.dumps(msg))
        elif to:
            outbound: dict[str, object] = {"op": "send", "to": to, "text": text or ""}
            if from_name:
                outbound["from_name"] = from_name
            await ws.send(json.dumps(outbound))
        else:
            outbound = {"op": "broadcast", "text": text or ""}
            if from_name:
                outbound["from_name"] = from_name
            await ws.send(json.dumps(outbound))
        return SendResult(
            welcome=welcome,
            welcome_payload=welcome_payload,
            error=await _recv_protocol_error(ws, response_timeout),
        )


async def send_direct_message(
    host: str, port: int, to: str, text: str, from_name: str | None = None
) -> SendResult:
    """Send a direct text message to one routing name."""
    return await send_message(
        host, port, to, text, custom_type=None, payload=None, from_name=from_name
    )


async def broadcast_message(
    host: str, port: int, text: str, from_name: str | None = None
) -> SendResult:
    """Broadcast a text message to all other connected agent sessions."""
    return await send_message(
        host, port, to=None, text=text, custom_type=None, payload=None, from_name=from_name
    )


async def send_custom_message(
    host: str,
    port: int,
    to: str | None,
    custom_type: str,
    payload: object,
) -> SendResult:
    """Send a custom protocol envelope through a control connection."""
    return await send_message(host, port, to, text=None, custom_type=custom_type, payload=payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-send")
    parser.add_argument("to", nargs="?")
    parser.add_argument("text", nargs="?")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--to", dest="to_option")
    parser.add_argument("--text", dest="text_option")
    parser.add_argument("--custom-type")
    parser.add_argument("--payload")
    parser.add_argument("--from", dest="from_name")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    to = args.to_option or args.to
    text = args.text_option if args.text_option is not None else args.text
    payload = parse_custom_payload(args.payload) if args.custom_type is not None else None
    endpoint = resolve_endpoint(args.host, args.port, allow_discovery=True)
    result = asyncio.run(
        send_message(
            endpoint.host, endpoint.port, to, text, args.custom_type, payload, args.from_name
        )
    )
    if result.error is not None:
        print(
            f"inter-agent: delivery failed ({result.error.code}): {result.error.message}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
