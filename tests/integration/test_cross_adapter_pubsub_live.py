from __future__ import annotations

import asyncio
import io
import json
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout, suppress
from dataclasses import dataclass

import pytest
from conftest import LiveServer

from inter_agent.adapters.claude import commands as claude_commands
from inter_agent.adapters.claude.listener import Listener as ClaudeListener
from inter_agent.adapters.pi import commands as pi_commands
from inter_agent.adapters.pi.listener import run_listener as run_pi_listener


@dataclass(frozen=True)
class CommandCapture:
    code: int
    stdout: str
    stderr: str


def run_command(function: Callable[..., int], *args: object) -> CommandCapture:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = function(*args)
    return CommandCapture(code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


async def wait_until(predicate: Callable[[], bool], timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("timed out waiting for cross-adapter state")


def pi_messages(output: io.StringIO) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    for line in output.getvalue().splitlines():
        if not line.strip():
            continue
        payload: object = json.loads(line)
        if isinstance(payload, dict) and payload.get("op") == "msg":
            messages.append({str(key): value for key, value in payload.items()})
    return messages


@pytest.mark.asyncio
async def test_pi_and_claude_pubsub_interoperate_on_one_server(
    live_server: LiveServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    data_dir = tmp_path_factory.mktemp("cross")
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("INTER_AGENT_SECRET", live_server.secret)
    monkeypatch.setenv("INTER_AGENT_HOST", live_server.host)
    monkeypatch.setenv("INTER_AGENT_PORT", str(live_server.port))

    channel = "cross-adapter"
    pi_name = "pi-cross"
    claude_name = "claude-cross"
    pi_output = io.StringIO()
    claude_output = io.StringIO()

    pi_task = asyncio.create_task(
        run_pi_listener(
            live_server.host,
            live_server.port,
            pi_name,
            None,
            output=pi_output,
            data_dir=data_dir,
        )
    )
    claude_listener = ClaudeListener(
        host=live_server.host,
        port=live_server.port,
        name=claude_name,
        output=claude_output,
    )
    claude_task = asyncio.create_task(claude_listener.run())

    try:
        await wait_until(lambda: '"op":"welcome"' in pi_output.getvalue().replace(" ", ""))
        await wait_until(lambda: f'connected as "{claude_name}"' in claude_output.getvalue())

        pi_subscribe = await asyncio.to_thread(run_command, pi_commands.subscribe, channel, pi_name)
        claude_subscribe = await asyncio.to_thread(run_command, claude_commands.subscribe, channel)
        assert pi_subscribe.code == 0
        assert pi_subscribe.stderr == ""
        assert claude_subscribe.code == 0
        assert claude_subscribe.stderr == ""

        pi_channels = await asyncio.to_thread(run_command, pi_commands.channels)
        claude_channels = await asyncio.to_thread(run_command, claude_commands.channels)
        assert pi_channels.code == 0
        assert claude_channels.code == 0
        expected_entry = {
            "name": channel,
            "subscribers": [claude_name, pi_name],
        }
        assert expected_entry in json.loads(pi_channels.stdout)["channels"]
        assert expected_entry in json.loads(claude_channels.stdout)["channels"]

        claude_text = "from Claude to Pi"
        claude_publish = await asyncio.to_thread(
            run_command, claude_commands.publish, channel, claude_text
        )
        assert claude_publish.code == 0
        assert claude_publish.stdout == ""
        assert claude_publish.stderr == ""
        await wait_until(
            lambda: any(msg.get("text") == claude_text for msg in pi_messages(pi_output))
        )
        delivered_to_pi = next(
            msg for msg in pi_messages(pi_output) if msg.get("text") == claude_text
        )
        assert delivered_to_pi["channel"] == channel
        assert delivered_to_pi["from_name"] == claude_name
        assert claude_text not in claude_output.getvalue()

        pi_text = "from Pi to Claude"
        pi_publish = await asyncio.to_thread(
            run_command, pi_commands.publish, channel, pi_text, pi_name
        )
        assert pi_publish.code == 0
        assert json.loads(pi_publish.stdout)["op"] == "welcome"
        assert pi_publish.stderr == ""
        await wait_until(lambda: pi_text in claude_output.getvalue())
        claude_delivery = next(
            line for line in claude_output.getvalue().splitlines() if pi_text in line
        )
        assert f'from="{pi_name}"' in claude_delivery
        assert f'kind="channel" channel="{channel}"' in claude_delivery
        assert not any(msg.get("text") == pi_text for msg in pi_messages(pi_output))

        pi_unsubscribe = await asyncio.to_thread(
            run_command, pi_commands.unsubscribe, channel, pi_name
        )
        claude_unsubscribe = await asyncio.to_thread(
            run_command, claude_commands.unsubscribe, channel
        )
        assert pi_unsubscribe.code == 0
        assert claude_unsubscribe.code == 0
    finally:
        claude_listener.stop()
        pi_task.cancel()
        with suppress(asyncio.CancelledError):
            await pi_task
        with suppress(asyncio.CancelledError):
            await claude_task
