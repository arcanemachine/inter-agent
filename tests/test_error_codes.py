from __future__ import annotations

import json
import re
from pathlib import Path

from inter_agent.core.errors import ERROR_CODE_VALUES

ROOT = Path(__file__).resolve().parents[1]


def _documented_codes() -> set[str]:
    text = (ROOT / "ERROR_CODES.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\| `([^`]+)` \|", text, flags=re.MULTILINE))


def _schema_codes() -> list[str]:
    schema = json.loads((ROOT / "spec/schemas/error.json").read_text(encoding="utf-8"))
    values = schema["properties"]["code"]["enum"]
    assert isinstance(values, list)
    return [str(value) for value in values]


def test_every_canonical_error_code_is_documented() -> None:
    assert _documented_codes() == set(ERROR_CODE_VALUES)


def test_error_schema_enumerates_canonical_error_codes() -> None:
    assert _schema_codes() == list(ERROR_CODE_VALUES)
