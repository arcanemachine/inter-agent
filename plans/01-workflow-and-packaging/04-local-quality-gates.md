# Local Quality Gates

Phase: 1 — Workflow and Packaging Foundation

## Purpose

Provide a project-local command that runs the repository's required checks reproducibly without depending on a hosted automation service.

## Repurposed backlog item

- Add automated quality gates to run formatting, linting, typing, tests, and spec validation.

## Scope

- Add a local check script or command target.
- Run the same checks required by `AGENTS.md`.
- Keep output straightforward for coding-agent and human review.

## Work

1. Add a checked-in command such as `scripts/check` or an equivalent project-local runner.
2. Have the command run `uv sync --locked` when appropriate, or clearly document when dependency sync is separate.
3. Run formatting, linting, typing, and tests.
4. Ensure spec validation remains covered by `pytest`.
5. Update `README.md` with the local quality gate command.
6. Update `AGENTS.md` so agents use the local quality gate when appropriate.
7. Keep the command independent of hosted automation providers.

## Acceptance criteria

- One documented project-local command runs the required quality checks.
- The command uses `uv.lock` without modifying it during routine checks.
- The command does not depend on external services.
- Individual check commands remain documented for targeted local debugging.

## Files likely to change

- `scripts/check` or equivalent
- `README.md`
- `AGENTS.md`

## Checks

- The new local quality gate command
- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`
