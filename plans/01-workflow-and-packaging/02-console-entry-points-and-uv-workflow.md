# Console Entry Points and uv Workflow

Phase: 1 — Workflow and Packaging Foundation

## Purpose

Make server and adapter commands runnable through installed package entry points instead of file paths or `.venv/bin/python` assumptions.

## Repurposed backlog items

- Add package entry points so users can run core and adapter commands without file paths.
- Improve installation/setup instructions to use `uv sync`.
- Clarify that `start.sh` is a development helper rather than the primary command path.

## Scope

- Add console scripts in `pyproject.toml`.
- Update quickstart and adapter docs to use `uv sync` and `uv run`.
- Keep `start.sh` working as a development helper.

## Work

1. Add `[project.scripts]` entries for the supported command surface.
2. Include entry points for starting the server and for the Pi adapter command UX.
3. Ensure entry-point functions return process exit codes where applicable.
4. Add smoke tests for command help output using the installed scripts through `uv run` or direct `main()` calls where subprocess use is unnecessary.
5. Rewrite `README.md` setup instructions around `uv sync`.
6. Rewrite `adapters/pi/README.md` around the package entry points.
7. Mention `start.sh` only as a local development/demo helper.

## Recommended command names

- `inter-agent-server`
- `inter-agent-connect`
- `inter-agent-send`
- `inter-agent-list`
- `inter-agent-pi`

The Pi command remains the primary host-adapter command surface for users.

## Acceptance criteria

- A fresh checkout can run `uv sync` and then use package entry points through `uv run`.
- Server, connect, send, broadcast, list, and status flows have documented command examples.
- Existing direct Python file-path invocations are no longer presented as the primary workflow.
- Help output tests cover the script entry points or their target `main()` functions.

## Files likely to change

- `pyproject.toml`
- `README.md`
- `adapters/pi/README.md`
- `tests/`
- `start.sh`

## Checks

- `uv sync --locked`
- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`
