# Error Code Semantics

Phase: 2 — Protocol Contract and Conformance

## Purpose

Make protocol errors canonical, documented, typed in code, and validated by tests.

## Repurposed backlog item

- Tighten protocol error semantics and document the canonical error-code set.

## Scope

- Define every server-emitted error code.
- Centralize error-code constants in implementation.
- Document codes for adapter and client authors.
- Ensure the schema reflects the canonical set.

## Work

1. Add a typed error-code enum or literal set in the core protocol implementation.
2. Replace string literals in server error sends with the canonical symbols.
3. Create `ERROR_CODES.md` describing each code, trigger condition, and client expectation.
4. Update `spec/schemas/error.json` to enumerate canonical codes if that does not block forward-compatible extension behavior.
5. Add tests that every emitted code is documented.
6. Add conformance tests for representative validation, auth, routing, and unknown-operation errors.
7. Update `SECURITY.md` for auth-related error behavior.

## Canonical codes to account for

- `PROTOCOL_ERROR`
- `AUTH_FAILED`
- `BAD_ROLE`
- `BAD_SESSION`
- `BAD_NAME`
- `NAME_TAKEN`
- `UNKNOWN_OP`
- `BAD_TEXT`
- `TEXT_TOO_LARGE`
- `UNKNOWN_TARGET`
- Additional codes introduced by label, lifecycle, or security hardening plans

## Acceptance criteria

- Server error codes come from one canonical implementation source.
- `ERROR_CODES.md` covers every emitted code.
- Tests fail when an emitted code is undocumented.
- Error schema and docs agree with implementation.

## Files likely to change

- `src/inter_agent/core/`
- `spec/schemas/error.json`
- `ERROR_CODES.md`
- `SECURITY.md`
- `ARCHITECTURE.md`
- `tests/`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest tests/test_spec_validation.py`
- `uv run ruff check .`
- `uv run mypy src tests`
