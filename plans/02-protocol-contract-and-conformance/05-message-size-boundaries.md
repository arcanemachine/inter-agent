# Message Size Boundaries

Phase: 2 — Protocol Contract and Conformance

## Purpose

Verify direct, broadcast, custom, and frame size boundaries so resource limits are predictable and documented.

## Repurposed backlog item

- Add message size-boundary tests for direct and broadcast paths.

## Scope

- Test exact-limit and over-limit behavior for direct and broadcast text.
- Document how byte length is calculated.
- Identify custom payload behavior for later hardening.

## Work

1. Add tests for direct text exactly at `direct_text_max`.
2. Add tests for direct text one byte over `direct_text_max`.
3. Add tests for broadcast text exactly at `broadcast_text_max`.
4. Add tests for broadcast text one byte over `broadcast_text_max`.
5. Add tests that multi-byte UTF-8 text uses encoded byte length rather than character count.
6. Add a frame-limit test if it can be reliable without making the test suite slow.
7. Document limit environment variables and byte semantics.
8. Record custom payload boundary behavior in the security hardening plan if it remains broader than text limits.

## Acceptance criteria

- Boundary tests pass at exact limits and fail just above limits.
- `TEXT_TOO_LARGE` behavior is covered for direct and broadcast.
- Docs state default limits and environment variables.
- Tests avoid large allocations beyond what is necessary to prove behavior.

## Files likely to change

- `tests/conformance/`
- `src/inter_agent/core/shared.py`
- `README.md`
- `SECURITY.md`
- `ERROR_CODES.md`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest`
