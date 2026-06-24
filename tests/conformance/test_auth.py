from __future__ import annotations

from pathlib import Path

import pytest
import websockets
from helpers import agent_hello, running_server, send_json

from inter_agent.core.errors import ErrorCode

# Each case describes a hello payload that must be rejected as AUTH_FAILED.
# "wrong" supplies an incorrect token; "missing" omits the token field
# entirely. Both exercise the same server branch
# (``hello.get("token") != self.token``), but the missing-token variant
# guards against a future refactor that treats absent keys specially.
AUTH_FAILURE_CASES: list[tuple[str, dict[str, object]]] = [
    ("wrong", agent_hello("wrong")),
    ("missing", {k: v for k, v in agent_hello("wrong").items() if k != "token"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("label,hello", AUTH_FAILURE_CASES, ids=[c[0] for c in AUTH_FAILURE_CASES])
async def test_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unused_tcp_port: int,
    label: str,
    hello: dict[str, object],
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            err = await send_json(ws, hello)

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.AUTH_FAILED.value
