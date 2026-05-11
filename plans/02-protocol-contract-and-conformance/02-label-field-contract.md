# Label Field Contract

Phase: 2 — Protocol Contract and Conformance

## Purpose

Resolve the mismatch where the spec declares an agent `label` but the server does not persist or return it.

## Decision

Implement `label` as an optional human-readable field. Keep `name` as the routing identifier and use `label` only for display/introspection.

## Scope

- Accept `label` during `hello`.
- Store `label` on the server connection record.
- Return `label` in `list_ok` responses.
- Document the field semantics.

## Work

1. Add `label: str | None` to the server connection state.
2. Validate `label` as `str | None`; reject non-string non-null values with a canonical error after error semantics are defined.
3. Return `label` in every `list_ok.sessions[]` item.
4. Add helper support for clients that want to send a label.
5. Add conformance tests for absent, string, null, and invalid label values.
6. Update schemas and examples as needed.
7. Update docs to state that labels are display metadata and never routing keys.

## Acceptance criteria

- `hello` without `label` remains valid.
- `hello` with a string or null `label` is accepted.
- `list_ok` includes `label` for each agent session.
- Invalid label shape is rejected predictably.
- Docs, schemas, and implementation agree.

## Files likely to change

- `src/inter_agent/core/server.py`
- `src/inter_agent/core/client.py`
- `spec/schemas/hello.json`
- `spec/schemas/list_ok.json`
- `spec/examples/`
- `tests/conformance/`
- `README.md`
- `ARCHITECTURE.md`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest tests/test_spec_validation.py`
- `uv run mypy src tests`
