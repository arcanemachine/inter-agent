# Target Resolution Rules

Phase: 4 — Lifecycle and Routing UX

## Purpose

Make direct messaging ergonomic while preserving deterministic routing.

## Repurposed backlog item

- Add target resolution beyond exact name and corresponding conformance tests.

## Scope

- Define and implement target resolution for direct and targeted custom messages.
- Preserve exact-name matching as the first rule.
- Reject ambiguous targets predictably.

## Work

1. Document target identifiers and matching order.
2. Implement exact-name match first.
3. Implement unique-prefix match after exact match.
4. Return a canonical ambiguity error when a prefix matches multiple sessions.
5. Keep routing by display `label` out of scope; labels are not routing keys.
6. Apply the same resolution rules to `send` and targeted `custom` messages.
7. Add conformance tests for exact match, unique prefix, unknown target, and ambiguous prefix.
8. Update adapter messages so ambiguity is understandable.

## Acceptance criteria

- Exact names continue to route as before.
- Unique prefixes route only when unambiguous.
- Ambiguous prefixes do not deliver messages.
- Error semantics are documented in `ERROR_CODES.md`.
- Conformance tests cover direct and custom routing.

## Files likely to change

- `src/inter_agent/core/server.py`
- `src/inter_agent/core/` target-resolution helper module if useful
- `tests/conformance/`
- `ERROR_CODES.md`
- `ARCHITECTURE.md`
- `README.md`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest`
- `uv run mypy src tests`
