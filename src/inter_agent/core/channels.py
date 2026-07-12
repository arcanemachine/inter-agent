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
class ChannelInfo:
    """Diagnostic information for a single pub/sub channel."""

    name: str
    subscribers: tuple[str, ...]


@dataclass(frozen=True)
class ChannelsResult:
    """Structured channels command result plus the raw protocol response."""

    raw_response: str
    response: dict[str, object]
    channels: tuple[ChannelInfo, ...]


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _json_object(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server response must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def _parse_channels(response: dict[str, object]) -> tuple[ChannelInfo, ...]:
    channels = response.get("channels")
    if not isinstance(channels, list):
        raise ValueError("channels response must include channels")

    result: list[ChannelInfo] = []
    for entry in channels:
        if not isinstance(entry, dict):
            raise ValueError("channels entries must be objects")
        name = entry.get("name")
        subscribers = entry.get("subscribers")
        if not isinstance(name, str):
            raise ValueError("channels entries must include string name")
        if not isinstance(subscribers, list):
            raise ValueError("channels entries must include subscribers list")
        parsed_subscribers: list[str] = []
        for subscriber in subscribers:
            if not isinstance(subscriber, str):
                raise ValueError("channel subscribers must be strings")
            parsed_subscribers.append(subscriber)
        result.append(ChannelInfo(name=name, subscribers=tuple(parsed_subscribers)))
    return tuple(result)


async def list_channels(
    host: str,
    port: int,
    *,
    tls: bool = False,
    data_dir: Path | None = None,
    tls_cert_path: Path | None = None,
) -> ChannelsResult:
    """Return pub/sub channel diagnostics through a control connection."""
    secret = resolve_shared_secret().secret
    ssl_context = client_ssl_context(tls, data_dir, tls_cert_path)
    async with websockets.connect(websocket_uri(host, port, tls), ssl=ssl_context) as ws:
        try:
            _ = await client_handshake(ws, secret, control_hello(f"ctl-{uuid.uuid4()}"))
        except AuthError as exc:
            raise SystemExit(str(exc)) from exc
        except (AuthProtocolError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SystemExit(f"server protocol mismatch: {exc}") from exc
        await ws.send(json.dumps({"op": "channels"}))
        raw_response = _text_frame(await ws.recv())
        response = _json_object(raw_response)
        channels = _parse_channels(response) if response.get("op") == "channels_ok" else ()
        return ChannelsResult(
            raw_response=raw_response,
            response=response,
            channels=channels,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-channels")
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
        list_channels(
            endpoint.host,
            endpoint.port,
            tls=endpoint.tls,
            data_dir=endpoint.data_dir,
            tls_cert_path=endpoint.tls_cert_path,
        )
    )
    print(result.raw_response)
    return 0 if result.response.get("op") == "channels_ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
