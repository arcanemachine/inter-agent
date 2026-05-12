from __future__ import annotations

import pytest

from inter_agent.adapters.pi.cli import main


def test_status_outputs_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["status"])
    assert code == 0
