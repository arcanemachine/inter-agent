# Agent Workflow

This file is for coding agents working in this repository.

## Core rules

1. Preserve universal core boundaries; keep host-specific behavior in adapters.
2. Keep behavior aligned with the protocol spec in `spec/`.
3. When adding protocol operations, update spec, implementation, and tests together.
4. Keep security behavior consistent with `SECURITY.md`.
5. Keep informational documents evergreen (`README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `AGENTS.md`).
6. Write docs as stable descriptions of what the project is and how it works; avoid temporary status language.
7. Use `TODO.md` as the evolution tracker; when work is completed, remove it from `TODO.md` and update `README.md`, `ARCHITECTURE.md`, and `SECURITY.md` as needed.
8. Prefer concrete types over `Any`; use `Any` only when a concrete type is impractical.
9. Keep commits atomic per logical step.

## Required workflow for every feature/change

1. Add or update tests for the behavior change.
2. Run repository checks locally before finishing:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run black --check .`
   - `uv run mypy core adapters tests`
3. Keep commits atomic per logical step.
4. Keep docs evergreen and scoped:
   - Agent process belongs in `AGENTS.md`.
   - User-oriented product docs belong in `README.md`.
   - Security model and assumptions belong in `SECURITY.md`.

## Design boundary

- `core/`: transport/auth/identity/routing/limits.
- `adapters/`: UX and host-integration behavior.
- `spec/`: protocol contract and examples.
- `tests/conformance/`: black-box protocol semantics.
