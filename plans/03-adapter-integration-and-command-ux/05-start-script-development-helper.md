# Start Script Development Helper

Phase: 3 — Adapter Integration and Command UX

## Purpose

Keep `start.sh` useful for local development while ensuring it does not define the supported user interface.

## Scope

- Update `start.sh` to call package entry points or module commands through `uv run`.
- Document it as a helper.
- Keep behavior aligned with the primary command surface.

## Work

1. Replace hardcoded `.venv/bin/python` assumptions with a more portable `uv run` or module-based invocation.
2. Ensure supported subcommands mirror the documented entry points.
3. Add or update tests only if the script remains an important supported helper.
4. Document the script in a development section, not in the primary quickstart.
5. Avoid adding new behavior that exists only in the script.

## Acceptance criteria

- `start.sh` works after the namespace and entry-point changes.
- The primary docs direct users to package commands, not the script.
- The script contains no behavior that cannot be reached through supported commands.

## Files likely to change

- `start.sh`
- `README.md`
- `adapters/pi/README.md` or namespaced equivalent
- `tests/` if script smoke coverage is retained

## Checks

- `./start.sh status` or equivalent bounded smoke command
- `uv run pytest`
