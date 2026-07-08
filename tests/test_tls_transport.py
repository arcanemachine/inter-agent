from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from pathlib import Path

import pytest
import websockets

from inter_agent.core.client import iter_client_frames
from inter_agent.core.list import list_sessions
from inter_agent.core.server import run_server
from inter_agent.core.shared import resolve_shared_secret
from inter_agent.core.status import check_server_status
from inter_agent.core.tls import build_client_ssl_context, default_cert_path, default_key_path

HOST = "127.0.0.1"


@pytest.mark.asyncio
async def test_tls_server_generates_material_and_accepts_wss_clients(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    resolve_shared_secret()
    task = asyncio.create_task(run_server(HOST, unused_tcp_port, tls=True, data_dir=tmp_path))
    await asyncio.sleep(0.2)
    try:
        frames = iter_client_frames(
            HOST,
            unused_tcp_port,
            "tls-agent",
            tls=True,
            data_dir=tmp_path,
        )
        welcome = await anext(frames)
        assert '"op": "welcome"' in welcome

        listed = await list_sessions(
            HOST,
            unused_tcp_port,
            tls=True,
            data_dir=tmp_path,
        )
        assert [session.name for session in listed.sessions] == ["tls-agent"]
        await frames.aclose()

        assert default_cert_path(tmp_path).exists()
        assert default_key_path(tmp_path).exists()
        if os.name == "posix":
            assert default_cert_path(tmp_path).stat().st_mode & 0o777 == 0o600
            assert default_key_path(tmp_path).stat().st_mode & 0o777 == 0o600
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_plain_ws_client_cannot_handshake_with_tls_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    resolve_shared_secret()
    task = asyncio.create_task(run_server(HOST, unused_tcp_port, tls=True, data_dir=tmp_path))
    await asyncio.sleep(0.2)
    try:
        with pytest.raises((OSError, websockets.WebSocketException)):
            async with websockets.connect(f"ws://{HOST}:{unused_tcp_port}"):
                pass
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_status_reports_tls_certificate_setup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    status = await check_server_status(
        HOST,
        unused_tcp_port,
        timeout=0.1,
        tls=True,
        data_dir=tmp_path,
    )

    assert status.state == "unavailable"
    assert status.reachable is False
    assert status.message.startswith("TLS configuration failed:")


def test_client_ssl_context_trusts_generated_certificate(
    tmp_path: Path,
) -> None:
    cert = default_cert_path(tmp_path)
    key = default_key_path(tmp_path)
    from inter_agent.core.tls import ensure_tls_material

    ensure_tls_material(tmp_path, HOST)

    context = build_client_ssl_context(tmp_path)

    assert cert.exists()
    assert key.exists()
    assert context.check_hostname is False
