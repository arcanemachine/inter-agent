# Package Metadata and Artifacts

Phase: 1 — Workflow and Packaging Foundation

## Purpose

Make package metadata and generated artifacts predictable so local installs, editable installs, and future release builds behave consistently.

## Scope

- Clean up generated packaging artifacts.
- Add safe package metadata that does not invent a license or publishing policy.
- Ensure build artifacts are ignored.

## Work

1. Add generated artifact patterns to `.gitignore`, including `*.egg-info/`, `build/`, and `dist/`.
2. Remove untracked or generated packaging directories from the working tree when they are not source files.
3. Add `readme = "README.md"` to `pyproject.toml` if absent.
4. Add classifiers that match the supported Python version and project maturity.
5. Do not add a license field unless the repository has an explicit license decision.
6. Add a release-readiness note if a maintainer license decision is still needed.

## Acceptance criteria

- `uv build` either succeeds or fails only for a clearly documented missing maintainer decision.
- Generated package metadata directories are ignored by Git.
- The package metadata points to the user-facing README.
- No unapproved license is asserted.

## Files likely to change

- `.gitignore`
- `pyproject.toml`
- `README.md`
- `plans/06-release-readiness/02-release-build-validation.md` if release validation depends on a license decision

## Checks

- `uv run python -m build` if the build dependency is available, or `uv build` when available through uv
- `git status --short`
- `uv run pytest`
