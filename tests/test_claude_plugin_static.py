from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_PLUGIN_DIR = ROOT / "integrations" / "claude-code"
PLUGIN_MANIFEST = CLAUDE_PLUGIN_DIR / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
MONITORS_DIR = CLAUDE_PLUGIN_DIR / "monitors"


def test_claude_marketplace_manifest_points_to_claude_plugin() -> None:
    """The root marketplace metadata must install the Claude plugin subdirectory."""
    marketplace = json.loads(MARKETPLACE_MANIFEST.read_text(encoding="utf-8"))
    plugin_manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))

    assert marketplace["$schema"] == "https://json.schemastore.org/claude-code-marketplace.json"
    assert marketplace["name"] == "inter-agent"
    assert marketplace["version"] == plugin_manifest["version"]
    assert marketplace["owner"]["name"]
    assert marketplace["owner"]["email"]

    plugins = marketplace["plugins"]
    assert len(plugins) == 1
    plugin = plugins[0]
    assert plugin["name"] == plugin_manifest["name"]
    assert plugin["version"] == plugin_manifest["version"]
    assert plugin_manifest["author"]["name"] == plugin["author"]["name"]
    assert plugin_manifest["author"]["email"] == plugin["author"]["email"]
    assert plugin["category"] == "productivity"

    source = plugin["source"]
    assert source == "./integrations/claude-code"
    assert not source.startswith("/")
    assert (ROOT / source).resolve() == CLAUDE_PLUGIN_DIR.resolve()
    assert ((ROOT / source) / ".claude-plugin" / "plugin.json").is_file()


def test_claude_plugin_manifest_declares_no_declarative_monitors() -> None:
    """The plugin must not declare an `on-skill-invoke` Monitor.

    A plugin-declared Monitor would race the skill-driven
    `inter-agent-claude listen --name <name>` Monitor for the same per-session
    flock and emit a confusing "another listener is already starting or
    running" line (and, because the declarative command carries no `--name`,
    could connect under the wrong cwd-derived name if it won the race).
    Connect is driven solely by the `/inter-agent` skill, which starts a
    single Monitor with the user's chosen routing name.
    """
    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    assert "monitors" not in manifest, (
        "plugin.json must not declare a monitors entry; the listener is "
        "started on demand by the /inter-agent skill with the user's name"
    )


def test_claude_plugin_has_no_monitors_directory() -> None:
    """No plugin-declared Monitor assets should ship with the integration."""
    assert not MONITORS_DIR.exists(), (
        "integrations/claude-code/monitors/ must not exist; a plugin-declared "
        "Monitor races the skill-driven listener and causes duplicate launches"
    )
