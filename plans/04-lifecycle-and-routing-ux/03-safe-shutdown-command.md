# Safe Shutdown Command

Phase: 4 — Lifecycle and Routing UX

## Purpose

Provide a supported way to stop the local server without manually killing processes.

## Repurposed backlog item

- Add safe shutdown command.

## Scope

- Add a shutdown command using the authenticated control path or a documented local signal mechanism.
- Ensure server state files are cleaned up.
- Preserve the security model.

## Work

1. Choose shutdown mechanism consistent with localhost shared-token auth.
2. Add protocol operation or local lifecycle command for shutdown.
3. Authenticate shutdown requests.
4. Close connected sessions gracefully where practical.
5. Remove or mark server identity metadata as inactive.
6. Add command entry point or Pi adapter command if it belongs in the user-facing UX.
7. Add integration tests for shutdown success, auth failure, and unavailable server.
8. Document shutdown behavior and non-goals.

## Acceptance criteria

- Users can stop the server through a documented command.
- Shutdown requires valid local auth.
- State files are cleaned up or invalidated.
- Connected clients observe a predictable close behavior.
- Tests cover success and failure paths.

## Files likely to change

- `src/inter_agent/core/server.py`
- `src/inter_agent/core/`
- `src/inter_agent/adapters/pi/`
- `spec/`
- `tests/conformance/`
- `tests/integration/`
- `README.md`
- `SECURITY.md`
- `ERROR_CODES.md`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest tests/integration`
- `uv run pytest`
