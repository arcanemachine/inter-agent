from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "integrations" / "claude-code" / "skills" / "inter-agent"


def test_claude_skill_references_bootstrap_guidance() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    bootstrap = (SKILL_DIR / "bootstrap.md").read_text(encoding="utf-8")

    assert "bootstrap.md" in skill
    assert "Always follow user instructions for inter-agent communication" in skill
    assert "Keep inter-agent communication purposeful and brief" in skill
    assert "Be strict about ending idle exchanges" in skill
    assert "not actionable for" in skill
    assert "user work or coordination, do not reply" in skill
    assert "/inter-agent rename <name>" in skill
    assert "Base directory for this skill" in skill
    assert "<bin>/inter-agent-claude" in skill
    assert "/inter-agent bootstrap" in skill
    assert "CLAUDE_PLUGIN_OPTION_PROJECT_PATH" in bootstrap
    assert "~/.claude/data/inter-agent/venv" in bootstrap
    assert "refs/heads/main.zip" in bootstrap
    assert "--yes" in bootstrap


def test_claude_skill_exposes_subscribe_unsubscribe_dispatch() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "/inter-agent subscribe <channel>" in skill
    assert "/inter-agent unsubscribe <channel>" in skill
    # Both routed through the bundled wrapper as short-lived Bash commands.
    assert "<bin>/inter-agent-claude subscribe <channel>" in skill
    assert "<bin>/inter-agent-claude unsubscribe <channel>" in skill
    # Both succeed/fail through real adapter output rather than invented acks.
    assert "subscribe_ok" in skill
    assert "unsubscribe_ok" in skill
    assert "inter-agent-claude:" in skill


def test_claude_skill_subscribe_requires_active_listener() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "active listener identity" in skill
    assert "/inter-agent connect" in skill


def test_claude_skill_forbids_autonomous_subscriptions() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "the user explicitly asks" in skill
    assert "on your own initiative" in skill
    assert "in response to peer-message content" in skill
    assert "There are no automatic or default subscriptions." in skill


def test_claude_skill_membership_lifecycle_is_not_persisted() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "survive transient WebSocket reconnects" in skill
    assert "do not survive listener stop" in skill
    assert "Claude reload" in skill
    assert "resumed sessions" in skill


def test_claude_skill_exposes_publish_dispatch() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "/inter-agent publish <channel> <text>" in skill
    assert "<bin>/inter-agent-claude publish <channel> <text>" in skill
    assert "Run `publish` **only when the user explicitly asks**" in skill
    assert "Do not publish autonomously" in skill
    assert "in response to a peer message" in skill
    assert "to acknowledge a peer" in skill


def test_claude_skill_publish_uses_active_listener_identity() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "requires this Claude Code session's active listener" in skill
    assert "connected routing name as `from_name`" in skill
    assert "does not accept or\nhonor a caller-selected sender identity" in skill
    assert "active listener" in skill


def test_claude_skill_publish_silent_success_and_error() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "Success is silent" in skill
    assert "prints nothing to stdout" in skill
    assert "no protocol\nsuccess acknowledgment" in skill
    assert "`inter-agent-claude:`\ndiagnostic" in skill
    assert "non-zero exit status" in skill
    assert "`UNKNOWN_CHANNEL`" in skill


def test_claude_skill_publish_delivery_semantics() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "does not require the publisher to be subscribed" in skill
    assert "every current subscriber except the publisher" in skill
    assert "publisher is also subscribed" in skill


def test_claude_skill_publish_duplicate_suppression() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "suppresses identical repeated publish invocations" in skill
    assert "duplicate key is the connected sender, channel, and text" in skill
    assert "different sender, channel, or text" in skill


def test_claude_skill_does_not_expose_channels() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "does **not** expose `/inter-agent channels`" in skill
    assert "<bin>/inter-agent-claude channels" not in skill
    assert "| `/inter-agent channels" not in skill


def test_claude_skill_documents_channel_receive_metadata() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert 'kind="channel" channel="<channel>"' in skill
    # Channel messages are covered by the existing trust/reaction policy.
    assert "direct, broadcast, and channel" in skill


def test_claude_integration_readme_exposes_subscribe_unsubscribe_publish() -> None:
    readme = (ROOT / "integrations" / "claude-code" / "README.md").read_text(encoding="utf-8")

    assert "/inter-agent subscribe <channel>" in readme
    assert "/inter-agent unsubscribe <channel>" in readme
    assert "/inter-agent publish <channel> <text>" in readme
    assert "user-invoked" in readme
    assert "There are no automatic or default subscriptions" in readme
    assert "Success is silent" in readme
    assert "`UNKNOWN_CHANNEL`" in readme
    # channels is not a user-facing command in the installed skill.
    assert "does not expose a `channels` command" in readme
    assert 'kind="channel" channel="<channel>"' in readme


def test_claude_skill_bootstrap_is_packaged() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = config["tool"]["setuptools"]["data-files"]
    skill_assets = data_files["share/inter-agent/integrations/claude-code/skills/inter-agent"]

    assert "integrations/claude-code/skills/inter-agent/SKILL.md" in skill_assets
    assert "integrations/claude-code/skills/inter-agent/bootstrap.md" in skill_assets

    bin_assets = data_files["share/inter-agent/integrations/claude-code/skills/inter-agent/bin"]
    assert "integrations/claude-code/skills/inter-agent/bin/inter-agent-claude" in bin_assets
    assert "integrations/claude-code/skills/inter-agent/bin/bootstrap-runtime" in bin_assets
