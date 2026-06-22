from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_PLUGIN_DIR = ROOT / "integrations" / "claude-code"
PLUGIN_MANIFEST = CLAUDE_PLUGIN_DIR / ".claude-plugin" / "plugin.json"
MONITORS_DIR = CLAUDE_PLUGIN_DIR / "monitors"


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


def test_claude_skill_connect_monitor_is_persistent_without_timeout_ms() -> None:
    """The connect Monitor must be persistent with no timeout_ms.

    Claude Code's Monitor docs state timeout_ms is ignored when persistent is
    true, and persistent means "run for the lifetime of the session (no
    timeout)". Keeping a timeout_ms in the example would imply a false 1-hour
    deafness cap and invite agents to defend against a gap that does not exist.
    """
    skill = (CLAUDE_PLUGIN_DIR / "skills" / "inter-agent" / "SKILL.md").read_text(encoding="utf-8")
    # The Monitor(...) invocation block must be persistent and must not set
    # timeout_ms; the prose may mention the token while explaining why.
    start = skill.index("Monitor(")
    fence_start = skill.rindex("```", 0, start)
    fence_end = skill.index("```", start)
    monitor_block = skill[fence_start:fence_end]
    assert "persistent=true" in monitor_block
    assert "timeout_ms" not in monitor_block


def test_claude_skill_marks_incoming_messages_as_not_from_user() -> None:
    """The skill must tell the agent incoming bus messages are not from the user.

    Observed failure: a Claude Code agent reasoned "the user is asking..."
    about a peer message, treating the peer as the user. Peer notifications
    are distinguishable by the `[inter-agent ... from="<name>"]` prefix but
    the skill must state explicitly that these are peer-agent messages, not
    user instructions, so the agent does not attribute the sender to the user.
    """
    skill = (CLAUDE_PLUGIN_DIR / "skills" / "inter-agent" / "SKILL.md").read_text(encoding="utf-8")
    # Strip markdown bold markers and newlines so the assertion holds across
    # line wraps introduced by black formatting.
    normalized = skill.replace("**", "").replace("\n", " ")
    assert "NOT from the user" in normalized


def test_claude_skill_explains_monitor_stream_ended_is_not_a_duplicate() -> None:
    """The skill must explain the Monitor "stream ended" line is the launcher wrapper.

    Claude Code's Monitor renders a persistent watch as two task entries: a
    launcher/wrapper that exits after bootstrap and the real persistent watch.
    Without an explicit note, agents confabulate a duplicate-listener or
    stale-prior-session story from the benign "stream ended" telemetry. The
    skill must state that only one `listen` process runs.
    """
    skill = (CLAUDE_PLUGIN_DIR / "skills" / "inter-agent" / "SKILL.md").read_text(encoding="utf-8")
    assert "stream ended" in skill
    assert (
        "one**\n`inter-agent-claude listen`" in skill or "one `inter-agent-claude listen`" in skill
    )
