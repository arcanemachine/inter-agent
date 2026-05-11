# Core Operation Conformance

Phase: 2 — Protocol Contract and Conformance

## Purpose

Expand black-box protocol coverage so every core operation and rejection path is tested through WebSocket behavior, not only through helper functions.

## Scope

- Add conformance tests for successful core operations.
- Add conformance tests for common invalid handshakes and routing failures.
- Keep tests readable and reusable through fixtures/helpers.

## Work

1. Extract shared conformance helpers for starting a server and connecting authenticated agents.
2. Add tests for `ping` / `pong`.
3. Add tests for `bye` and connection cleanup.
4. Add tests for `list` / `list_ok` with agent and control roles.
5. Add tests for broadcast excluding the sender and control sessions.
6. Add tests for duplicate names, invalid names, bad roles, missing sessions, first-op-not-hello, unknown operations, and unknown targets.
7. Add tests for custom broadcast mode without `to`.
8. Keep ports isolated and data directories temporary.

## Acceptance criteria

- Every operation in `spec/asyncapi.yaml` has at least one conformance test.
- Every canonical error-code category has at least one behavior test.
- Tests do not rely on fixed shared state in the user's home directory.
- Test helpers make later protocol tests concise.

## Files likely to change

- `tests/conformance/`
- `tests/conftest.py` if shared fixtures are useful
- `src/inter_agent/core/server.py` only if tests expose behavior gaps

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
