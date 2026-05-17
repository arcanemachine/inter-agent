from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_EXTENSION = ROOT / "integrations" / "pi" / "src" / "index.ts"


def test_pi_extension_auto_starts_server_with_bounded_idle_timeout() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'server: join(binDir, "inter-agent-server")' in content
    assert "const AUTO_STARTED_SERVER_IDLE_TIMEOUT_S = 300;" in content
    assert '"--idle-timeout"' in content
    assert "String(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S)" in content
    assert "const ready = await ensureServerAvailable(scripts);" in content


def test_pi_extension_disconnect_does_not_shutdown_server() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'pi.registerCommand("inter-agent-disconnect"' in content
    assert '["shutdown"]' not in content


def test_pi_extension_notifies_when_server_connection_closes() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'notify(\n          "[inter-agent] disconnected"' in content
    assert "server connection closed" in content
    assert "Use /inter-agent-connect" in content
