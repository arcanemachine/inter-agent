# Filesystem Permission Tests

Phase: 5 — Security and Operational Hardening

## Purpose

Verify filesystem permissions that are part of the security model.

## Scope

- Data directory permissions.
- Token file permissions.
- Server identity metadata permissions.
- Platform-compatible tests.

## Work

1. Add tests that the data directory is created with owner-only permissions where supported.
2. Add tests that token files are created with owner-read/write permissions where supported.
3. Add tests that server identity metadata is created with owner-read/write permissions where supported.
4. Handle platforms that do not support POSIX modes with explicit skips or documented behavior.
5. Ensure tests use temporary directories.
6. Update `SECURITY.md` if actual behavior differs by platform.

## Acceptance criteria

- Filesystem permission controls in `SECURITY.md` are backed by tests.
- Tests do not inspect or modify the user's real home directory.
- Platform skips are explicit and justified.
- Permission changes do not break token reuse or server startup.

## Files likely to change

- `src/inter_agent/core/shared.py`
- `tests/`
- `SECURITY.md`

## Checks

- `uv run pytest`
- `uv run mypy src tests`
