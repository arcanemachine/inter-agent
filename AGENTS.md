# Agent Workflow

This file is for coding agents working in this repository.

## Core rules

1. Preserve universal core boundaries; keep host-specific behavior in adapters.
2. Keep behavior aligned with the protocol spec in `spec/`.
3. When adding protocol operations, update spec, implementation, and tests together.
4. Keep security behavior consistent with `SECURITY.md`.
5. Keep informational documents evergreen (`README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `AGENTS.md`).
6. Write docs as stable descriptions of what the project is and how it works; avoid temporary status language and date-specific status notes.
7. Use precise project terminology. Prefer `sub-agent` for delegated coding-agent work; avoid overloaded role names.
8. Use `AGENTS.PLAN.md` and `plans/` as the completion tracker. Keep exploratory work in `IDEAS.md` until it is promoted into the plan.
9. When plan work is completed, update or remove the relevant plan item and update `README.md`, `ARCHITECTURE.md`, and `SECURITY.md` as needed.
10. Prefer concrete types over `Any`; use `Any` only when a concrete type is impractical.
11. Match existing project style and conventions in code, tests, docs, and commits.
12. Keep commits atomic per logical step.
13. Commit completed work before handing back unless the user explicitly requests no commits.

## Required workflow for every feature/change

1. Add or update tests for the behavior change.
2. Run all configured repository checks locally before finishing, including tests, linters, formatters/style checks, type checkers, and spec validation. Use `./run-checks.sh` for the full gate. It runs `uv sync --locked` and the current required commands:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run black --check .`
   - `uv run mypy src tests`
3. Commit completed work when the task is done, keeping commits atomic per logical step.
4. When completing a plan phase, provide a user acceptance test when possible, along with the commit hash where that acceptance test applies.
5. If Git needs an explicit author identity for a maintainer-requested commit, use `Nicholas Moen <arcanemachine@gmail.com>` unless instructed otherwise.
6. Keep docs evergreen and scoped:
   - Agent process belongs in `AGENTS.md`.
   - User-oriented product docs belong in `README.md`.
   - Security model and assumptions belong in `SECURITY.md`.

## Design boundary

- `src/inter_agent/core/`: transport/auth/identity/routing/limits.
- `src/inter_agent/adapters/`: UX and host-integration behavior.
- `spec/`: protocol contract and examples.
- `tests/conformance/`: black-box protocol semantics.

When the package layout changes, update this section and the required check paths in the same change.
