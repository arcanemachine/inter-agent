# Session List and Status Semantics

Phase: 4 — Lifecycle and Routing UX

## Purpose

Make `list` and `status` reliable introspection tools for users, adapters, and host integrations.

## Scope

- Define what list returns.
- Define what status reports.
- Align core and Pi adapter output.

## Work

1. Document `list_ok.sessions[]` fields and ordering.
2. Decide whether list order should be connection order, name order, or unspecified; implement and test the decision.
3. Ensure control sessions are excluded from list unless a command explicitly requests them.
4. Define status states: server reachable, server unreachable, identity mismatch, auth failure, and protocol mismatch.
5. Add structured status result types in core command APIs.
6. Update Pi status output to reflect the core status result.
7. Add tests for list and status semantics.

## Acceptance criteria

- List output is stable enough for host tooling.
- Status output distinguishes common operational states.
- Core and Pi docs agree on fields and meanings.
- Tests cover the defined states without relying on global user state.

## Files likely to change

- `src/inter_agent/core/list.py`
- `src/inter_agent/core/`
- `src/inter_agent/adapters/pi/`
- `spec/schemas/list_ok.json`
- `tests/`
- `README.md`
- `ARCHITECTURE.md`

## Checks

- `uv run pytest`
- `uv run mypy src tests`
