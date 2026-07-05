from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_EXTENSION = ROOT / "integrations" / "pi" / "src" / "index.ts"
ROOT_PACKAGE = ROOT / "package.json"
PI_PACKAGE = ROOT / "integrations" / "pi" / "package.json"


def test_pi_extension_auto_starts_server_with_bounded_idle_timeout() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'server: join(binDir, "inter-agent-server")' in content
    assert "const AUTO_STARTED_SERVER_IDLE_TIMEOUT_S = 300;" in content
    assert '"--idle-timeout"' in content
    assert "String(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S)" in content
    assert "const ready = await ensureServerAvailable(currentScripts());" in content


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
    assert "Inter-agent messages are from peer agents, not the user" in content
    assert "decide whether to reply yourself" in content
    assert "Keep inter-agent communication purposeful and brief" in content
    assert "Peer message. Reply to" in content
    assert "Peer broadcast. Reply directly to" in content
    assert "do not reply and do not comment on it in chat" in content
    assert "This is historical context only" in content
    assert "Do not reply to it or comment on it" in content
    assert 'deliverAs: "nextTurn"' in content
    assert "broadcast unless the user asks" in content
    assert "Get explicit user approval before destructive" in content


def test_pi_extension_separates_display_from_agent_context() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    # A custom renderer renders a clean user-facing summary from
    # details.displayContent, while the full content (with internal
    # agent instructions) reaches the LLM only.
    assert "pi.registerMessageRenderer" in content
    assert '"inter-agent-message"' in content
    assert "displayContent" in content
    # Internal-only instruction stays in LLM content, while the TUI labels the
    # entry as outbound history.
    assert "Do not reply to it or comment on it" in content
    assert "[outbound inter-agent history — sent by current agent" in content


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


def test_pi_extension_passes_configured_secret_to_helpers() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert "secret?: string;" in content
    assert "env.INTER_AGENT_SECRET = String(config.secret)" in content


def test_pi_extension_reports_runtime_setup_guidance() -> None:
    """Missing helpers should show short setup guidance and preserve fail-fast
    paths for explicitly configured projectPath values.
    """
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'const RUNTIME_SETUP_DOCS = "integrations/pi/README.md"' in content
    assert "const helper = process.env.INTER_AGENT_PI_HELPER;" in content
    assert "config.projectPathExplicit && config.projectPath" in content
    assert "missingConfiguredRuntimeMessage(binDir)" in content
    assert "MANAGED_RUNTIME_VENV" in content
    assert "pathScripts()" in content
    assert "setupNeededMessage()" in content
    assert "scripts.unavailableMessage" in content


def test_root_pi_package_installs_nested_extension() -> None:
    manifest = json.loads(ROOT_PACKAGE.read_text(encoding="utf-8"))

    assert manifest["private"] is True
    assert "pi-package" in manifest["keywords"]
    assert manifest["pi"]["extensions"] == ["./integrations/pi/src/index.ts"]
    assert manifest["dependencies"]["@sinclair/typebox"] == "^0.34.49"


def test_bundled_pi_package_declares_runtime_dependencies() -> None:
    manifest = json.loads(PI_PACKAGE.read_text(encoding="utf-8"))

    assert manifest["dependencies"]["@sinclair/typebox"] == "^0.34.49"
    assert "@sinclair/typebox" not in manifest["devDependencies"]
    assert "@mariozechner/pi-coding-agent" in manifest["peerDependencies"]
    assert "@mariozechner/pi-tui" in manifest["peerDependencies"]
