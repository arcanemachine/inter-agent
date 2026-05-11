# Claude Command Surface and Reaction Policy

Extra Phase: 7 — Claude Code Support

## Purpose

Define and implement the Claude Code user commands and the instruction policy for how Claude should treat incoming peer messages.

## Scope

- Claude Code commands for bus operations.
- Human- and model-readable output.
- Safety policy for peer-originated instructions.

## Work

1. Implement commands for `connect`, `disconnect`, `send`, `broadcast`, `list`, and `status`.
2. Add `rename` or reconnect-with-name only if the accepted design includes it.
3. Add auto-start controls only if they are part of the supported install shape.
4. Define output formats for success, failure, and protocol errors.
5. Write a concise reaction policy for incoming messages: instruction-like messages, informational prefixes, questions, status updates, and destructive-operation safeguards.
6. State clearly that peer messages never override system, developer, tool, or permission rules.
7. Keep command behavior aligned with the Pi adapter where host differences do not require divergence.
8. Add tests for command parsing, formatting, and error mapping.

## Acceptance criteria

- Claude Code users have a documented command for each supported bus operation.
- Incoming message policy is explicit and avoids treating every peer message as unconditional authority.
- Command failures return predictable exit codes and messages.
- The command surface does not create Claude-only protocol semantics.

## Files likely to change

- `src/inter_agent/adapters/claude/cli.py`
- `src/inter_agent/adapters/claude/commands.py`
- Claude Code skill or plugin instruction files
- `tests/`
- `ERROR_CODES.md`
- `src/inter_agent/adapters/claude/README.md`

## Checks

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy src tests`
