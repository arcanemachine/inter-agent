from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "spec"


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_asyncapi_file_is_valid_yaml_and_has_basics() -> None:
    doc = yaml.safe_load((SPEC_DIR / "asyncapi.yaml").read_text(encoding="utf-8"))
    assert doc["asyncapi"] == "2.6.0"
    assert "channels" in doc
    assert "components" in doc


def test_examples_validate_against_schemas() -> None:
    hello_schema = _load_json(SPEC_DIR / "schemas/hello.json")
    send_schema = _load_json(SPEC_DIR / "schemas/send.json")
    custom_schema = _load_json(SPEC_DIR / "schemas/custom.json")

    hello_example = _load_json(SPEC_DIR / "examples/hello.agent.json")
    send_example = _load_json(SPEC_DIR / "examples/send.direct.json")
    custom_example = _load_json(SPEC_DIR / "examples/custom.unknown-pass-through.json")

    Draft202012Validator(hello_schema).validate(hello_example)
    Draft202012Validator(send_schema).validate(send_example)
    Draft202012Validator(custom_schema).validate(custom_example)
