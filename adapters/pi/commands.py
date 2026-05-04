from __future__ import annotations

"""Minimal Pi adapter wrappers.

Core supports `list`; adapter surfaces may choose whether to expose it.
"""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def connect(name: str) -> int:
    return subprocess.call([sys.executable, str(ROOT / "core/client.py"), "--name", name])


def send(to: str, text: str) -> int:
    return subprocess.call([sys.executable, str(ROOT / "core/send.py"), "--to", to, "--text", text])


def broadcast(text: str) -> int:
    return subprocess.call([sys.executable, str(ROOT / "core/send.py"), "--text", text])


def list_sessions() -> int:
    return subprocess.call([sys.executable, str(ROOT / "core/list.py")])
