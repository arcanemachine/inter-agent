from __future__ import annotations

import ipaddress
import json
import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

BUILTIN_DEFAULT_HOST = "127.0.0.1"
BUILTIN_DEFAULT_PORT = 16837


class ConfigError(ValueError):
    """Raised when inter-agent configuration cannot be interpreted."""


@dataclass(frozen=True)
class EndpointResolution:
    """Resolved inter-agent endpoint and state location."""

    host: str
    port: int
    data_dir: Path
    host_source: str
    port_source: str
    data_dir_source: str
    config_path: Path | None
    configured_host: str
    configured_port: int
    scheme: str
    tls: bool
    tls_source: str
    tls_cert_path: Path | None
    tls_cert_source: str | None
    tls_key_path: Path | None
    tls_key_source: str | None


@dataclass(frozen=True)
class ExplicitSecretResolution:
    """Resolved explicit shared secret from environment or config."""

    secret: str
    source: str
    config_path: Path | None


def _expand_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw)))


def _platform_config_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "inter-agent" / "config.json"
    if sys.platform.startswith("win"):
        base = os.getenv("APPDATA")
        if base:
            return Path(base) / "inter-agent" / "config.json"
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "inter-agent" / "config.json"
    return Path.home() / ".config" / "inter-agent" / "config.json"


def default_config_path() -> Path:
    """Return the platform-native inter-agent config file path."""
    override = os.getenv("INTER_AGENT_CONFIG")
    if override:
        return _expand_path(override)
    return _platform_config_path()


def _platform_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "inter-agent"
    if sys.platform.startswith("win"):
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if base:
            return Path(base) / "inter-agent"
    xdg_state_home = os.getenv("XDG_STATE_HOME")
    if xdg_state_home:
        return Path(xdg_state_home) / "inter-agent"
    return Path.home() / ".local" / "state" / "inter-agent"


def _load_config() -> tuple[dict[str, object], Path | None]:
    path = default_config_path()
    if not path.exists():
        return {}, None
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"invalid inter-agent config file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"invalid inter-agent config file {path}: expected JSON object")
    return {str(key): value for key, value in payload.items()}, path


def _config_string(config: dict[str, object], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"inter-agent config key {key!r} must be a string")
    return value


def _config_port(config: dict[str, object]) -> int | None:
    value = config.get("port")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ConfigError("inter-agent config key 'port' must be an integer")
    try:
        port = int(value)
    except ValueError as exc:
        raise ConfigError("inter-agent config key 'port' must be an integer") from exc
    return _validate_port(port, "inter-agent config key 'port'")


def _env_port() -> int | None:
    raw = os.getenv("INTER_AGENT_PORT")
    if raw is None or raw == "":
        return None
    try:
        port = int(raw)
    except ValueError as exc:
        raise ConfigError("INTER_AGENT_PORT must be an integer") from exc
    return _validate_port(port, "INTER_AGENT_PORT")


def _parse_bool(value: object, source: str) -> bool:
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        raise ConfigError(f"{source} must be a boolean")
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "wss", "tls"}:
        return True
    if normalized in {"0", "false", "no", "off", "ws", "plaintext"}:
        return False
    raise ConfigError(f"{source} must be a boolean")


def _config_bool(config: dict[str, object], key: str) -> bool | None:
    value = config.get(key)
    if value is None:
        return None
    return _parse_bool(value, f"inter-agent config key {key!r}")


