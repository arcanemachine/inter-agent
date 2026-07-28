#!/usr/bin/env python3
"""Validate initialized, exact ecosystem submodules without contacting a remote."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "core": "https://github.com/arcanemachine/inter-agent-core.git",
    "extensions/pi": "https://github.com/arcanemachine/inter-agent-pi.git",
    "extensions/claude-code": "https://github.com/arcanemachine/inter-agent-claude-code.git",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True)


def fail(message: str) -> None:
    raise SystemExit(f"submodule check failed: {message}")


def main() -> None:
    modules = ROOT / ".gitmodules"
    if not modules.is_file():
        fail(".gitmodules is absent")

    configured = {}
    for path in EXPECTED:
        try:
            configured[path] = git("config", "-f", ".gitmodules", "--get", f"submodule.{path}.url").strip()
        except subprocess.CalledProcessError:
            fail(f"missing URL for {path}")
    if configured != EXPECTED:
        fail(".gitmodules does not contain the expected canonical URLs")

    index = {}
    for line in git("ls-files", "-s").splitlines():
        mode, object_id, _, path = line.split(maxsplit=3)
        if mode == "160000":
            index[path] = object_id
    if set(index) != set(EXPECTED):
        fail("index does not contain exactly the expected gitlinks")

    statuses = git("submodule", "status", "--recursive").splitlines()
    if len(statuses) != len(EXPECTED):
        fail("submodules are not initialized exactly once")
    for line in statuses:
        if not line or line[0] != " ":
            fail("a submodule is uninitialized, conflicted, or dirty")
        fields = line.split()
        if len(fields) < 2:
            fail("unparseable submodule status")
        object_id, path = fields[0], fields[1]
        if path not in index or index[path] != object_id:
            fail(f"{path} is not at its indexed gitlink")
        if git("-C", path, "status", "--porcelain"):
            fail(f"{path} has worktree changes")

    print("submodule check passed")


if __name__ == "__main__":
    main()
