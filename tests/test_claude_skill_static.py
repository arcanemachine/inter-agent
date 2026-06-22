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
    assert "/inter-agent rename <name>" in skill
    assert "pipx install -e <path-to-inter-agent>" in bootstrap
    assert "uv tool install --from <path-to-inter-agent> ." in bootstrap
    assert "do **not** install" in bootstrap


def test_claude_skill_bootstrap_is_packaged() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = config["tool"]["setuptools"]["data-files"]
    skill_assets = data_files["share/inter-agent/integrations/claude-code/skills/inter-agent"]

    assert "integrations/claude-code/skills/inter-agent/SKILL.md" in skill_assets
    assert "integrations/claude-code/skills/inter-agent/bootstrap.md" in skill_assets
