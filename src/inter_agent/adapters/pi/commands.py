"""Pi adapter wrappers around importable core command APIs.

Core supports `list`; adapter surfaces may choose whether to expose it.
"""

from __future__ import annotations

import asyncio
import json
import sys

from inter_agent.core import client as core_client
from inter_agent.core import list as core_list
from inter_agent.core import send as core_send
from inter_agent.core import status as core_status
from inter_agent.core.send import SendResult
from inter_agent.core.shared import DEFAULT_HOST, DEFAULT_PORT


def _system_exit_code(exc: SystemExit) -> int:
    if isinstance(exc.code, int):
        return exc.code
    if exc.code is not None:
        print(exc.code, file=sys.stderr)
    return 1


def _send_result_code(result: SendResult) -> int:
    print(result.welcome)
    if result.error is not None:
        print(result.error.raw)
        return 1
    return 0


def connect(name: str, label: str | None = None) -> int:
    try:
        asyncio.run(core_client.run_client(DEFAULT_HOST, DEFAULT_PORT, name, label))
    except SystemExit as exc:
        return _system_exit_code(exc)
    return 0


def send(to: str, text: str) -> int:
    try:
        result = asyncio.run(core_send.send_direct_message(DEFAULT_HOST, DEFAULT_PORT, to, text))
    except SystemExit as exc:
        return _system_exit_code(exc)
    return _send_result_code(result)


def broadcast(text: str) -> int:
    try:
        result = asyncio.run(core_send.broadcast_message(DEFAULT_HOST, DEFAULT_PORT, text))
    except SystemExit as exc:
        return _system_exit_code(exc)
    return _send_result_code(result)


def list_sessions() -> int:
    try:
        result = asyncio.run(core_list.list_sessions(DEFAULT_HOST, DEFAULT_PORT))
    except SystemExit as exc:
        return _system_exit_code(exc)
    print(result.raw_response)
    return 0


def status() -> dict[str, object]:
    result = core_status.command_status()
    return {"core_list_supported": result.list_supported, "adapter_list_exposed": True}


def status_json() -> str:
    return json.dumps(status())
