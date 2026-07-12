# Task C — persistent agent-session channel control

## Goal

Add an additive typed `AgentSession` async context manager for one persistent authenticated agent connection. It must receive ordinary inbound frames and manage its own subscribe, unsubscribe, and publish operations without opening another session identity.

## Allowed files

Read and modify only:

- `src/inter_agent/core/client.py`
- `tests/test_client_helpers.py`
- `tests/test_core_command_api.py`

Read only as needed:

- `src/inter_agent/core/auth.py`
- `src/inter_agent/core/publish.py`
- `src/inter_agent/core/shared.py`
- `src/inter_agent/core/transport.py`
- `tests/conformance/helpers.py`
- `tests/conformance/test_channels.py`

## Requirements

1. Add `AgentSession(host, port, name, label=None, *, tls=False, data_dir=None, tls_cert_path=None)` as an async context manager in `client.py`.
2. `async with AgentSession(...) as session:` must establish the existing agent handshake with the same shared-secret, endpoint, TLS, label, and error behavior as `iter_client_frames`.
3. `async for frame in session:` yields raw JSON strings. The first yielded frame is `welcome`; thereafter yield direct, broadcast, and channel-delivery frames in receive order.
4. Add these methods, all using the already-connected agent WebSocket and never creating a second connection or session ID:
   - `await session.subscribe(channel) -> dict[str, object]`
   - `await session.unsubscribe(channel) -> dict[str, object]`
   - `await session.publish(channel, text, from_name=None) -> dict[str, object] | None`
5. Subscribe/unsubscribe return their raw parsed response (`*_ok` or `error`). Publish returns a parsed protocol error received during the existing short command-response timeout, otherwise `None` on success.
6. A single reader owns WebSocket receives. It must buffer unrelated inbound frames while an operation awaits its response, so normal iteration loses no peer/channel delivery. Serialize simultaneous command-method calls rather than misattributing responses.
7. On context exit, close the WebSocket and stop reader/background work cleanly. Do not change the public signatures or behavior of `iter_client_frames` or `run_client`.

## Tests

Add live-server coverage proving that:

- the context manager yields `welcome`;
- an agent subscribes, receives a channel message published by another session, unsubscribes, and disconnects cleanly;
- a subscribe/unsubscribe protocol error reaches the method caller;
- a publish error reaches the method caller;
- an inbound frame received while a command waits remains available through iteration;
- two concurrent `AgentSession` instances maintain independent identities and subscriptions.

## Non-goals

- Do not add CLI commands, wrappers, package scripts, adapters, extension UX, protocol/schema/server changes, automatic subscriptions, reconnection, or durable channel state.
- Do not modify `README.md`, `pyproject.toml`, `inter-agent`, `publish.py`, or `channels.py`.

## Acceptance

- All operations use the one agent session identity and existing endpoint/TLS resolution.
- No inbound message is dropped or returned as the wrong command response.
- New focused tests and `./run-checks.sh` pass.
