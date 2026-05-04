import asyncio
import json

import pytest
import websockets

from core.server import run_server
from core.shared import load_or_create_token


@pytest.mark.asyncio
async def test_custom_unknown_passthrough(monkeypatch, tmp_path):
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", 9782

    task = asyncio.create_task(run_server(host, port))
    await asyncio.sleep(0.1)

    try:
        async with websockets.connect(f"ws://{host}:{port}") as a, websockets.connect(f"ws://{host}:{port}") as b:
            await a.send(json.dumps({"op": "hello", "token": token, "role": "agent", "session_id": "a", "name": "agent-a", "capabilities": {}}))
            await b.send(json.dumps({"op": "hello", "token": token, "role": "agent", "session_id": "b", "name": "agent-b", "capabilities": {}}))
            await a.recv()
            await b.recv()

            await a.send(json.dumps({
                "op": "custom",
                "custom_type": "x.unknown.v1",
                "to": "agent-b",
                "payload": {"k": "v"},
            }))
            msg = json.loads(await b.recv())
            assert msg["op"] == "msg"
            assert msg["custom_type"] == "x.unknown.v1"
            assert msg["payload"] == {"k": "v"}
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
