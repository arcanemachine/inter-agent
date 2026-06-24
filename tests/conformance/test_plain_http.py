from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from helpers import running_server


async def _plain_http_get(host: str, port: int, path: str = "/") -> tuple[int, str, bytes]:
    """Perform a raw HTTP/1.1 GET without WebSocket upgrade headers."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        request = (
            f"GET {path} HTTP/1.1\r\n" f"Host: {host}:{port}\r\n" f"Connection: close\r\n" f"\r\n"
        )
        writer.write(request.encode())
        await writer.drain()
        raw = await reader.read()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError):
            pass

    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode()
    status_code = int(status_line.split(" ")[1])
    return status_code, status_line, body


@pytest.mark.asyncio
async def test_plain_http_request_returns_upgrade_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    """A plain HTTP probe (no WebSocket upgrade) gets a clean 426 response.

    The server must not raise an unhandled handshake exception; it should
    reply with a friendly HTTP response instead.
    """
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        status_code, _status_line, body = await _plain_http_get(context.host, context.port)

    assert status_code == 426
    assert b"WebSocket" in body
