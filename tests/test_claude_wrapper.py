from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_BIN = ROOT / "integrations" / "claude-code" / "skills" / "inter-agent" / "bin"
WRAPPER = SKILL_BIN / "inter-agent-claude"
BOOTSTRAP = SKILL_BIN / "bootstrap-runtime"


def make_helper(path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env bash\n" "set -euo pipefail\n" f"printf '{label}:%s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def run_wrapper(
    tmp_path: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    runtime_env = {
        "HOME": str(tmp_path / "home"),
        "PATH": "/usr/bin:/bin",
    }
    if env:
        runtime_env.update(env)
    return subprocess.run(
        ["bash", str(WRAPPER), *args],
        env=runtime_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_claude_wrapper_env_helper_override_wins(tmp_path: Path) -> None:
    env_helper = tmp_path / "env" / "inter-agent-claude"
    config_helper = tmp_path / "checkout" / ".venv" / "bin" / "inter-agent-claude"
    make_helper(env_helper, "env")
    make_helper(config_helper, "config")

    result = run_wrapper(
        tmp_path,
        "status",
        "--json",
        env={
            "INTER_AGENT_CLAUDE_HELPER": str(env_helper),
            "CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(tmp_path / "checkout"),
        },
    )

    assert result.returncode == 0
    assert result.stdout == "env:status --json\n"


def test_claude_wrapper_uses_plugin_project_path(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    make_helper(helper, "config")

    result = run_wrapper(
        tmp_path,
        "list",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    assert result.stdout == "config:list\n"


def test_claude_wrapper_uses_managed_venv_before_path(tmp_path: Path) -> None:
    managed = tmp_path / "home" / ".claude" / "data" / "inter-agent" / "venv"
    managed_helper = managed / "bin" / "inter-agent-claude"
    path_helper = tmp_path / "path" / "inter-agent-claude"
    make_helper(managed_helper, "managed")
    make_helper(path_helper, "path")

    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{path_helper.parent}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert result.stdout == "managed:status\n"


def test_claude_wrapper_reports_setup_needed_when_no_runtime_exists(tmp_path: Path) -> None:
    result = run_wrapper(tmp_path, "status")

    assert result.returncode == 127
    assert result.stdout == ""
    assert "[inter-agent] setup needed: run /inter-agent bootstrap" in result.stderr
    assert "integrations/claude-code/README.md#runtime-setup" in result.stderr


def test_claude_wrapper_bootstrap_requires_yes(tmp_path: Path) -> None:
    result = run_wrapper(tmp_path, "bootstrap")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "[inter-agent] setup approval required" in result.stderr


def test_claude_bootstrap_source_uses_github_main_archive() -> None:
    script = BOOTSTRAP.read_text(encoding="utf-8")

    assert "https://github.com/arcanemachine/inter-agent/archive/refs/heads/main.zip" in script
    assert "--yes" in script
    assert "Python 3.10+ not found" in script


def test_claude_wrapper_passes_plugin_secret_to_helper(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'secret:%s\\n' \"${INTER_AGENT_SECRET:-}\"\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)

    result = run_wrapper(
        tmp_path,
        "status",
        env={
            "CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path),
            "CLAUDE_PLUGIN_OPTION_SECRET": "plugin-secret",
        },
    )

    assert result.returncode == 0
    assert result.stdout == "secret:plugin-secret\n"
