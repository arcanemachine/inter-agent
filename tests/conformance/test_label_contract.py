from __future__ import annotations

from pathlib import Path

import pytest
import websockets
from helpers import MISSING, agent_hello, connect_agent, connect_control, running_server, send_json

from inter_agent.core.errors import ErrorCode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("label", "expected_label"),
    [
        (MISSING, None),
        ("Agent A", "Agent A"),
        (None, None),
    ],
)
async def test_label_values_are_listed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    label: object,
    expected_label: str | None,
    unused_tcp_port: int,
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with (
            websockets.connect(context.url) as agent,
            websockets.connect(context.url) as control,
        ):
            await connect_agent(agent, context, "a", "agent-a", label)
            await connect_control(control, context)
            list_ok = await send_json(control, {"op": "list"})

    assert list_ok["op"] == "list_ok"
    assert list_ok["sessions"] == [
        {
            "session_id": "a",
            "name": "agent-a",
            "label": expected_label,
        }
    ]


@pytest.mark.asyncio
async def test_invalid_label_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unused_tcp_port: int
) -> None:
    async with running_server(monkeypatch, tmp_path, unused_tcp_port) as context:
        async with websockets.connect(context.url) as ws:
            err = await send_json(
                ws, agent_hello(context.token, session_id="a", name="agent-a", label=42)
            )

    assert err["op"] == "error"
    assert err["code"] == ErrorCode.BAD_LABEL.value
