from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_BIN = ROOT / "integrations" / "claude-code" / "skills" / "inter-agent" / "bin"
WRAPPER = SKILL_BIN / "inter-agent-claude"
BOOTSTRAP = SKILL_BIN / "bootstrap-runtime"

#: Each entry maps a presence field name to the INTER_AGENT_* variable the
#: fake helper inspects. The helper emits only fixed boolean eq/presence
#: fields; no raw or hash-derived values are ever written to stdout.
PRESENCE_FIELDS = [
    ("DATA_DIR", "INTER_AGENT_DATA_DIR"),
    ("TLS", "INTER_AGENT_TLS"),
    ("TLS_CERT", "INTER_AGENT_TLS_CERT"),
    ("TLS_KEY", "INTER_AGENT_TLS_KEY"),
    ("SECRET", "INTER_AGENT_SECRET"),
]


def make_presence_helper(path: Path, expected: dict[str, str]) -> None:
    """Write a helper that emits fixed boolean equality/presence fields only.

    Each field reports whether the received ``INTER_AGENT_*`` value equals an
    embedded expected sentinel (``NAME_eq=true/false``) and whether it is set
    (``NAME_present=true/false``). No raw or hash-derived values are emitted.
    """
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'emit() { local name="$1" actual="$2" expected="$3"; '
        'if [[ "$actual" == "$expected" ]]; then printf "%s_eq=true\\n" "$name"; '
        'else printf "%s_eq=false\\n" "$name"; fi; '
        'if [[ -n "$actual" ]]; then printf "%s_present=true\\n" "$name"; '
        'else printf "%s_present=false\\n" "$name"; fi; }',
    ]
    for name, var in PRESENCE_FIELDS:
        lines.append(f'emit {name} "${{{var}:-}}" {shlex.quote(expected.get(name, ""))}')
    lines.append("printf 'ARGS_BEGIN\\n'")
    lines.append('printf "%s\\n" "$@"')
    lines.append("printf 'ARGS_END\\n'")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def _parse_presence(stdout: str) -> dict[str, str]:
    summary: dict[str, str] = {}
    for line in stdout.splitlines():
        if line.startswith("ARGS_BEGIN") or line.startswith("ARGS_END"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            summary[key] = value
    return summary


def _parse_args(stdout: str) -> list[str]:
    lines = stdout.splitlines()
    start = lines.index("ARGS_BEGIN") + 1
    end = lines.index("ARGS_END")
    return lines[start:end]


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


def test_claude_wrapper_forwards_channels_argument_unchanged(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "#!/usr/bin/env bash\n" "set -euo pipefail\n" "printf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)

    result = run_wrapper(
        tmp_path,
        "channels",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["channels"]
    assert result.stderr == ""


def test_claude_wrapper_forwards_publish_arguments_unchanged(tmp_path: Path) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "#!/usr/bin/env bash\n" "set -euo pipefail\n" "printf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)

    result = run_wrapper(
        tmp_path,
        "publish",
        "updates",
        "build is green",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["publish", "updates", "build is green"]
    assert result.stderr == ""


def make_broken_interpreter_helper(path: Path) -> None:
    """An executable helper whose shebang interpreter does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/no/such/interpreter\n" "echo should-not-run\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_claude_wrapper_bin_assets_are_executable() -> None:
    """The bundled wrapper and bootstrap must ship executable."""
    for asset in (WRAPPER, BOOTSTRAP):
        assert asset.is_file()
        assert asset.stat().st_mode & 0o111, f"{asset} is not executable"


def test_claude_wrapper_env_helper_not_executable_fails_bounded(tmp_path: Path) -> None:
    helper = tmp_path / "env" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("#!/usr/bin/env bash\necho nope\n", encoding="utf-8")
    # Deliberately not executable.

    result = run_wrapper(
        tmp_path,
        "status",
        env={"INTER_AGENT_CLAUDE_HELPER": str(helper)},
    )

    assert result.returncode == 127
    assert result.stdout == ""
    assert "[inter-agent] setup failed:" in result.stderr
    assert "helper from INTER_AGENT_CLAUDE_HELPER not executable" in result.stderr
    assert "integrations/claude-code/README.md#runtime-setup" in result.stderr
    assert "setup needed" not in result.stderr


def test_claude_wrapper_env_helper_broken_interpreter_fails_bounded(tmp_path: Path) -> None:
    helper = tmp_path / "env" / "inter-agent-claude"
    make_broken_interpreter_helper(helper)

    result = run_wrapper(
        tmp_path,
        "status",
        env={"INTER_AGENT_CLAUDE_HELPER": str(helper)},
    )

    assert result.returncode == 127
    assert result.stdout == ""
    assert "[inter-agent] setup failed:" in result.stderr
    assert "INTER_AGENT_CLAUDE_HELPER interpreter not executable" in result.stderr
    assert "/no/such/interpreter" in result.stderr
    assert "integrations/claude-code/README.md#runtime-setup" in result.stderr
    # The bounded wrapper diagnostic must replace a raw shell exec error.
    assert "cannot execute" not in result.stderr
    assert "setup needed" not in result.stderr


def test_claude_wrapper_project_path_helper_not_executable_fails_bounded(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("#!/usr/bin/env bash\necho nope\n", encoding="utf-8")
    # Deliberately not executable.

    result = run_wrapper(
        tmp_path,
        "status",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 127
    assert result.stdout == ""
    assert "[inter-agent] setup failed:" in result.stderr
    assert "configured project_path helper not found" in result.stderr
    assert "setup needed" not in result.stderr


def test_claude_wrapper_managed_helper_broken_interpreter_fails_bounded(
    tmp_path: Path,
) -> None:
    managed = tmp_path / "home" / ".claude" / "data" / "inter-agent" / "venv"
    make_broken_interpreter_helper(managed / "bin" / "inter-agent-claude")

    result = run_wrapper(tmp_path, "status")

    assert result.returncode == 127
    assert result.stdout == ""
    assert "[inter-agent] setup failed:" in result.stderr
    assert "managed venv interpreter not executable" in result.stderr
    assert "/no/such/interpreter" in result.stderr
    assert "setup needed" not in result.stderr


def test_claude_wrapper_uses_path_helper_when_no_managed_or_project(tmp_path: Path) -> None:
    path_helper = tmp_path / "path" / "inter-agent-claude"
    make_helper(path_helper, "path")

    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{path_helper.parent}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert result.stdout == "path:status\n"


def test_claude_wrapper_path_helper_broken_interpreter_fails_bounded(
    tmp_path: Path,
) -> None:
    path_helper = tmp_path / "path" / "inter-agent-claude"
    make_broken_interpreter_helper(path_helper)

    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{path_helper.parent}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 127
    assert result.stdout == ""
    assert "[inter-agent] setup failed:" in result.stderr
    assert "PATH interpreter not executable" in result.stderr
    assert "/no/such/interpreter" in result.stderr
    assert "setup needed" not in result.stderr


def test_claude_wrapper_skips_path_helper_equal_to_self(tmp_path: Path) -> None:
    # The wrapper must not exec itself when its own bin directory is on PATH;
    # that guard is what prevents a setup-needed 127 from hiding behind a
    # recursive wrapper invocation.
    result = run_wrapper(
        tmp_path,
        "status",
        env={"PATH": f"{SKILL_BIN}{os.pathsep}/usr/bin:/bin"},
    )

    assert result.returncode == 127
    assert result.stdout == ""
    assert "[inter-agent] setup needed: run /inter-agent bootstrap" in result.stderr


def test_claude_wrapper_forwards_tls_data_and_secret_to_helper_unchanged(
    tmp_path: Path,
) -> None:
    """The bundled wrapper forwards core TLS/data env and maps the plugin
    secret to INTER_AGENT_SECRET without altering values or leaking them."""
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    data_dir = str(tmp_path / "state")
    tls_cert = str(tmp_path / "certs" / "tls-cert.pem")
    tls_key = str(tmp_path / "certs" / "tls-key.pem")
    secret_value = "claude-wrapper-tls-test-secret"
    expected = {
        "DATA_DIR": data_dir,
        "TLS": "true",
        "TLS_CERT": tls_cert,
        "TLS_KEY": tls_key,
        "SECRET": secret_value,
    }
    make_presence_helper(helper, expected)

    result = run_wrapper(
        tmp_path,
        "status",
        "--json",
        env={
            "CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path),
            "CLAUDE_PLUGIN_OPTION_SECRET": secret_value,
            "INTER_AGENT_DATA_DIR": data_dir,
            "INTER_AGENT_TLS": "true",
            "INTER_AGENT_TLS_CERT": tls_cert,
            "INTER_AGENT_TLS_KEY": tls_key,
        },
    )

    assert result.returncode == 0
    summary = _parse_presence(result.stdout)
    # Each value passed through unchanged (eq=true) and is present.
    for name in ("DATA_DIR", "TLS", "TLS_CERT", "TLS_KEY", "SECRET"):
        assert summary[f"{name}_eq"] == "true", name
        assert summary[f"{name}_present"] == "true", name

    # Helper arguments pass through unchanged.
    assert _parse_args(result.stdout) == ["status", "--json"]

    # The raw secret and private-key/cert paths never enter argv, stdout, or
    # stderr; only fixed boolean fields are emitted.
    for stream in (result.stdout, result.stderr):
        assert secret_value not in stream
        assert tls_cert not in stream
        assert tls_key not in stream
        assert data_dir not in stream
    assert secret_value not in result.args


def test_claude_wrapper_adds_no_claude_specific_tls_defaults(tmp_path: Path) -> None:
    """With no TLS env or plugin secret configured, the wrapper injects none."""
    project_path = tmp_path / "checkout"
    helper = project_path / ".venv" / "bin" / "inter-agent-claude"
    # Non-empty sentinels so eq=false would also flag an injection; the
    # presence check is the primary no-default proof.
    make_presence_helper(
        helper,
        {"TLS": "true", "TLS_CERT": "/x", "TLS_KEY": "/y", "SECRET": "s"},
    )

    result = run_wrapper(
        tmp_path,
        "channels",
        env={"CLAUDE_PLUGIN_OPTION_PROJECT_PATH": str(project_path)},
    )

    assert result.returncode == 0
    summary = _parse_presence(result.stdout)
    # The wrapper injected no Claude-specific TLS defaults and no secret.
    for name in ("TLS", "TLS_CERT", "TLS_KEY", "SECRET"):
        assert summary[f"{name}_present"] == "false", name
    assert _parse_args(result.stdout) == ["channels"]
