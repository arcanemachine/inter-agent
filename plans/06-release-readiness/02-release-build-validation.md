# Release Build Validation

Phase: 6 — Release Readiness

## Purpose

Verify that the package can be built and inspected using local release commands.

## Scope

- Build source distribution and wheel.
- Validate package metadata.
- Ensure generated artifacts are ignored.
- Do not publish artifacts as part of this plan.

## Work

1. Add or document the local release validation command.
2. Run a source distribution and wheel build with uv.
3. Validate metadata with available tooling.
4. Confirm entry points are present in the built wheel.
5. Confirm generated build artifacts are ignored by Git.
6. Document any maintainer-owned release decisions, such as license or package index configuration.

## Acceptance criteria

- Local release build succeeds.
- Built package includes expected packages, schemas, examples, and entry points.
- Build artifacts do not pollute `git status`.
- Publishing remains a separate maintainer action.

## Files likely to change

- `pyproject.toml`
- `.gitignore`
- `README.md`
- local release/check script if added

## Checks

- `uv build`
- local quality gate command
- `git status --short`
