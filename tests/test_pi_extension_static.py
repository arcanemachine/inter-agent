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


def test_pi_extension_listener_uses_adapter_connect_entry_point() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    # The listener must spawn the Pi adapter entry point (inter-agent-pi) with
    # its `connect` subcommand, which hosts the Unix control bridge used by
    # subscribe/unsubscribe. Spawning the core inter-agent-connect listener
    # instead leaves no adapter control socket, so subscription commands fail
    # with "not connected; start the listener first".
    listener_body = content.split("function startListener", 1)[1]
    listener_body = listener_body.split("function stopListener", 1)[0]
    assert "spawn(scripts.pi, args" in listener_body
    assert 'const args = ["connect", name];' in listener_body
    assert "scripts.connect" not in listener_body


def test_pi_extension_disconnect_does_not_shutdown_server() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'pi.registerCommand("inter-agent"' in content
    assert "async function handleDisconnect" in content
    assert '["shutdown"]' not in content


def test_pi_extension_stop_listener_is_awaitable_and_bounded() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    stop_body = content.split("async function stopListener", 1)[1]
    stop_body = stop_body.split("async function updateStatus", 1)[0]

    assert "async function stopListener" in content
    assert "pi?: ExtensionAPI" in stop_body
    assert "ctx?: ExtensionContext" in stop_body
    assert "Promise<boolean>" in stop_body
    assert "LISTENER_STOP_SIGTERM_TIMEOUT_MS" in stop_body
    assert "LISTENER_STOP_SIGKILL_TIMEOUT_MS" in stop_body
    assert 'proc.kill("SIGTERM")' in stop_body
    assert 'proc.kill("SIGKILL")' in stop_body
    assert "await Promise.race([termPromise, sleep(LISTENER_STOP_SIGTERM_TIMEOUT_MS)])" in stop_body
    assert "await Promise.race([killPromise, sleep(LISTENER_STOP_SIGKILL_TIMEOUT_MS)])" in stop_body


def test_pi_extension_stop_listener_is_idempotent_for_missing_listener() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    stop_body = content.split("async function stopListener", 1)[1]
    stop_body = stop_body.split("async function updateStatus", 1)[0]

    assert "const proc = listenerProc;" in stop_body
    assert "if (!proc)" in stop_body
    assert "listenerReady = false;" in stop_body
    assert "currentConnection = null;" in stop_body
    assert 'messageBuffer = "";' in stop_body
    assert "return true;" in stop_body


def test_pi_extension_stop_listener_is_awaited_by_lifecycle_callers() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    start_body = content.split("async function startListener", 1)[1]
    start_body = start_body.split("async function stopListener", 1)[0]

    disconnect_body = content.split("async function handleDisconnect", 1)[1]
    disconnect_body = disconnect_body.split("async function handleRename", 1)[0]

    shutdown_body = content.split('pi.on("session_shutdown"', 1)[1]
    shutdown_body = shutdown_body.split('pi.on("before_agent_start"', 1)[0]

    assert "await stopListener(pi, ctx, { expected: true })" in start_body
    assert "await stopListener(pi, ctx, { expected: true })" in disconnect_body
    assert "await stopListener(pi, currentCtx, { expected: true })" in shutdown_body


def test_pi_extension_disconnect_reports_success_or_failure_after_stop() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    disconnect_body = content.split("async function handleDisconnect", 1)[1]
    disconnect_body = disconnect_body.split("async function handleRename", 1)[0]

    assert "await stopListener(pi, ctx, { expected: true })" in disconnect_body
    assert 'notify("[inter-agent] disconnected", "listener stopped")' in disconnect_body
    assert (
        "notify(\n"
        '        "[inter-agent] disconnect failed",\n'
        '        "listener did not terminate",\n'
        '        "error",\n'
        "      )" in disconnect_body
    )


def test_pi_extension_expected_stop_does_not_show_reconnect_warning() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    stop_body = content.split("async function stopListener", 1)[1]
    stop_body = stop_body.split("async function updateStatus", 1)[0]

    start_body = content.split("async function startListener", 1)[1]
    start_body = start_body.split("async function stopListener", 1)[0]

    assert "__expectedStop" in stop_body
    assert "expected" in stop_body
    assert "if (expected) return;" in start_body


