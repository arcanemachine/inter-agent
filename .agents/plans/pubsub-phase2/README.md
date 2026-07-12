# Pub/sub channels — Phase 2: core command APIs

Design reference: `docs/plans/pubsub-channels/00-design-seed.md`

## Sub-tasks

This packet contains three independently completable sub-tasks. The active executor packet is [Task C](c-agent-session.md). Historical packets [Task A](a-publish.md) and [Task B](b-channels.md) remain for context.

---

### Sub-task A — publish core API and CLI

**Goal:** Add a typed core API `publish_to_channel()` and a CLI entry point `inter-agent-publish` so host adapters and users can publish to a channel from a single-shot control connection.

**Files to modify:**
- `src/inter_agent/core/publish.py` (new) — `publish_to_channel()` async function and `main()` CLI
- `pyproject.toml` — add `inter-agent-publish` to `[project.scripts]`
- `inter-agent` — add `publish <channel> <text>` subcommand
- `README.md` — add publish to command list and remove "Channels are available at the core protocol level; adapters may expose channel commands in a future update." caveat

**Requirements:**
1. `publish_to_channel(host, port, channel, text, from_name=None, *, tls=False, data_dir=None, tls_cert_path=None)` follows the `send_direct_message` / `broadcast_message` pattern (control connection, handshake, send frame, handle error response).
2. Returns `SendResult` — reuse the existing dataclass from `send.py`. Publish has no success acknowledgment per protocol, so `SendResult.error` captures a protocol error if the server returns one.
3. CLI `inter-agent-publish <channel> <text> [--from <name>] [--host] [--port] [--tls/--no-tls] [--tls-cert]` exits 0 on success, 1 on error (matching `inter-agent-send`).
4. Wrapper `./inter-agent publish <channel> <text>` delegates to `uv run inter-agent-publish`.
5. Validate channel name per `validate_channel_name` from `shared.py`.

**Acceptance:**
- `publish_to_channel()` sends the correct wire frame and handles protocol errors.
- `inter-agent-publish` CLI works end-to-end with a running server.
- `./inter-agent publish` wrapper works.
- Static entry-point check in `test_console_entry_points.py` passes.
- `publish` appears in `./inter-agent --help` output.
- `./run-checks.sh` passes.

**Non-goals:** adapter-level commands, Pi/Claude extension tools, channel listing in this sub-task.

---

### Sub-task B — channels diagnostics core API and CLI

**Goal:** Add a typed core API `list_channels()` and a CLI entry point `inter-agent-channels` for diagnostic channel inspection from a control connection.

**Files to modify:**
- `src/inter_agent/core/channels.py` (new) — `list_channels()` async function, `ChannelInfo` and `ChannelsResult` dataclasses, and `main()` CLI
- `pyproject.toml` — add `inter-agent-channels` to `[project.scripts]`
- `inter-agent` — add `channels` subcommand
- `README.md` — add channels to command list

**Requirements:**
1. `ChannelInfo` dataclass with `name: str` and `subscribers: tuple[str, ...]`.
2. `ChannelsResult` dataclass with `raw_response: str`, `response: dict[str, object]`, `channels: tuple[ChannelInfo, ...]` (mirrors `ListResult` pattern).
3. `list_channels(host, port, *, tls=False, data_dir=None, tls_cert_path=None)` follows the `list_sessions` pattern.
4. CLI `inter-agent-channels [--host] [--port] [--tls/--no-tls] [--tls-cert]` prints `raw_response` JSON on stdout, exits 0 on success, 1 on error.
5. Wrapper `./inter-agent channels` delegates to `uv run inter-agent-channels`.

**Acceptance:**
- `list_channels()` returns correctly structured `ChannelsResult`.
- `inter-agent-channels` CLI works end-to-end with subscribed sessions.
- `./inter-agent channels` wrapper works.
- Static entry-point check passes.
- `./run-checks.sh` passes.

**Non-goals:** format-printing of channel lists, adapter-level commands, grouping into this sub-task.

---

### Sub-task C — agent session surface for subscribe/unsubscribe

**Goal:** Define a core `AgentSession` async context manager that lets a long-running agent connection manage channel subscriptions and publish to channels without creating a separate identity.

**Files to modify:**
- `src/inter_agent/core/client.py` — add `AgentSession` class
- `tests/test_core_command_api.py` — add conformance/usage tests

**Requirements:**
1. `AgentSession` is an async context manager that establishes an authenticated agent WebSocket connection.
2. Iterating `async for frame in session:` yields incoming raw JSON frames (the same frames `iter_client_frames` yields — direct messages, broadcast, channel deliveries).
3. `await session.subscribe(channel) -> dict[str, object]` sends a subscribe frame and returns the response (`subscribe_ok` or `error`).
4. `await session.unsubscribe(channel) -> dict[str, object]` sends an unsubscribe frame and returns the response.
5. `await session.publish(channel, text, from_name=None) -> dict[str, object] | None` sends a publish frame and returns a protocol error if one arrives within a short timeout, or `None` if the publish succeeds.

**Design constraints:**
- `AgentSession` should use the existing `iter_client_frames`-style connection setup internally (shared secret resolution, hello, auth handshake, TLS/config propagation).
- A background receiver task should buffer incoming frames while the caller is blocked on a subscribe/unsubscribe/publish response, so no frames are lost.
- The class must handle connection close cleanly (yield remaining buffered frames, then stop iteration / raise `StopAsyncIteration`).
- Route published channel messages through the normal frame-iteration path so the caller receives them alongside direct/broadcast messages.
- Do not alter the public signature of `iter_client_frames` or `run_client` — `AgentSession` is additive.

**Acceptance:**
- `AgentSession` connects, yields welcome, subscribes, receives channel messages (from another session's publish), unsubscribes, and disconnects cleanly.
- Subscribe/unsubscribe/publish protocol errors are surfaced to the caller.
- Multiple concurrent `AgentSession` instances don't interfere.
- `./run-checks.sh` passes.

**Non-goals:** adapter-level commands, Pi/Claude extension tools, persistent reconnection logic, automatic subscriptions.

---

## Sequence

1. Sub-task A (publish API + CLI) — independent.
2. Sub-task B (channels API + CLI) — independent.
3. Sub-task C (AgentSession) — depends on core channel protocol being implemented (Phase 1 is done) but is otherwise independent of A and B.

Dispatch order: A, then B, then C, or all three in parallel to separate executors since they touch different files.

## Verification

For each sub-task: `./run-checks.sh` must pass. The test file `tests/test_console_entry_points.py` and `tests/test_core_command_api.py` will need additions for each sub-task.
