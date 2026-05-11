# Server Lifecycle State Files

Phase: 4 — Lifecycle and Routing UX

## Purpose

Make server identity and lifecycle metadata accurate and safe to use across startup, restart, and shutdown.

## Repurposed backlog item

- Add graceful server lifecycle helpers with PID file handling.

## Scope

- Define state files owned by the server.
- Track active server identity explicitly.
- Clean up stale metadata where safe.

## Work

1. Define the state file set: token, identity metadata, PID metadata, and any shutdown-control metadata.
2. Write server identity atomically to avoid partial reads.
3. Include enough metadata for clients to detect stale files.
4. Detect an existing live server for the same host/port before starting a new one.
5. Remove stale state for dead server processes when safe.
6. Add tests for state file creation, detection, and cleanup.
7. Update `SECURITY.md` and architecture docs for lifecycle state.

## Acceptance criteria

- Starting a server writes complete state metadata with restrictive permissions.
- Starting a second server for the same host/port fails clearly when the first is live.
- Stale metadata is handled predictably.
- State file behavior is documented.

## Files likely to change

- `src/inter_agent/core/shared.py`
- `src/inter_agent/core/server.py`
- `tests/`
- `SECURITY.md`
- `ARCHITECTURE.md`

## Checks

- `uv run pytest`
- `uv run mypy src tests`
