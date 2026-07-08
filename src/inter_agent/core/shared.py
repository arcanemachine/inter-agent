from __future__ import annotations

import os
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path

from inter_agent.core.auth import build_hello
from inter_agent.core.config import (
    BUILTIN_DEFAULT_HOST,
    BUILTIN_DEFAULT_PORT,
    ConfigError,
    EndpointResolution,
    resolve_data_dir_path,
    resolve_endpoint_config,
    resolve_explicit_secret_config,
)

DEFAULT_HOST = BUILTIN_DEFAULT_HOST
DEFAULT_PORT = BUILTIN_DEFAULT_PORT
DEFAULT_DIRECT_CAP = 2 * 1024 * 1024
DEFAULT_BROADCAST_CAP = 512 * 1024
DEFAULT_FRAME_CAP = 16 * 1024 * 1024
DEFAULT_CONNECTION_CAP = 64
DEFAULT_CUSTOM_TYPE_CAP = 128
DEFAULT_CUSTOM_PAYLOAD_CAP = 1024 * 1024


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
    connection_max: int = env_int("INTER_AGENT_CONNECTION_MAX", DEFAULT_CONNECTION_CAP)
    custom_type_max: int = env_int("INTER_AGENT_CUSTOM_TYPE_MAX", DEFAULT_CUSTOM_TYPE_CAP)
    custom_payload_max: int = env_int("INTER_AGENT_CUSTOM_PAYLOAD_MAX", DEFAULT_CUSTOM_PAYLOAD_CAP)


@dataclass(frozen=True)
class SecretResolution:
    """Resolved shared server secret without exposing it in status output."""

    secret: str
    source: str
    config_path: Path | None = None
    path: Path | None = None


class ServerAlreadyRunningError(RuntimeError):
    """Compatibility error for older callers; bind failure now detects duplicates."""


def data_dir() -> Path:
    path = resolve_data_dir_path()
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def token_path() -> Path:
    return data_dir() / "token"


def _atomic_write_text(path: Path, content: str, mode: int = 0o600) -> None:
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.chmod(temp_path, mode)
    os.replace(temp_path, path)
    os.chmod(path, mode)


def load_or_create_token() -> str:
    """Load or create the fallback local generated secret."""
    path = token_path()
    if path.exists():
        os.chmod(path, 0o600)
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(32)
    _atomic_write_text(path, token + "\n")
    return token


def resolve_shared_secret() -> SecretResolution:
    """Resolve the shared server secret using env/config/token-file precedence."""
    try:
        explicit = resolve_explicit_secret_config()
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc
    if explicit is not None:
        return SecretResolution(
            secret=explicit.secret,
            source=explicit.source,
            config_path=explicit.config_path,
        )
    return SecretResolution(secret=load_or_create_token(), source="token_file", path=token_path())


def resolve_endpoint(
    host: str | None = None,
    port: int | None = None,
    *,
    allow_discovery: bool = False,
    tls: bool | None = None,
    tls_cert_path: str | None = None,
    tls_key_path: str | None = None,
) -> EndpointResolution:
    """Resolve the configured endpoint.

    ``allow_discovery`` is accepted for compatibility but no longer redirects
    away from the configured endpoint.
    """
    del allow_discovery
    try:
        return resolve_endpoint_config(host, port, tls, tls_cert_path, tls_key_path)
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc


def utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def next_msg_id() -> str:
    return secrets.token_hex(8)


def control_hello(session_id: str, client_nonce: str | None = None) -> dict[str, object]:
    return build_hello(
        role="control",
        session_id=session_id,
        name="control",
        capabilities={},
        client_nonce=client_nonce,
    )


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
