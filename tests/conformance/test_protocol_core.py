import asyncio
import json

import pytest
import websockets

from core.server import run_server
from core.shared import load_or_create_token


@pytest.mark.asyncio
async def test_handshake_and_direct_and_broadcast(monkeypatch, tmp_path):
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    token = load_or_create_token()
    host, port = "127.0.0.1", 9781

    task = asyncio.create_task(run_server(host, port))
    await asyncio.sleep(0.1)

    try:
        async with websockets.connect(f"ws://{host}:{port}") as a, websockets.connect(f"ws://{host}:{port}") as b:
            await a.send(json.dumps({"op": "hello", "token": token, "role": "agent", "session_id": "a", "name": "agent-a", "capabilities": {}}))
            await b.send(json.dumps({"op": "hello", "token": token, "role": "agent", "session_id": "b", "name": "agent-b", "capabilities": {}}))
            wa = json.loads(await a.recv())
            wb = json.loads(await b.recv())
            assert wa["op"] == "welcome"
            assert wb["op"] == "welcome"
            assert "capabilities" in wa

            await a.send(json.dumps({"op": "send", "to": "agent-b", "text": "hi"}))
            msg = json.loads(await b.recv())
            assert msg["op"] == "msg"
            assert msg["text"] == "hi"

            await a.send(json.dumps({"op": "broadcast", "text": "all"}))
            bmsg = json.loads(await b.recv())
            assert bmsg["op"] == "msg"
            assert bmsg["text"] == "all"
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
