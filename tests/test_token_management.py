from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from inter_agent.core.shared import load_or_create_token, resolve_shared_secret, token_path


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_token_is_created_once_with_restrictive_permissions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

    token = load_or_create_token()
    reused = load_or_create_token()

    assert token
    assert reused == token
    assert token_path().read_text(encoding="utf-8") == token + "\n"
    assert file_mode(token_path()) == 0o600
    assert file_mode(tmp_path) == 0o700


def test_existing_token_permissions_are_tightened(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    path = token_path()
    path.write_text("existing-token\n", encoding="utf-8")
    path.chmod(0o644)

    token = load_or_create_token()

    assert token == "existing-token"
    assert file_mode(path) == 0o600


def test_env_secret_wins_and_does_not_create_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"secret": "config-secret"}), encoding="utf-8")
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("INTER_AGENT_SECRET", "env-secret")

    resolution = resolve_shared_secret()

    assert resolution.secret == "env-secret"
    assert resolution.source == "env"
    assert not token_path().exists()


def test_config_secret_wins_over_token_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.json"
    state_dir = tmp_path / "state"
    config_path.write_text(
        json.dumps({"secret": "config-secret", "dataDir": str(state_dir)}),
        encoding="utf-8",
    )
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))
    monkeypatch.delenv("INTER_AGENT_SECRET", raising=False)

    resolution = resolve_shared_secret()

    assert resolution.secret == "config-secret"
    assert resolution.source == "config"
    assert not token_path().exists()


def test_fallback_token_file_is_used_without_explicit_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("INTER_AGENT_SECRET", raising=False)

    resolution = resolve_shared_secret()
    reused = resolve_shared_secret()

    assert resolution.source == "token_file"
    assert resolution.secret
    assert reused.secret == resolution.secret
    assert token_path().exists()


@pytest.mark.parametrize(
    "payload,message",
    [({"secret": ""}, "must not be empty"), ({"secret": 123}, "must be a string")],
)
def test_invalid_config_secret_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: dict[str, object],
    message: str,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("INTER_AGENT_CONFIG", str(config_path))
    monkeypatch.delenv("INTER_AGENT_SECRET", raising=False)

    with pytest.raises(SystemExit, match=message):
        resolve_shared_secret()
