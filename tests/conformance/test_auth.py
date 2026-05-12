import asyncio
import json

import pytest
import websockets

from inter_agent.core.server import run_server


@pytest.mark.asyncio
async def test_auth_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    host, port = "127.0.0.1", 9783

    task = asyncio.create_task(run_server(host, port))
    await asyncio.sleep(0.1)

    try:
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            await ws.send(
                json.dumps(
                    {
                        "op": "hello",
                        "token": "wrong",
                        "role": "agent",
                        "session_id": "a",
                        "name": "agent-a",
                        "capabilities": {},
                    }
                )
            )
            err = json.loads(await ws.recv())
            assert err["op"] == "error"
            assert err["code"] == "AUTH_FAILED"
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
