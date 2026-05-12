"""Minimal Pi adapter wrappers.

Core supports `list`; adapter surfaces may choose whether to expose it.
"""

from __future__ import annotations

import subprocess
import sys


def connect(name: str, label: str | None = None) -> int:
    command = [sys.executable, "-m", "inter_agent.core.client", name]
    if label is not None:
        command.extend(["--label", label])
    return subprocess.call(command)


def send(to: str, text: str) -> int:
    return subprocess.call(
        [sys.executable, "-m", "inter_agent.core.send", "--to", to, "--text", text]
    )


def broadcast(text: str) -> int:
    return subprocess.call([sys.executable, "-m", "inter_agent.core.send", "--text", text])


def list_sessions() -> int:
    return subprocess.call([sys.executable, "-m", "inter_agent.core.list"])
