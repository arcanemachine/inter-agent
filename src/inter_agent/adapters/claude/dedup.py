"""Short-window suppression of identical repeated sends.

The Claude Code agent loop sometimes re-fires the same send command within
a few seconds (e.g. because send is silent on success and the loop cannot
confirm delivery). The bus itself is single-delivery, so each re-fire
produces a separate delivered message. This module suppresses the
duplicate *client-side* invocations within a short window so only the
first reaches the bus.

The cache is keyed by (sender_name, target, text) for direct sends and
(sender_name, text) for broadcasts, and persists across CLI processes via
a small JSON file in the adapter data directory.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from inter_agent.adapters.claude import state

# Wall-clock seconds are used because each CLI invocation is a fresh
# process with its own monotonic clock origin; monotonic time is not
# comparable across processes.

DEDUP_WINDOW_S = 3.0


def _dedup_path() -> Path:
    return state.claude_data_dir() / "send-dedup.json"


def _cache_key(sender: str, *parts: str) -> str:
    h = hashlib.sha256()
    h.update(sender.encode("utf-8"))
    for part in parts:
        h.update(b"\x00")
        h.update(part.encode("utf-8"))
    return h.hexdigest()


def _read_cache(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, (int, float)):
            result[key] = float(value)
    return result


def _atomic_write(path: Path, data: dict[str, float]) -> None:
    # Reuse the shared atomic-write helper to keep permissions consistent.
    state._atomic_write_json(path, {k: v for k, v in data.items()})


@contextmanager
def _cache_lock(path: Path) -> Iterator[None]:
    """Serialize read/check/write updates across short-lived CLI processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _prune(cache: dict[str, float], now: float) -> dict[str, float]:
    cutoff = now - DEDUP_WINDOW_S
    return {k: v for k, v in cache.items() if v >= cutoff}


def is_duplicate_send(sender: str, *parts: str) -> bool:
    """Return True if an identical send was recorded within the window.

    Records the current send otherwise. Window is short enough that
    legitimate later re-sends of the same text are unaffected.
    """
    path = _dedup_path()
    key = _cache_key(sender, *parts)
    with _cache_lock(path):
        now = time.time()
        cache = _prune(_read_cache(path), now)
        if key in cache:
            return True
        cache[key] = now
        _atomic_write(path, cache)
        return False