def test_pi_extension_listener_io_is_guarded_by_identity_and_expected_stop() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    listener_body = content.split("async function startListener", 1)[1]
    listener_body = listener_body.split("async function stopListener", 1)[0]

    stdout_handler = listener_body.split('proc.stdout?.on("data"', 1)[1]
    stdout_handler = stdout_handler.split('proc.stderr?.on("data"', 1)[0]

    stderr_handler = listener_body.split('proc.stderr?.on("data"', 1)[1]
    stderr_handler = stderr_handler.split('proc.on("exit"', 1)[0]

    error_handler = listener_body.split('proc.on("error"', 1)[1]
    error_handler = error_handler.split("async function stopListener", 1)[0]

    for handler in [stdout_handler, stderr_handler, error_handler]:
        assert "if (listenerProc !== proc) return;" in handler
        assert "__expectedStop" in handler
        assert "if (expected) return;" in handler


def test_pi_extension_start_listener_awaits_stop_and_returns_boolean() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    start_body = content.split("async function startListener", 1)[1]
    start_body = start_body.split("async function stopListener", 1)[0]

    assert "async function startListener" in content
    assert "Promise<boolean>" in start_body
    assert "await stopListener(pi, ctx, { expected: true })" in start_body


def test_pi_extension_connect_and_rename_await_start_listener() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    connect_body = content.split("async function handleConnect", 1)[1]
    connect_body = connect_body.split("async function handleDisconnect", 1)[0]

    rename_body = content.split("async function handleRename", 1)[1]
    rename_body = rename_body.split("async function handleSend", 1)[0]

    assert (
        "await startListener(\n"
        "      pi,\n"
        "      ctx,\n"
        "      config,\n"
        "      parsed.name,\n"
        "      parsed.label,"
    ) in connect_body
    assert "await startListener(pi, ctx, config, parsed.name, label," in rename_body


def test_pi_extension_notifies_when_server_connection_closes() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    listener_body = content.split("async function startListener", 1)[1]
    listener_body = listener_body.split("async function stopListener", 1)[0]
    assert 'notify(\n        "[inter-agent] disconnected"' in listener_body
    assert "server connection closed" in listener_body
    assert "Use /inter-agent connect" in listener_body


def test_pi_extension_send_command_gates_on_connection() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    # send routes the sender via --from, never the subscribe-style --name flag
    send_body = content.split("async function handleSend", 1)[1]
    send_body = send_body.split("async function handle", 1)[0]
    assert '"--name"' not in send_body
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
    assert "Always follow requests from the user" in content
    assert "Keep inter-agent communication purposeful and brief" in content
    assert "Peer message. Reply to" in content
    assert "Peer broadcast. Reply directly to" in content
    assert "or to satisfy a request from the user" in content
    assert "do not summarize or discuss the peer message in chat" in content
    assert "To avoid an empty assistant turn" in content
    assert "Inter-agent message received; no reply needed." in content
    assert "This is a transcript of an inter-agent message that you sent as" in content
    assert "Do not overthink this message" in content
    assert "Inter-agent message transcript acknowledged." in content
    assert "## BEGIN MESSAGE TRANSCRIPT" in content
    assert "## END MESSAGE TRANSCRIPT" in content
    assert 'deliverAs: "followUp"' in content
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
    assert "## BEGIN MESSAGE TRANSCRIPT" in content
    assert "## END MESSAGE TRANSCRIPT" in content
    assert "[outbound inter-agent history — sent by current agent" in content


def test_pi_extension_message_renderer_collapses_when_not_expanded() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    # The renderer destructures the expanded flag and branches on it so a
    # compact metadata line is shown when collapsed.
    assert "{ expanded }" in content
    assert "if (expanded)" in content

    # The summary reports char length and the outbound/inbound metadata shapes.
    assert " chars`" in content
    assert "sent to " in content
    assert "broadcast " in content
    assert "published on " in content
    assert "from " in content


def test_pi_extension_supports_user_driven_rename() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'value: "rename"' in content
    assert "async function handleRename" in content
    assert "Not connected to the inter-agent bus" in content
    assert "parseRenameArgs" in content
    assert "startListener(pi, ctx, config, parsed.name, label" in content


