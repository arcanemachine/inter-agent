from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = ROOT / "start.sh"


def test_start_script_delegates_to_package_entry_points() -> None:
    content = START_SCRIPT.read_text(encoding="utf-8")

    assert ".venv/bin/python" not in content
    assert "uv run inter-agent-server" in content
    assert "uv run inter-agent-pi connect" in content
    assert "uv run inter-agent-pi send" in content
    assert "uv run inter-agent-pi broadcast" in content
    assert "uv run inter-agent-pi list" in content
    assert "uv run inter-agent-pi status" in content
    assert "uv run inter-agent-pi shutdown" in content


def test_start_script_status_smoke(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["INTER_AGENT_DATA_DIR"] = str(tmp_path)

    result = subprocess.run(
        [str(START_SCRIPT), "status", "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["state"] == "unavailable"
    assert payload["message"] == "server identity not found"
