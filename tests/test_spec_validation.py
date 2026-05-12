from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "spec"


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def _load_asyncapi() -> dict[str, object]:
    doc = yaml.safe_load((SPEC_DIR / "asyncapi.yaml").read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return cast(dict[str, object], doc)


def _iter_refs(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        item = cast(dict[str, object], value)
        ref = item.get("$ref")
        if isinstance(ref, str):
            yield ref
        for child in item.values():
            yield from _iter_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_refs(child)


def _resolve_internal_ref(doc: dict[str, object], ref: str) -> object:
    target: object = doc
    for part in ref.removeprefix("#/").split("/"):
        assert isinstance(target, dict), f"{ref} traverses through a non-object"
        target_dict = cast(dict[str, object], target)
        assert part in target_dict, f"{ref} references missing path segment {part}"
        target = target_dict[part]
    return target


def test_asyncapi_file_is_valid_yaml_and_has_basics() -> None:
    doc = _load_asyncapi()
    assert doc["asyncapi"] == "2.6.0"
    assert "channels" in doc
    assert "components" in doc


def test_schema_files_are_valid_json_schemas() -> None:
    for schema_path in sorted((SPEC_DIR / "schemas").glob("*.json")):
        Draft202012Validator.check_schema(_load_json(schema_path))


def test_examples_validate_against_schemas() -> None:
    for example_path in sorted((SPEC_DIR / "examples").glob("*.json")):
        example = _load_json(example_path)
        op = example.get("op")
        assert isinstance(op, str), f"{example_path} must include a string op"
        schema_path = SPEC_DIR / "schemas" / f"{op}.json"
        assert schema_path.exists(), f"{example_path} has no matching schema at {schema_path}"
        Draft202012Validator(_load_json(schema_path)).validate(example)


def test_asyncapi_refs_exist() -> None:
    doc = _load_asyncapi()
    for ref in _iter_refs(doc):
        if ref.startswith("#/"):
            _resolve_internal_ref(doc, ref)
        elif ref.startswith("./"):
            assert (SPEC_DIR / ref).exists(), f"missing external ref target: {ref}"
        else:
            raise AssertionError(f"unsupported ref format: {ref}")


def test_asyncapi_messages_use_component_schema_refs() -> None:
    doc = _load_asyncapi()
    components = cast(dict[str, object], doc["components"])
    messages = cast(dict[str, object], components["messages"])
    schemas = cast(dict[str, object], components["schemas"])

    for message_name, message in messages.items():
        assert isinstance(message, dict), f"message {message_name} must be an object"
        payload = cast(dict[str, object], message).get("payload")
        assert isinstance(payload, dict), f"message {message_name} must define a payload object"
        ref = cast(dict[str, object], payload).get("$ref")
        assert ref == f"#/components/schemas/{message_name}"
        assert message_name in schemas
