# Session ID Collision Policy

Phase: 5 — Security and Operational Hardening

## Purpose

Prevent registry confusion when two connections present the same `session_id`.

## Scope

- Define duplicate session behavior.
- Implement explicit rejection or replacement semantics.
- Test cleanup behavior.

## Decision

Reject duplicate active `session_id` values with a canonical error. This preserves session identity without surprising existing connections.

## Work

1. Add duplicate `session_id` detection during handshake.
2. Return a canonical error code for active session collisions.
3. Ensure a disconnected session releases its `session_id` reliably.
4. Add conformance tests for duplicate active sessions and reconnect after disconnect.
5. Document session identity semantics in `ARCHITECTURE.md` and `ERROR_CODES.md`.
6. Ensure list and routing behavior remain name-based where documented.

## Acceptance criteria

- A second active connection with the same `session_id` is rejected.
- A session can reconnect with the same `session_id` after the previous connection is gone.
- Error behavior is documented and tested.
- Registry cleanup remains correct for normal and abnormal disconnects.

## Files likely to change

- `src/inter_agent/core/server.py`
- `tests/conformance/`
- `ERROR_CODES.md`
- `ARCHITECTURE.md`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest`
