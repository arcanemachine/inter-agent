from __future__ import annotations

import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from inter_agent.adapters.pi.cli import main as pi_main
from inter_agent.core.client import main as connect_main
from inter_agent.core.list import main as list_main
from inter_agent.core.send import main as send_main
from inter_agent.core.server import main as server_main
from inter_agent.core.shutdown import main as shutdown_main

ROOT = Path(__file__).resolve().parents[1]


def test_project_scripts_are_declared() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = config["project"]["scripts"]

    expected = {
        "inter-agent-server": "inter_agent.core.server:main",
        "inter-agent-connect": "inter_agent.core.client:main",
        "inter-agent-send": "inter_agent.core.send:main",
        "inter-agent-list": "inter_agent.core.list:main",
        "inter-agent-shutdown": "inter_agent.core.shutdown:main",
        "inter-agent-pi": "inter_agent.adapters.pi.cli:main",
    }
    assert expected.items() <= scripts.items()


@pytest.mark.parametrize(
    ("command_name", "main"),
    [
        ("inter-agent-server", server_main),
        ("inter-agent-connect", connect_main),
        ("inter-agent-send", send_main),
        ("inter-agent-list", list_main),
        ("inter-agent-shutdown", shutdown_main),
        ("inter-agent-pi", pi_main),
    ],
)
def test_command_help_output(
    command_name: str,
    main: Callable[[Sequence[str] | None], int],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert command_name in capsys.readouterr().out
