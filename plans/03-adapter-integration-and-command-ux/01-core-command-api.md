# Core Command API

Phase: 3 — Adapter Integration and Command UX

## Purpose

Expose reusable core functions for command behavior so adapters can call Python APIs instead of spawning scripts by file path.

## Scope

- Refactor command modules into importable functions with typed inputs and exit-code behavior.
- Keep CLI wrappers thin.
- Preserve protocol behavior.

## Work

1. Identify command behavior currently embedded in server, client, send, and list modules.
2. Extract reusable async or sync functions for server start, connect, send, broadcast, list, and status-oriented operations.
3. Keep `argparse` parsing in CLI-facing functions only.
4. Return structured results where adapters need to display or inspect output.
5. Convert Pi adapter command wrappers to call core APIs directly.
6. Preserve exit-code behavior for console scripts.
7. Add unit tests around the reusable functions where practical.

## Acceptance criteria

- Pi adapter command functions do not invoke core Python files through `subprocess.call`.
- CLI modules remain usable as console entry-point targets.
- Core command APIs are typed and documented enough for adapter authors.
- Existing command behavior is preserved by tests.

## Files likely to change

- `src/inter_agent/core/client.py`
- `src/inter_agent/core/send.py`
- `src/inter_agent/core/list.py`
- `src/inter_agent/core/server.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/pi/cli.py`
- `tests/`
- `ARCHITECTURE.md`

## Checks

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`
