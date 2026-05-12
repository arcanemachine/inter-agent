from __future__ import annotations

import json

import pytest

import inter_agent.core.client as core_client
import inter_agent.core.list as core_list
import inter_agent.core.send as core_send
from inter_agent.adapters.pi import commands
from inter_agent.adapters.pi.cli import main
from inter_agent.core.list import ListResult
from inter_agent.core.send import SendResult


def test_status_outputs_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["status"])
    assert code == 0
    assert json.loads(capsys.readouterr().out) == {
        "core_list_supported": True,
        "adapter_list_exposed": True,
    }


def test_send_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str, str]] = []

    async def fake_send(host: str, port: int, to: str, text: str) -> SendResult:
        calls.append((host, port, to, text))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "send_direct_message", fake_send)

    code = commands.send("agent-b", "hello")

    assert code == 0
    assert calls == [("127.0.0.1", 9473, "agent-b", "hello")]
    assert capsys.readouterr().out == '{"op": "welcome"}\n'


def test_broadcast_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int, str]] = []

    async def fake_broadcast(host: str, port: int, text: str) -> SendResult:
        calls.append((host, port, text))
        return SendResult(welcome='{"op": "welcome"}', welcome_payload={"op": "welcome"})

    monkeypatch.setattr(core_send, "broadcast_message", fake_broadcast)

    code = commands.broadcast("hello all")

    assert code == 0
    assert calls == [("127.0.0.1", 9473, "hello all")]
    assert capsys.readouterr().out == '{"op": "welcome"}\n'


def test_list_uses_core_api(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, int]] = []

    async def fake_list(host: str, port: int) -> ListResult:
        calls.append((host, port))
        return ListResult(
            raw_response='{"op": "list_ok", "sessions": []}',
            response={"op": "list_ok", "sessions": []},
            sessions=(),
        )

    monkeypatch.setattr(core_list, "list_sessions", fake_list)

    code = commands.list_sessions()

    assert code == 0
    assert calls == [("127.0.0.1", 9473)]
    assert capsys.readouterr().out == '{"op": "list_ok", "sessions": []}\n'


def test_connect_uses_core_api(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, str, str | None]] = []

    async def fake_connect(host: str, port: int, name: str, label: str | None = None) -> None:
        calls.append((host, port, name, label))

    monkeypatch.setattr(core_client, "run_client", fake_connect)

    code = commands.connect("agent-a", "Agent A")

    assert code == 0
    assert calls == [("127.0.0.1", 9473, "agent-a", "Agent A")]
