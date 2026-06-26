# Monitor Listener and Session State

Extra Phase: 7 — Claude Code Support

## Purpose

Implement the long-running Claude Code listener that connects a session to the inter-agent bus and prints inbound messages as safe Monitor notifications.

## Scope

- Persistent listener process for Claude Code Monitor.
- Session state used by short-lived helper commands.
- Duplicate listener prevention.
- Notification truncation and continuation pointers.

## Work

1. Implement a Monitor listener command that connects to the bus as an `agent` role.
2. Print each inbound message as one stdout line that Claude Code can ingest as a notification.
3. Bound notification line length and write large message bodies to an adapter-owned log or state file with a continuation pointer.
4. Store per-session state so helper commands can identify the owning Claude Code listener.
5. Add deduplication so one Claude Code session does not start multiple active listeners.
6. Reconnect with bounded backoff when the bus restarts.
7. Clean up session state on graceful exit and handle stale state defensively.
8. Ensure the listener verifies server identity before sending the shared token.

## Acceptance criteria

- A Claude Code Monitor process can receive direct and broadcast bus messages in real time.
- Duplicate Monitor listeners for the same Claude Code session are prevented or harmless.
- Short-lived helper commands can discover the correct listener state without global ambiguity.
- Long messages are not silently truncated without a continuation path.
- Listener state uses restrictive permissions consistent with `SECURITY.md`.

## Files likely to change

- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/state.py`
- `src/inter_agent/adapters/claude/formatting.py`
- `src/inter_agent/core/` if reusable listener APIs are needed
- `tests/`
- `SECURITY.md`

## Checks

- `uv run pytest`
- `uv run mypy src tests`