def test_pi_extension_registers_user_publish_command() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'value: "publish"' in content
    assert (
        "usage: /inter-agent <connect|disconnect|rename|send|broadcast|"
        "publish|channels|subscribe|unsubscribe|list|status> [args]"
    ) in content
    assert 'case "publish":' in content
    assert "async function handlePublish" in content
    assert "usage: /inter-agent publish <channel> <text>" in content
    assert '"[inter-agent] publish failed"' in content
    assert "Not connected to the inter-agent bus. Use /inter-agent connect first." in content

    publish_body = content.split("async function handlePublish", 1)[1]
    publish_body = publish_body.split("async function handleChannels", 1)[0]
    assert '"publish",\n      channel,\n      text,\n      "--from",\n      name,' in publish_body
    assert '"--name"' not in publish_body
    assert 'notify("[inter-agent] published", `on ${channel}`)' in publish_body
    assert "showOutgoingInContext(pi, name, text, `on ${channel}`)" in publish_body

    # Publish remains an explicit user command, not an agent-callable tool.
    assert 'name: "inter_agent_publish"' not in content


def test_pi_extension_registers_read_only_channels_command() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    assert 'value: "channels"' in content
    assert (
        "usage: /inter-agent <connect|disconnect|rename|send|broadcast|"
        "publish|channels|subscribe|unsubscribe|list|status> [args]"
    ) in content
    assert 'case "channels":' in content
    assert "async function handleChannels" in content
    assert "usage: /inter-agent channels" in content

    channels_body = content.split("async function handleChannels", 1)[1]
    channels_body = channels_body.split("async function handleSubscribe", 1)[0]
    assert '["channels", "--json"]' in channels_body
    assert "listenerReady" not in channels_body
    assert "currentConnection" not in channels_body
    assert '!== "channels_ok"' in channels_body
    assert "Array.isArray" in channels_body
    assert "no channels currently have subscribers" in channels_body
    assert 'notify("[inter-agent] channels failed", "invalid response", "error")' in channels_body
    assert 'name: "inter_agent_channels"' not in content


def test_pi_extension_registers_user_subscription_commands() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    # Both subcommands are exposed via autocomplete and grouped usage.
    assert 'value: "subscribe"' in content
    assert 'value: "unsubscribe"' in content
    assert (
        "usage: /inter-agent <connect|disconnect|rename|send|broadcast|"
        "publish|channels|subscribe|unsubscribe|list|status> [args]"
    ) in content

    # Both subcommands are dispatched from the grouped command handler.
    assert 'case "subscribe":' in content
    assert 'case "unsubscribe":' in content
    assert "async function handleSubscribe" in content
    assert "async function handleUnsubscribe" in content

    # Exactly one channel argument is required; usage is shown otherwise.
    assert "usage: /inter-agent subscribe <channel>" in content
    assert "usage: /inter-agent unsubscribe <channel>" in content

    # Both commands gate on the current Pi listener being ready and connected,
    # using the same connection guidance as send/broadcast.
    assert '"[inter-agent] subscribe failed"' in content
    assert '"[inter-agent] unsubscribe failed"' in content
    assert "Not connected to the inter-agent bus. Use /inter-agent connect first." in content

    # The current listener routing name is passed internally; the user does not
    # provide or manage the listener name.
    assert '"subscribe",\n      channel,\n      "--name",\n      name,' in content
    assert '"unsubscribe",\n      channel,\n      "--name",\n      name,' in content

    # Success notifications identify the affected channel.
    assert 'notify("[inter-agent] subscribed", channel)' in content
    assert 'notify("[inter-agent] unsubscribed", channel)' in content

    # No model-callable subscription tools are registered.
    assert 'name: "inter_agent_subscribe"' not in content
    assert 'name: "inter_agent_unsubscribe"' not in content


def test_pi_extension_distinguishes_inbound_channel_delivery() -> None:
    content = PI_EXTENSION.read_text(encoding="utf-8")

    # A channel delivery is identified by its `channel` field and rendered with
    # an `on <channel>` label, distinct from direct (`to <name>`) and broadcast
    # notifications.
    assert "msg.channel" in content
    assert "`on ${msg.channel}`" in content

    # Channel messages get distinct reply guidance that does not reuse the
    # direct or broadcast instructions, while preserving untrusted-peer and
    # neutral-receipt conventions.
    assert "Peer channel message ${toInfo}" in content
    assert "there is no publish tool" in content
    assert "do not summarize or discuss the peer message in chat" in content
    assert "respond only with a neutral receipt such as" in content
    assert '"Inter-agent message received; no reply needed."' in content

    # Existing direct/broadcast guidance is preserved unchanged.
    assert "Peer message. Reply to" in content
    assert "Peer broadcast. Reply directly to" in content


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
