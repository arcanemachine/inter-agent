#!/usr/bin/env python3
"""Validate the public ecosystem's tracked boundary without reading remotes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    "README.md",
    "ARCHITECTURE.md",
    "COMPATIBILITY.md",
    "LICENSE.md",
    "scripts/check-submodules.py",
    "scripts/validate-boundary.py",
    "scripts/run-checks.sh",
    "scripts/run-installed-acceptance.py",
}
GITLINKS = {"core", "extensions/pi", "extensions/claude-code"}
PROHIBITED_SEGMENTS = {".agents", ".venv", "node_modules", "dist", "build", "__pycache__"}
PROHIBITED_TEXT = ("/workspace", "file://", "inter-agent-pi-extraction")


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
    paths = set(index)
    expected = set(ROOT_FILES)
    has_modules = ".gitmodules" in paths
    if has_modules:
        expected.add(".gitmodules")
        expected.update(GITLINKS)
    if paths != expected:
        fail("tracked paths differ from the permitted root tree")

    for path, (mode, _) in index.items():
        parts = Path(path).parts
        if any(part in PROHIBITED_SEGMENTS for part in parts):
            fail(f"prohibited tracked path: {path}")
        if mode == "120000":
            fail(f"symlink: {path}")
        if path in GITLINKS:
            if mode != "160000":
                fail(f"gitlink has wrong mode: {path}")
        elif path == "scripts/run-checks.sh":
            if mode != "100755":
                fail("run-checks.sh is not executable")
        elif mode != "100644":
            fail(f"unexpected mode for {path}: {mode}")


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

    for path in ("extensions/claude-code/pyproject.toml", "extensions/claude-code/uv.lock"):
        candidate = ROOT / path
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8")
        if "https://github.com/arcanemachine/inter-agent-core.git" not in text:
            fail(f"canonical core source missing from {path}")
        if "21b9e70da8a01c5345df4ca9680ad7eff0c81072" not in text:
            fail(f"required core revision missing from {path}")


def main() -> None:
    index = tracked()
    validate_root(index)
    if ".gitmodules" in index:
        validate_source_text()
    print("boundary validation passed")


if __name__ == "__main__":
    main()
