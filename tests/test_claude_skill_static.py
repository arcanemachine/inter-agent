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


def test_claude_skill_does_not_expose_publish_or_channels() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert "does **not** expose `/inter-agent publish`" in skill
    assert "or\n`/inter-agent channels`" in skill
    # publish/channels must not be documented as dispatchable wrapper commands.
    assert "<bin>/inter-agent-claude publish" not in skill
    assert "<bin>/inter-agent-claude channels" not in skill


def test_claude_skill_documents_channel_receive_metadata() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    assert 'kind="channel" channel="<channel>"' in skill
    # Channel messages are covered by the existing trust/reaction policy.
    assert "direct, broadcast, and channel" in skill


def test_claude_integration_readme_exposes_subscribe_unsubscribe_only() -> None:
    readme = (ROOT / "integrations" / "claude-code" / "README.md").read_text(encoding="utf-8")

    assert "/inter-agent subscribe <channel>" in readme
    assert "/inter-agent unsubscribe <channel>" in readme
    assert "user-invoked" in readme
    assert "There are no automatic or default subscriptions" in readme
    # publish/channels are not user-facing commands in the installed skill.
    assert "does not expose `publish` or `channels`" in readme
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
