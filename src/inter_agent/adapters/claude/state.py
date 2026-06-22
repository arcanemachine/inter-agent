"""Per-session state files and flock-based duplicate listener prevention."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import subprocess
import tempfile
from pathlib import Path

from inter_agent.core.shared import data_dir as core_data_dir


def claude_data_dir() -> Path:
    """Return the adapter-specific data directory under the core data dir."""
    path = core_data_dir() / "claude-sessions"
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def messages_log_path() -> Path:
    """Path for the continuation-pointer messages log."""
    return claude_data_dir() / "messages.log"


def read_message_by_id(msg_id: str) -> dict[str, object] | None:
    """Return the most recent log record matching ``msg_id``, or None.

    The messages log is JSONL with ``{"msg_id", "from_name", "text"}``
    records appended by the listener. The latest match wins so a re-delivered
    or re-logged msg_id resolves to the most recent content.
    """
    path = messages_log_path()
    if not path.exists():
        return None
    found: dict[str, object] | None = None
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    payload: object = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if payload.get("msg_id") == msg_id:
                    found = {str(k): v for k, v in payload.items()}
    except OSError:
        return None
    return found


def session_path(ppid: int) -> Path:
    """Path to the per-session state file."""
    return claude_data_dir() / f"{ppid}.session"


def lock_path(ppid: int) -> Path:
    """Path to the per-session flock file."""
    return claude_data_dir() / f"{ppid}.lock"


def _atomic_write_json(path: Path, data: dict[str, object]) -> None:
    """Write JSON atomically with restrictive permissions."""
    fd, tmp_path_str = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_path_str)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, (json.dumps(data) + "\n").encode("utf-8"))
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, path)
    except OSError:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def write_session_state(ppid: int, state: dict[str, object]) -> None:
    """Atomically write session state to disk."""
    _atomic_write_json(session_path(ppid), state)


def read_session_state(ppid: int) -> dict[str, object] | None:
    """Read session state if it exists."""
    path = session_path(ppid)
    if not path.exists():
        return None
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        return {str(key): value for key, value in payload.items()}
    except (OSError, json.JSONDecodeError):
        return None


def delete_session_state(ppid: int) -> None:
    """Best-effort removal of the session state file."""
    try:
        session_path(ppid).unlink()
    except OSError:
        pass


def acquire_lock(ppid: int) -> int | None:
    """Acquire an exclusive non-blocking flock for the given ppid.

    Returns an open file descriptor on success, or None if the lock
    is already held (another listener is running for this session).
    """
    path = lock_path(ppid)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EAGAIN, errno.EACCES):
            return None
        raise


def release_lock(fd: int) -> None:
    """Release a flock file descriptor."""
    try:
        os.close(fd)
    except OSError:
        pass


def _resolve_listener_key() -> int:
    """Return the process ID used as the state-file key.

    In a Claude Code session, the listener and helper CLIs (send, status,
    etc.) are all descendants of the main Claude Code host process. We walk
    up the process tree to find that host so every CLI in the same session
    resolves to the same stable PID.

    The host is identified by an argv[0] basename of exactly ``claude``.
    A substring match on the full cmdline would wrongly match the
    ``inter-agent-claude`` entry-point script (and the Bash wrappers that
    invoke it), causing each CLI to key on its own ephemeral PID instead of
    the shared host. The exact-basename check excludes those, as well as
    ``python3.12`` and ``bash``.
    """
    pid = os.getpid()
    seen: set[int] = set()
    while pid and pid not in seen:
        seen.add(pid)
        cmdline_path = Path("/proc") / str(pid) / "cmdline"
        if cmdline_path.exists():
            try:
                argv0 = cmdline_path.read_bytes().split(b"\x00", 1)[0].decode("utf-8", "replace")
                if os.path.basename(argv0) == "claude":
                    return pid
            except OSError:
                pass
        ppid = _ppid_of(pid)
        if ppid is None:
            break
        pid = ppid
    return os.getppid() if os.getppid() > 1 else os.getpid()


def _ppid_of(pid: int) -> int | None:
    """Return the parent process ID via /proc or ps fallback."""
    proc_status = Path("/proc") / str(pid) / "status"
    if proc_status.exists():
        try:
            for line in proc_status.read_text().splitlines():
                if line.startswith("PPid:"):
                    return int(line.split()[1])
        except (OSError, ValueError):
            return None
    try:
        out = (
            subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "ppid="],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        return int(out) if out else None
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def find_listener_state() -> tuple[dict[str, object] | None, Path | None]:
    """Find the current Claude Code session's listener state.

    Returns (state, path) or (None, None) if no listener is found.
    """
    key = _resolve_listener_key()
    direct_path = session_path(key)
    state = read_session_state(key)
    if state is not None:
        return state, direct_path

    # Walk up the process tree as fallback
    pid = os.getpid()
    seen: set[int] = set()
    while pid and pid not in seen:
        seen.add(pid)
        path = session_path(pid)
        state = read_session_state(pid)
        if state is not None:
            return state, path
        ppid = _ppid_of(pid)
        if ppid is None:
            break
        pid = ppid
    return None, None


def unlink_if_matches(path: Path, expected_state: dict[str, object]) -> bool:
    """Delete `path` only if its contents match expected_state by session_id+nonce
    and the corresponding lock file is not held (no live listener).
    """
    lock_p = lock_path(int(path.stem)) if path.name.endswith(".session") else None

    fd: int | None = None
    if lock_p is not None and lock_p.exists():
        try:
            fd = os.open(str(lock_p), os.O_WRONLY | os.O_CREAT, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
                return False
        except OSError:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            fd = None

    try:
        current = read_session_state(int(path.stem))
        if current is None:
            return False
        if current.get("session_id") != expected_state.get("session_id") or current.get(
            "nonce"
        ) != expected_state.get("nonce"):
            return False
        path.unlink()
        return True
    except OSError:
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
