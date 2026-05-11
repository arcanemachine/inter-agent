# Token Management Docs and Tests

Phase: 5 — Security and Operational Hardening

## Purpose

Document and test shared-token lifecycle behavior within the local security model.

## Scope

- Token creation, permissions, loading, and rotation guidance.
- No remote trust or multi-user credential model.

## Work

1. Add tests for token file creation and reuse.
2. Add tests for token file permissions.
3. Define behavior when an existing token file has unsafe permissions.
4. Add a documented token rotation procedure.
5. Ensure clients never accept a missing identity check before loading/sending the token.
6. Update `SECURITY.md` with plaintext localhost WebSocket assumptions.
7. Add user-facing troubleshooting for auth failures.

## Acceptance criteria

- Token file behavior is covered by tests.
- Security docs explain where the token lives, how it is protected, and how to rotate it.
- Auth failure behavior is linked to canonical errors.
- The implementation does not send tokens before server identity verification.

## Files likely to change

- `src/inter_agent/core/shared.py`
- `tests/`
- `SECURITY.md`
- `README.md`
- `ERROR_CODES.md`

## Checks

- `uv run pytest`
- `uv run mypy src tests`
