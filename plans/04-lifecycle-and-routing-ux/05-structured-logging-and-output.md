# Structured Logging and Output

Phase: 4 — Lifecycle and Routing UX

## Purpose

Separate machine-readable command output from diagnostic logging so commands are predictable in terminals and host integrations.

## Scope

- Replace ad hoc prints used for diagnostics with logging.
- Preserve command outputs that are part of the user interface.
- Add verbosity controls where useful.

## Work

1. Identify current `print()` calls and classify each as user output or diagnostic output.
2. Use Python logging for diagnostics.
3. Keep protocol payload output stable for commands that intentionally print JSON.
4. Add `--verbose` and `--quiet` flags only where they are needed and tested.
5. Ensure error output goes to stderr when appropriate.
6. Update tests to assert stdout/stderr behavior for command commands.
7. Update docs with output conventions.

## Acceptance criteria

- User-facing stdout is stable and documented.
- Diagnostics can be controlled without breaking machine-readable output.
- Tests cover stdout/stderr for key command paths.
- No command emits tracebacks for normal protocol or server-availability failures.

## Files likely to change

- `src/inter_agent/core/client.py`
- `src/inter_agent/core/send.py`
- `src/inter_agent/core/list.py`
- `src/inter_agent/core/server.py`
- `src/inter_agent/adapters/pi/`
- `tests/`
- `README.md`

## Checks

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy src tests`
