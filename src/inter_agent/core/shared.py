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


def data_dir() -> Path:
    path = Path(os.getenv("INTER_AGENT_DATA_DIR", str(Path.home() / ".inter-agent")))
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def token_path() -> Path:
    return data_dir() / "token"


def identity_path(port: int) -> Path:
    return data_dir() / f"server.{port}.meta"


def load_or_create_token() -> str:
    path = token_path()
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    path.write_text(token + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return token


def write_server_identity(host: str, port: int) -> None:
    payload = {"pid": os.getpid(), "host": host, "port": port}
    path = identity_path(port)
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, 0o600)


def verify_server_identity(host: str, port: int) -> bool:
    path = identity_path(port)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("host") != host or payload.get("port") != port:
            return False
        pid = int(payload.get("pid"))
        os.kill(pid, 0)
        return True
    except Exception:
        return False


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


def validate_name(name: str) -> bool:
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
