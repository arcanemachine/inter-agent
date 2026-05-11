# Claude Code Plugin and Skill Scaffold

Extra Phase: 7 — Claude Code Support

## Purpose

Create the Claude Code packaging scaffold that exposes inter-agent commands and starts the Monitor listener in supported Claude Code sessions.

## Scope

- Add Claude Code adapter files under the project namespace.
- Add plugin and/or skill assets according to the accepted design.
- Keep shell-facing pieces thin and route behavior through Python adapter code.

## Work

1. Create the `src/inter_agent/adapters/claude/` package.
2. Add adapter modules for CLI parsing, command dispatch, Monitor listener startup, and output formatting.
3. Add Claude Code plugin or skill files in a documented location.
4. Add a Monitor definition that starts the listener lazily on inter-agent command invocation by default.
5. Provide an auto-start configuration path only if the design accepts it.
6. Avoid relying on manifest substitution tokens as shell environment variables; resolve paths script-relatively or through documented Claude Code headers.
7. Keep plugin/skill instructions concise to control context cost.
8. Add smoke tests for parser dispatch and generated config files where practical.

## Acceptance criteria

- Claude Code assets are present and documented.
- The Monitor command resolves paths correctly after installation.
- The scaffold can start a bounded help/status command without a running bus server.
- Adapter code uses core APIs rather than invoking core files by path.
- Plugin or skill files do not embed project-local absolute paths.

## Files likely to change

- `src/inter_agent/adapters/claude/`
- Claude Code plugin or skill asset directory selected by the design
- `pyproject.toml`
- `tests/`
- `README.md`

## Checks

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`
