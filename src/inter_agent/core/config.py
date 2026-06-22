from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, replace
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
    discovered: bool = False
    discovery_message: str | None = None


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


def resolve_endpoint_config(
    cli_host: str | None = None,
    cli_port: int | None = None,
) -> EndpointResolution:
    """Resolve endpoint and data directory from flags, environment, config, defaults."""
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
    )


def with_discovered_endpoint(
    resolution: EndpointResolution,
    *,
    host: str,
    port: int,
    message: str,
) -> EndpointResolution:
    """Return a resolution redirected to a discovered live server."""
    return replace(
        resolution,
        host=host,
        port=port,
        discovered=True,
        discovery_message=message,
    )
