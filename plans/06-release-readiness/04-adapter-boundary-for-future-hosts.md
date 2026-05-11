# Adapter Boundary for Future Hosts

Phase: 6 — Release Readiness

## Purpose

Confirm that the core/adapter boundary is clear enough for additional host integrations without making another host adapter part of the completion scope.

## Scope

- Document adapter responsibilities.
- Ensure core APIs are usable by host adapters.
- Record non-Pi host ideas in `IDEAS.md`.

## Work

1. Review adapter code for Pi-specific assumptions that belong outside core.
2. Document what adapters may do: command UX, host notifications, output formatting, and lifecycle integration.
3. Document what adapters must not do: redefine protocol semantics, bypass auth, or depend on private server internals.
4. Add a small adapter-author section in `ARCHITECTURE.md` or adapter docs.
5. Ensure the core command API has enough typed surfaces for another adapter.
6. Add Claude Code and other host integrations to `IDEAS.md`, not to completion plans.

## Acceptance criteria

- Core behavior is independent of Pi-specific UX.
- Adapter responsibilities are documented.
- Future host integrations have a clear starting point.
- Completion does not require another host adapter.

## Files likely to change

- `ARCHITECTURE.md`
- `README.md`
- `src/inter_agent/adapters/pi/`
- `IDEAS.md`

## Checks

- `uv run pytest`
- `uv run mypy src tests`
