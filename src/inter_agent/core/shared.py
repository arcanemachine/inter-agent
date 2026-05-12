from __future__ import annotations

import json
import os
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9473
DEFAULT_DIRECT_CAP = 2 * 1024 * 1024
DEFAULT_BROADCAST_CAP = 512 * 1024
DEFAULT_FRAME_CAP = 16 * 1024 * 1024
STATE_VERSION = 1


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Limits:
    frame_max: int = env_int("INTER_AGENT_FRAME_MAX", DEFAULT_FRAME_CAP)
    direct_text_max: int = env_int("INTER_AGENT_DIRECT_MAX", DEFAULT_DIRECT_CAP)
    broadcast_text_max: int = env_int("INTER_AGENT_BROADCAST_MAX", DEFAULT_BROADCAST_CAP)


@dataclass(frozen=True)
class ServerIdentity:
    pid: int
    host: str
    port: int
    state_version: int
    started_at: str


class ServerAlreadyRunningError(RuntimeError):
    """Raised when lifecycle metadata points at a live server."""


def data_dir() -> Path:
    path = Path(os.getenv("INTER_AGENT_DATA_DIR", str(Path.home() / ".inter-agent")))
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def token_path() -> Path:
    return data_dir() / "token"


def identity_path(port: int) -> Path:
    return data_dir() / f"server.{port}.meta"


def pid_path(port: int) -> Path:
    return data_dir() / f"server.{port}.pid"


def shutdown_path(port: int) -> Path:
    return data_dir() / f"server.{port}.shutdown"


def server_state_paths(port: int) -> tuple[Path, ...]:
    return (identity_path(port), pid_path(port), shutdown_path(port))


def _atomic_write_text(path: Path, content: str, mode: int = 0o600) -> None:
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.chmod(temp_path, mode)
    os.replace(temp_path, path)
    os.chmod(path, mode)


def _unlink_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def load_or_create_token() -> str:
    path = token_path()
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    _atomic_write_text(path, token + "\n")
    return token


def read_server_identity(port: int) -> ServerIdentity | None:
    path = identity_path(port)
    if not path.exists():
        return None
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    pid_value = payload.get("pid")
    host_value = payload.get("host")
    port_value = payload.get("port")
    version_value = payload.get("state_version", 0)
    started_at_value = payload.get("started_at", "")
    if not isinstance(host_value, str) or not isinstance(started_at_value, str):
        return None
    try:
        if not isinstance(pid_value, (int, str)) or not isinstance(port_value, (int, str)):
            return None
        if not isinstance(version_value, (int, str)):
            return None
        return ServerIdentity(
            pid=int(pid_value),
            host=host_value,
            port=int(port_value),
            state_version=int(version_value),
            started_at=started_at_value,
        )
    except ValueError:
        return None


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def remove_server_state(host: str, port: int, pid: int | None = None) -> None:
    identity = read_server_identity(port)
    if identity is not None:
        if identity.host != host or identity.port != port:
            return
        if pid is not None and identity.pid != pid:
            return
    elif pid is not None:
        return

    for path in server_state_paths(port):
        _unlink_if_exists(path)


def cleanup_stale_server_state(host: str, port: int) -> None:
    identity = read_server_identity(port)
    if identity is None:
        if identity_path(port).exists() or pid_path(port).exists() or shutdown_path(port).exists():
            remove_server_state(host, port)
        return
    if identity.port != port:
        return
    if not is_pid_alive(identity.pid):
        remove_server_state(identity.host, port, identity.pid)


def write_server_identity(host: str, port: int) -> ServerIdentity:
    identity = ServerIdentity(
        pid=os.getpid(),
        host=host,
        port=port,
        state_version=STATE_VERSION,
        started_at=utc_now(),
    )
    payload = {
        "state_version": identity.state_version,
        "pid": identity.pid,
        "host": identity.host,
        "port": identity.port,
        "started_at": identity.started_at,
    }
    _atomic_write_text(identity_path(port), json.dumps(payload, sort_keys=True))
    _atomic_write_text(pid_path(port), f"{identity.pid}\n")
    return identity


def claim_server_state(host: str, port: int) -> ServerIdentity:
    cleanup_stale_server_state(host, port)
    existing = read_server_identity(port)
    if existing is not None and existing.port == port:
        if is_pid_alive(existing.pid):
            raise ServerAlreadyRunningError(
                f"server already running for {existing.host}:{port} with pid {existing.pid}"
            )
    return write_server_identity(host, port)


def verify_server_identity(host: str, port: int) -> bool:
    identity = read_server_identity(port)
    if identity is None:
        return False
    if identity.host != host or identity.port != port:
        return False
    return is_pid_alive(identity.pid)


def utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def next_msg_id() -> str:
    return secrets.token_hex(8)


def control_hello(token: str, session_id: str) -> dict[str, object]:
    return {
        "op": "hello",
        "token": token,
        "role": "control",
        "session_id": session_id,
        "name": "control",
        "capabilities": {},
    }


def validate_name(name: object) -> bool:
    if not isinstance(name, str):
        return False
    import re

    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", name))


def is_localhost(host: str) -> bool:
    if host == "127.0.0.1":
        return True
    try:
        return socket.gethostbyname(host) == "127.0.0.1"
    except Exception:
        return False