def _env_bool(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    return _parse_bool(raw, name)


def _is_loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    try:
        return ipaddress.ip_address(socket.gethostbyname(host)).is_loopback
    except Exception:
        return False


def _validate_port(port: int, source: str) -> int:
    if port < 1 or port > 65535:
        raise ConfigError(f"{source} must be between 1 and 65535")
    return port


def resolve_data_dir_path() -> Path:
    """Resolve the inter-agent state/data directory without creating it."""
    config, _ = _load_config()
    env_data_dir = os.getenv("INTER_AGENT_DATA_DIR")
    if env_data_dir:
        return _expand_path(env_data_dir)
    config_data_dir = _config_string(config, "dataDir")
    if config_data_dir:
        return _expand_path(config_data_dir)
    return _platform_data_dir()


def resolve_explicit_secret_config() -> ExplicitSecretResolution | None:
    """Resolve explicit shared secret from environment/config, if configured."""
    config, path = _load_config()

    env_secret = os.getenv("INTER_AGENT_SECRET")
    if env_secret is not None:
        if not env_secret.strip():
            raise ConfigError("INTER_AGENT_SECRET must not be empty")
        return ExplicitSecretResolution(secret=env_secret, source="env", config_path=path)

    config_secret = _config_string(config, "secret")
    if config_secret is not None:
        if not config_secret.strip():
            raise ConfigError("inter-agent config key 'secret' must not be empty")
        return ExplicitSecretResolution(secret=config_secret, source="config", config_path=path)

    return None


def resolve_endpoint_config(
    cli_host: str | None = None,
    cli_port: int | None = None,
    cli_tls: bool | None = None,
    cli_tls_cert_path: str | None = None,
    cli_tls_key_path: str | None = None,
) -> EndpointResolution:
    """Resolve endpoint, TLS mode, and data directory from flags, env, config, defaults."""
    config, path = _load_config()

    config_host = _config_string(config, "host")
    env_host = os.getenv("INTER_AGENT_HOST")
    if cli_host:
        host = cli_host
        host_source = "cli"
    elif env_host:
        host = env_host
        host_source = "env"
    elif config_host:
        host = config_host
        host_source = "config"
    else:
        host = BUILTIN_DEFAULT_HOST
        host_source = "default"

    config_port = _config_port(config)
    env_port = _env_port()
    if cli_port is not None:
        port = _validate_port(cli_port, "--port")
        port_source = "cli"
    elif env_port is not None:
        port = env_port
        port_source = "env"
    elif config_port is not None:
        port = config_port
        port_source = "config"
    else:
        port = BUILTIN_DEFAULT_PORT
        port_source = "default"

    env_data_dir = os.getenv("INTER_AGENT_DATA_DIR")
    config_data_dir = _config_string(config, "dataDir")
    if env_data_dir:
        data_dir = _expand_path(env_data_dir)
        data_dir_source = "env"
    elif config_data_dir:
        data_dir = _expand_path(config_data_dir)
        data_dir_source = "config"
    else:
        data_dir = _platform_data_dir()
        data_dir_source = "default"

    config_tls = _config_bool(config, "tls")
    env_tls = _env_bool("INTER_AGENT_TLS")
    if cli_tls is not None:
        tls = cli_tls
        tls_source = "cli"
    elif env_tls is not None:
        tls = env_tls
        tls_source = "env"
    elif config_tls is not None:
        tls = config_tls
        tls_source = "config"
    else:
        tls = not _is_loopback_host(host)
        tls_source = "default"

    config_tls_cert_path = _config_string(config, "tlsCert")
    env_tls_cert_path = os.getenv("INTER_AGENT_TLS_CERT")
    if cli_tls_cert_path:
        tls_cert_path = _expand_path(cli_tls_cert_path)
        tls_cert_source = "cli"
    elif env_tls_cert_path:
        tls_cert_path = _expand_path(env_tls_cert_path)
        tls_cert_source = "env"
    elif config_tls_cert_path:
        tls_cert_path = _expand_path(config_tls_cert_path)
        tls_cert_source = "config"
    else:
        tls_cert_path = None
        tls_cert_source = None

    config_tls_key_path = _config_string(config, "tlsKey")
    env_tls_key_path = os.getenv("INTER_AGENT_TLS_KEY")
    if cli_tls_key_path:
        tls_key_path = _expand_path(cli_tls_key_path)
        tls_key_source = "cli"
    elif env_tls_key_path:
        tls_key_path = _expand_path(env_tls_key_path)
        tls_key_source = "env"
    elif config_tls_key_path:
        tls_key_path = _expand_path(config_tls_key_path)
        tls_key_source = "config"
    else:
        tls_key_path = None
        tls_key_source = None

    return EndpointResolution(
        host=host,
        port=port,
        data_dir=data_dir,
        host_source=host_source,
        port_source=port_source,
        data_dir_source=data_dir_source,
        config_path=path,
        configured_host=host,
        configured_port=port,
        scheme="wss" if tls else "ws",
        tls=tls,
        tls_source=tls_source,
        tls_cert_path=tls_cert_path,
        tls_cert_source=tls_cert_source,
        tls_key_path=tls_key_path,
        tls_key_source=tls_key_source,
    )
