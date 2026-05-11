# Pi Adapter Live Integration Tests

Phase: 3 — Adapter Integration and Command UX

## Purpose

Prove that the Pi adapter command surface works against a live bus server.

## Repurposed backlog item

- Add integration test coverage for adapter commands against a live server.

## Scope

- Start a real server in tests.
- Exercise Pi adapter commands through their Python API and command parser.
- Validate command output, exit codes, and delivered messages.

## Work

1. Add shared integration fixtures for temporary data directories, free ports, and background server tasks.
2. Test `inter-agent-pi status` behavior without requiring a connected agent.
3. Test Pi `list` against a live server with one or more connected agents.
4. Test Pi `send` delivering to a connected agent.
5. Test Pi `broadcast` delivering to connected agents and excluding sender/control sessions.
6. Test failure behavior for unknown targets and unavailable server identity.
7. Avoid long-running interactive `connect` tests unless they can be bounded cleanly.
8. Ensure tests clean up server tasks and state files.

## Acceptance criteria

- Adapter integration tests run without external services.
- Success and failure exit codes are asserted.
- Live-server tests use temporary state, not the user's home directory.
- Tests cover the Pi adapter commands users are expected to run.

## Files likely to change

- `tests/integration/`
- `tests/conftest.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/pi/cli.py`
- `README.md`
- `adapters/pi/README.md` or namespaced equivalent

## Checks

- `uv run pytest tests/integration`
- `uv run pytest`
- `uv run mypy src tests`
