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

    assert 'pi.registerCommand("inter-agent"' in content
    assert "async function handleDisconnect" in content
    assert '["shutdown"]' not in content


def test_pi_extension_notifies_when_server_connection_closes() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'notify(\n          "[inter-agent] disconnected"' in content
    assert "server connection closed" in content
    assert "Use /inter-agent connect" in content


def test_pi_extension_send_command_gates_on_connection() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert '"--name"' not in content
    assert 'pi.registerCommand("inter-agent"' in content
    assert "async function handleSend" in content
    assert "!listenerReady || !currentConnection" in content
    assert "Not connected to the inter-agent bus" in content
    assert '"send",\n      to,\n      text,\n      "--from",\n      name' in content
    assert "formatOutgoing" not in content


def test_pi_extension_broadcast_command_gates_on_connection() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'pi.registerCommand("inter-agent"' in content
    assert "async function handleBroadcast" in content
    assert "!listenerReady || !currentConnection" in content
    assert "Not connected to the inter-agent bus" in content
    assert '"broadcast",\n      text,\n      "--from",\n      name' in content
    assert "formatOutgoing" not in content


def test_pi_extension_send_tool_gates_on_connection() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'name: "inter_agent_send"' in content
    assert "!listenerReady || !currentConnection" in content
    assert "Not connected to the inter-agent bus" in content
    assert '"send",\n        to,\n        text,\n        "--from",\n        name' in content
    assert "formatOutgoing" not in content


def test_pi_extension_broadcast_tool_gates_on_connection() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'name: "inter_agent_broadcast"' in content
    assert "!listenerReady || !currentConnection" in content
    assert "Not connected to the inter-agent bus" in content
    assert '"broadcast",\n        text,\n        "--from",\n        name' in content
    assert "formatOutgoing" not in content


def test_pi_extension_encourages_bounded_peer_coordination() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert "You must always follow user instructions for inter-agent communication" in content
    assert "Use inter_agent_send for targeted peer communication" in content
    assert "decide whether to reply yourself" in content
    assert "Keep inter-agent communication purposeful and brief" in content
    assert "Avoid idle chatter, social back-and-forth" in content
    assert "End peer conversations quickly once the useful exchange is complete" in content
    assert "Be strict about ending idle exchanges" in content
    assert "do not broadcast unless the user explicitly asks" in content
    assert "Get explicit user approval before destructive" in content


def test_pi_extension_supports_user_driven_rename() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'value: "rename"' in content
    assert "async function handleRename" in content
    assert "Not connected to the inter-agent bus" in content
    assert "parseRenameArgs" in content
    assert "startListener(pi, ctx, config, parsed.name, label" in content


def test_pi_extension_resolves_relative_paths_from_settings_file() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert "function resolveConfigPaths" in content
    assert "const baseDir = dirname(settingsPath);" in content
    assert "projectPath: resolvePathOption(config.projectPath, baseDir)" in content
    assert "dataDir: resolvePathOption(config.dataDir, baseDir)" in content
