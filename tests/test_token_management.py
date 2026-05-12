from __future__ import annotations

import stat
from pathlib import Path
from typing import NoReturn

import pytest

import inter_agent.core.client as core_client
import inter_agent.core.list as core_list
import inter_agent.core.send as core_send
import inter_agent.core.shutdown as core_shutdown
from inter_agent.core.shared import load_or_create_token, token_path

HOST = "127.0.0.1"


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_token_is_created_once_with_restrictive_permissions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    token = load_or_create_token()
    reused = load_or_create_token()

    assert token
    assert reused == token
    assert token_path().read_text(encoding="utf-8") == token + "\n"
    assert file_mode(token_path()) == 0o600
    assert file_mode(tmp_path) == 0o700


def test_existing_token_permissions_are_tightened(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    path = token_path()
    path.write_text("existing-token\n", encoding="utf-8")
    path.chmod(0o644)

    token = load_or_create_token()

    assert token == "existing-token"
    assert file_mode(path) == 0o600


def fail_if_loaded() -> NoReturn:
    raise AssertionError("token loaded before identity verification")


@pytest.mark.asyncio
async def test_send_does_not_load_token_without_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(core_send, "load_or_create_token", fail_if_loaded)

    with pytest.raises(SystemExit, match="server identity check failed"):
        await core_send.send_direct_message(HOST, unused_tcp_port, "agent-b", "hello")


@pytest.mark.asyncio
async def test_list_does_not_load_token_without_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(core_list, "load_or_create_token", fail_if_loaded)

    with pytest.raises(SystemExit, match="server identity check failed"):
        await core_list.list_sessions(HOST, unused_tcp_port)


@pytest.mark.asyncio
async def test_shutdown_does_not_load_token_without_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(core_shutdown, "load_or_create_token", fail_if_loaded)

    with pytest.raises(SystemExit, match="server identity check failed"):
        await core_shutdown.shutdown_server(HOST, unused_tcp_port)


@pytest.mark.asyncio
async def test_connect_does_not_load_token_without_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(core_client, "load_or_create_token", fail_if_loaded)

    frames = core_client.iter_client_frames(HOST, unused_tcp_port, "agent-a")
    with pytest.raises(SystemExit, match="server identity check failed"):
        await anext(frames)
