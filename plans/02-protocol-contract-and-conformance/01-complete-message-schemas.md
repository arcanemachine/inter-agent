# Complete Message Schemas

Phase: 2 — Protocol Contract and Conformance

## Purpose

Give every protocol operation a standalone JSON Schema so examples, tests, and AsyncAPI references validate the full wire contract consistently.

## Scope

- Extract inline AsyncAPI payload definitions into `spec/schemas/`.
- Add examples where the protocol lacks canonical payloads.
- Expand schema validation tests.

## Work

1. Add schemas for `welcome`, `broadcast`, `ping`, `pong`, `bye`, `list`, and `list_ok`.
2. Update `spec/asyncapi.yaml` to reference the standalone schemas.
3. Add examples for missing canonical payloads when useful for validation.
4. Update `tests/test_spec_validation.py` to validate all schema/example pairs.
5. Add a test that AsyncAPI `$ref` targets exist.
6. Keep `additionalProperties` policy consistent with the extension posture of the protocol.

## Acceptance criteria

- Every operation listed in `spec/asyncapi.yaml` has schema coverage.
- Examples validate against their schemas.
- A missing schema reference fails tests.
- Protocol docs mention the schema organization.

## Files likely to change

- `spec/asyncapi.yaml`
- `spec/schemas/`
- `spec/examples/`
- `tests/test_spec_validation.py`
- `README.md`
- `ARCHITECTURE.md`

## Checks

- `uv run pytest tests/test_spec_validation.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
