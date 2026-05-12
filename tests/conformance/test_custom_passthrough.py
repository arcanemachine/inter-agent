from __future__ import annotations

import json
from pathlib import Path

import pytest
import websockets
from helpers import connect_agent, recv_json, running_server


@pytest.mark.asyncio
async def test_custom_unknown_passthrough(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as a,
            websockets.connect(context.url) as b,
        ):
            await connect_agent(a, context, "a", "agent-a")
            await connect_agent(b, context, "b", "agent-b")

            await a.send(
                json.dumps(
                    {
                        "op": "custom",
                        "custom_type": "x.unknown.v1",
                        "to": "agent-b",
                        "payload": {"k": "v"},
                    }
                )
            )
            msg = await recv_json(b)

    assert msg["op"] == "msg"
    assert msg["custom_type"] == "x.unknown.v1"
    assert msg["payload"] == {"k": "v"}
