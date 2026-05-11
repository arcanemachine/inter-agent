# Live Integration Tests and Fixtures

Extra Phase: 7 — Claude Code Support

## Purpose

Prove the Claude Code adapter works against a live inter-agent bus without requiring an interactive Claude Code session in the automated test suite.

## Scope

- Reusable live-server fixtures.
- Monitor listener simulation through subprocesses or direct async tasks.
- Command integration tests for success and failure paths.

## Work

1. Reuse Phase 3 live-server fixtures for temporary state directories and free ports.
2. Add a test harness that runs the listener command and captures stdout as a Monitor stand-in.
3. Test direct message delivery to the listener.
4. Test broadcast delivery to the listener.
5. Test `list`, `send`, `broadcast`, `status`, `connect`, and `disconnect` command behavior where bounded.
6. Test unknown target, unavailable server, identity mismatch, duplicate listener, and stale state behavior.
7. Test notification length bounding and continuation pointer creation.
8. Mark any tests that need a real Claude Code binary as manual or separate from the required local quality gate.

## Acceptance criteria

- Required tests run without Claude Code installed.
- Listener stdout format is asserted by tests.
- Adapter state uses temporary directories in tests.
- Success and failure paths are covered.
- Manual Claude Code verification steps are documented separately if needed.

## Files likely to change

- `tests/integration/adapters/claude/`
- `tests/conftest.py`
- `src/inter_agent/adapters/claude/`
- `README.md`

## Checks

- `uv run pytest tests/integration`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy src tests`
