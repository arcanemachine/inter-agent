from __future__ import annotations

import json
from pathlib import Path

import pytest

from inter_agent.core.config import (
    BUILTIN_DEFAULT_PORT,
    resolve_endpoint_config,
    resolve_explicit_secret_config,
)
from inter_agent.core.shared import resolve_endpoint


def test_config_file_supplies_endpoint_and_data_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.json"
    data_dir = tmp_path / "state"
    config_path.write_text(
        json.dumps({"host": "localhost", "port": 16838, "dataDir": str(data_dir)}),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))

    resolution = resolve_endpoint_config()

    assert resolution.host == "localhost"
    assert resolution.port == 16838
    assert resolution.data_dir == data_dir
    assert resolution.host_source == "config"
    assert resolution.port_source == "config"
    assert resolution.data_dir_source == "config"


def test_cli_overrides_env_and_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"host": "config-host", "port": 16838}), encoding="utf-8")
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))
    monkeypatch.setenv("INTER_AGENT_HOST", "env-host")
    monkeypatch.setenv("INTER_AGENT_PORT", "16839")

    resolution = resolve_endpoint_config("cli-host", 16840)

    assert resolution.host == "cli-host"
    assert resolution.port == 16840
    assert resolution.host_source == "cli"
    assert resolution.port_source == "cli"


def test_env_overrides_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    env_data_dir = tmp_path / "env-state"
    config_path.write_text(
        json.dumps({"host": "config-host", "port": 16838, "dataDir": str(tmp_path / "state")}),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))
    monkeypatch.setenv("INTER_AGENT_HOST", "env-host")
    monkeypatch.setenv("INTER_AGENT_PORT", "16839")
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(env_data_dir))

    resolution = resolve_endpoint_config()

    assert resolution.host == "env-host"
    assert resolution.port == 16839
    assert resolution.data_dir == env_data_dir
    assert resolution.host_source == "env"
    assert resolution.port_source == "env"
    assert resolution.data_dir_source == "env"


def test_xdg_state_default_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    xdg_state = tmp_path / "state-home"
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(tmp_path / "missing-config.json"))
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg_state))
    monkeypatch.delenv("INTER_AGENT_DATA_DIR", raising=False)

    resolution = resolve_endpoint_config()

    assert resolution.host == "127.0.0.1"
    assert resolution.port == BUILTIN_DEFAULT_PORT
    assert resolution.data_dir == xdg_state / "inter-agent"
    assert resolution.data_dir_source == "default"


def test_allow_discovery_no_longer_redirects_endpoint(
    unused_tcp_port: int,
) -> None:
    configured_port = unused_tcp_port + 1 if unused_tcp_port < 65535 else unused_tcp_port - 1

    resolution = resolve_endpoint("127.0.0.1", configured_port, allow_discovery=True)

    assert resolution.host == "127.0.0.1"
    assert resolution.port == configured_port
    assert resolution.configured_port == configured_port


def test_config_file_supplies_explicit_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"secret": "config-secret"}), encoding="utf-8")
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))
    monkeypatch.delenv("INTER_AGENT_SECRET", raising=False)

    resolution = resolve_explicit_secret_config()

    assert resolution is not None
    assert resolution.secret == "config-secret"
    assert resolution.source == "config"


def test_env_secret_overrides_config_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"secret": "config-secret"}), encoding="utf-8")
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))
    monkeypatch.setenv("INTER_AGENT_SECRET", "env-secret")

    resolution = resolve_explicit_secret_config()

    assert resolution is not None
    assert resolution.secret == "env-secret"
    assert resolution.source == "env"
