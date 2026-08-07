#!/usr/bin/env python3
"""Validate the public ecosystem's tracked boundary without reading remotes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_SEGMENTS = {".agents", ".venv", "node_modules", "dist", "build", "__pycache__"}
PROHIBITED_TEXT = (
    "file://",
    "path =",
    "directory =",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def fail(message: str) -> None:
    raise SystemExit(f"boundary validation failed: {message}")


def tracked() -> dict[str, tuple[str, str]]:
    result = {}
    for line in git("ls-files", "-s").splitlines():
        mode, object_id, _, path = line.split(maxsplit=3)
        result[path] = (mode, object_id)
    return result


def validate_root(index: dict[str, tuple[str, str]]) -> None:
    for path, (mode, _) in index.items():
        parts = Path(path).parts
        if any(part in PROHIBITED_SEGMENTS for part in parts):
            fail(f"prohibited tracked path: {path}")
        if mode == "120000":
            fail(f"symlink: {path}")


def validate_source_text() -> None:
    paths = (
        "extensions/pi/pyproject.toml",
        "extensions/pi/uv.lock",
        "extensions/claude-code/pyproject.toml",
        "extensions/claude-code/uv.lock",
    )
    for path in paths:
        candidate = ROOT / path
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8")
        if any(token in text for token in PROHIBITED_TEXT):
            fail(f"local dependency source in {path}")


def main() -> None:
    index = tracked()
    validate_root(index)
    if ".gitmodules" in index:
        validate_source_text()
    print("boundary validation passed")


if __name__ == "__main__":
    main()
