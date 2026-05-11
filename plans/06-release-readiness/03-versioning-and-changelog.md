# Versioning and Changelog

Phase: 6 — Release Readiness

## Purpose

Define how project versions and notable changes are recorded.

## Scope

- Establish versioning policy.
- Add a changelog if maintainers want one.
- Keep release notes factual and durable.

## Work

1. Decide whether the package version remains static during pre-release work or changes per release.
2. Document versioning policy in `README.md` or a dedicated changelog.
3. Add `CHANGELOG.md` if release notes should be tracked in-repo.
4. Ensure changelog entries describe stable behavior changes rather than session history.
5. Keep package version in `pyproject.toml` aligned with the documented policy.

## Acceptance criteria

- Maintainers know where to update version and release notes.
- Versioning policy is documented.
- Changelog, if present, uses stable release-oriented language.
- Package metadata and docs agree on the version.

## Files likely to change

- `pyproject.toml`
- `README.md`
- `CHANGELOG.md`

## Checks

- `uv build`
- `uv run pytest`
