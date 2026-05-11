# Packaging, Docs, and Entry Points

Extra Phase: 7 — Claude Code Support

## Purpose

Make Claude Code support installable, discoverable, documented, and included in release validation.

## Scope

- Package metadata and console entry points.
- Claude Code installation docs.
- Release and quality-gate updates.

## Work

1. Add a console entry point such as `inter-agent-claude`.
2. Ensure the Claude adapter package and plugin or skill assets are included in source and wheel builds.
3. Document installation for the selected Claude Code integration shape.
4. Document Monitor availability requirements and fallbacks.
5. Document troubleshooting for permission prompts, disabled Monitor availability, stale listener state, and bus authentication errors.
6. Update root `README.md` to list Claude Code as an extra supported adapter after the core release path.
7. Update release validation to inspect the Claude Code entry point and packaged assets.
8. Update `IDEAS.md` to remove Claude Code from unplanned host adapter ideas.

## Acceptance criteria

- `uv run inter-agent-claude --help` succeeds after a clean sync.
- Build validation includes Claude adapter code and assets.
- Docs explain how to install, connect, send, receive, and disconnect in Claude Code.
- Docs state that Monitor-backed support is local and subject to Claude Code Monitor availability and permissions.
- Repository checks pass.

## Files likely to change

- `pyproject.toml`
- `README.md`
- `src/inter_agent/adapters/claude/README.md`
- `IDEAS.md`
- `plans/06-release-readiness/02-release-build-validation.md`
- local quality gate script if paths change

## Checks

- `uv run inter-agent-claude --help`
- `uv build`
- local quality gate command
- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`
