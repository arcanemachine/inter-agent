from __future__ import annotations

import json
from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, recv_json, running_server, send_json

from inter_agent.core.auth import build_auth_response, parse_auth_challenge
from inter_agent.core.errors import ErrorCode


def hello_client_nonce(hello: dict[str, object]) -> str:
    auth = hello["auth"]
    assert isinstance(auth, dict)
    nonce = auth["client_nonce"]
    assert isinstance(nonce, str)
    return nonce


@pytest.mark.asyncio
async def test_valid_challenge_response_connects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            hello = agent_hello(session_id="a", name="agent-a")
            await ws.send(json.dumps(hello))
            challenge = parse_auth_challenge(await recv_json(ws))
            await ws.send(
                json.dumps(
                    build_auth_response(
                        context.secret,
                        client_nonce=hello_client_nonce(hello),
                        server_nonce=challenge.server_nonce,
                        hello=hello,
                    )
                )
            )
            welcome = await recv_json(ws)

    assert welcome["op"] == "welcome"


@pytest.mark.asyncio
async def test_wrong_secret_fails_with_auth_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            hello = agent_hello(session_id="a", name="agent-a")
            await ws.send(json.dumps(hello))
            challenge = parse_auth_challenge(await recv_json(ws))
            await ws.send(
                json.dumps(
                    build_auth_response(
                        "wrong-secret",
                        client_nonce=hello_client_nonce(hello),
                        server_nonce=challenge.server_nonce,
                        hello=hello,
                    )
                )
            )
            err = await recv_json(ws)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "label,hello",
    [
        ("missing", {k: v for k, v in agent_hello().items() if k != "auth"}),
        ("bad_method", {**agent_hello(), "auth": {"method": "plain", "client_nonce": "abc"}}),
    ],
    ids=["missing", "bad_method"],
)
async def test_invalid_auth_hello_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    label: str,
    hello: dict[str, object],
) -> None:
    del label
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            err = await send_json(ws, hello)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value


@pytest.mark.asyncio
async def test_raw_hello_token_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            hello = agent_hello(session_id="a", name="agent-a")
            hello.pop("auth", None)
            hello["token"] = context.secret
            err = await send_json(ws, hello)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value
