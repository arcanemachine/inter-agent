"""Pi adapter wrappers around importable core command APIs.

Core supports `list`; adapter surfaces may choose whether to expose it.
"""

from __future__ import annotations

import asyncio
import json

from inter_agent.core import client as core_client
from inter_agent.core import list as core_list
from inter_agent.core import send as core_send
from inter_agent.core import status as core_status
from inter_agent.core.shared import DEFAULT_HOST, DEFAULT_PORT


def connect(name: str, label: str | None = None) -> int:
    asyncio.run(core_client.run_client(DEFAULT_HOST, DEFAULT_PORT, name, label))
    return 0


def send(to: str, text: str) -> int:
    result = asyncio.run(core_send.send_direct_message(DEFAULT_HOST, DEFAULT_PORT, to, text))
    print(result.welcome)
    return 0


def broadcast(text: str) -> int:
    result = asyncio.run(core_send.broadcast_message(DEFAULT_HOST, DEFAULT_PORT, text))
    print(result.welcome)
    return 0


def list_sessions() -> int:
    result = asyncio.run(core_list.list_sessions(DEFAULT_HOST, DEFAULT_PORT))
    print(result.raw_response)
    return 0


def status() -> dict[str, object]:
    result = core_status.command_status()
    return {"core_list_supported": result.list_supported, "adapter_list_exposed": True}


def status_json() -> str:
    return json.dumps(status())
