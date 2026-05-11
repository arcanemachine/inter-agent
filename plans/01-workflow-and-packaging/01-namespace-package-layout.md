# Namespace Package Layout

Phase: 1 — Workflow and Packaging Foundation

## Purpose

Move importable code into a stable `inter_agent` package namespace so console entry points, tests, and future adapters do not rely on generic top-level packages named `core` and `adapters`.

## Scope

- Create a `src/inter_agent/` package layout.
- Move existing `core/` modules to `src/inter_agent/core/`.
- Move existing `adapters/` modules to `src/inter_agent/adapters/`.
- Preserve public behavior while updating imports, tests, and docs.

## Work

1. Create `src/inter_agent/__init__.py`, `src/inter_agent/core/`, and `src/inter_agent/adapters/pi/`.
2. Move package files from `core/` and `adapters/` into the new namespace.
3. Update imports from `core.*` and `adapters.*` to `inter_agent.core.*` and `inter_agent.adapters.*`.
4. Update `pyproject.toml` setuptools configuration to use the `src` package layout.
5. Update test imports and any script/module references.
6. Update docs that describe repository layout.
7. Keep compatibility only where it is explicitly documented; otherwise avoid duplicate old-path modules.

## Acceptance criteria

- `uv run python -c "import inter_agent.core.server; import inter_agent.adapters.pi.cli"` succeeds.
- No production or test imports reference top-level `core` or `adapters` packages.
- Repository checks pass with updated mypy paths.
- `README.md`, `ARCHITECTURE.md`, and `AGENTS.md` describe the new layout.

## Files likely to change

- `pyproject.toml`
- `core/`
- `adapters/`
- `src/inter_agent/`
- `tests/`
- `README.md`
- `ARCHITECTURE.md`
- `AGENTS.md`
- `start.sh`

## Checks

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`
