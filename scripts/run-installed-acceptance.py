#!/usr/bin/env python3
"""Refuse source-checkout leakage before isolated installed acceptance begins."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"installed acceptance preflight failed: {message}")


def main() -> None:
    if os.environ.get("PYTHONPATH"):
        fail("PYTHONPATH must be unset")
    if "/workspace/projects/inter-agent" in os.environ.get("PATH", "").split(":"):
        fail("protected archive must not be on PATH")
    for relative in ("core", "extensions/pi", "extensions/claude-code"):
        if not (ROOT / relative / ".git").exists():
            fail(f"uninitialized submodule: {relative}")
    print("installed acceptance preflight passed")


if __name__ == "__main__":
    main()
