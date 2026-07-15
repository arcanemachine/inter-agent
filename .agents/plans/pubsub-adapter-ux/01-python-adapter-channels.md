# Task 1 — Python adapter channel commands

## Goal

Expose `subscribe`, `unsubscribe`, `publish`, and `channels` through both Python host adapters while preserving the active listener identity and each adapter's established output, error, reconnection, duplicate-suppression, and inbound-message behavior.

## Reading sequence and file authority

The packet is the implementation authority. Do not read `.agents/PLAN.md`, `ROADMAP.md`, the design seed, unrelated documentation, or the full authorized set as an onboarding sweep.

After the mandatory repository instructions and executor role, initially read only:

- `src/inter_agent/core/channels.py` (read only)
- `src/inter_agent/core/client.py` (read only)
- `src/inter_agent/core/publish.py` (read only)
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/pi/listener.py`

Inspect the other authorized files below only immediately before changing them or when a concrete requirement requires them. Tests should be read in focused groups alongside the behavior being implemented, not all at once.

### Writable files

- `src/inter_agent/adapters/control.py` (new shared adapter-local control bridge)
- `src/inter_agent/adapters/claude/README.md`
- `src/inter_agent/adapters/claude/cli.py`
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/dedup.py`
- `src/inter_agent/adapters/claude/formatting.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/state.py`
- `src/inter_agent/adapters/pi/README.md`
- `src/inter_agent/adapters/pi/cli.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/pi/listener.py`
- `tests/test_adapter_control.py` (new)
- `tests/test_claude_adapter_cli.py`
- `tests/test_claude_dedup.py`
- `tests/test_claude_listener.py`
- `tests/test_pi_adapter_cli.py`
- `tests/test_pi_listener.py`
- `tests/integration/test_claude_adapter_live.py`
- `tests/integration/test_pi_adapter_live.py`

No other file may be read or changed without leader approval. Core files are reference-only.

## Non-goals

- Do not change protocol schemas, server routing, authentication, or core command semantics.
- Do not add automatic/default subscriptions.
- Do not add Pi or Claude installed-extension commands or tools.
- Do not persist subscriptions across an explicit listener stop or process restart.
- Do not add remote listener-control behavior; the bridge is local and private.
- Do not add model-callable subscription controls.

## Exact requirements

1. Add adapter CLI commands consistent with existing syntax:
   - `inter-agent-pi subscribe <channel> --name <connected-name>`
   - `inter-agent-pi unsubscribe <channel> --name <connected-name>`
   - `inter-agent-pi publish <channel> <text> [--from <name>]`
   - `inter-agent-pi channels [--json]`
   - `inter-agent-claude subscribe <channel>`
   - `inter-agent-claude unsubscribe <channel>`
   - `inter-agent-claude publish <channel> <text>`
   - `inter-agent-claude channels [--json]`
2. `subscribe` and `unsubscribe` must operate on the matching already-connected agent listener, not a new control or agent identity.
3. Implement a private local Unix-domain socket bridge between short-lived adapter commands and the listener in `src/inter_agent/adapters/control.py`:
   - Place sockets in a `control/` child of the configured adapter data directory.
   - Derive `control-<adapter>-<16 lowercase hex>.sock` from SHA-256 over adapter, normalized host, port, and routing identity so the Unix path remains bounded and endpoint/name collisions do not occur.
   - Create the control directory with mode `0700` and set the socket to `0600`.
   - Exchange one newline-delimited JSON request and response per connection. Requests contain only `op` (`subscribe` or `unsubscribe`) and `channel`; responses are the raw protocol acknowledgment or error object.
   - Reject malformed, oversized, or unsupported requests. Cap a request at 64 KiB and each connect/read/write wait at 2 seconds.
   - On listener startup, remove an existing socket only after a failed liveness probe; refuse to replace a live endpoint. On shutdown, unlink only the endpoint owned by that listener instance.
   - Never expose the shared secret through this bridge.
4. Pi listener selection is explicit through `--name`. Claude uses its existing current-session listener-state resolution. A missing, stale, reconnecting, or mismatched listener must fail cleanly without traceback.
5. Listeners must use the persistent `AgentSession` channel operations and retain the desired subscription set across transient WebSocket reconnections. Reapply desired subscriptions after reconnect before reporting normal readiness. Explicit listener shutdown clears the in-memory set.
6. Successful subscribe/unsubscribe commands print their protocol acknowledgment JSON. Protocol errors print an adapter-prefixed diagnostic to stderr and return nonzero.
7. `publish` delegates to `publish_to_channel` and `channels` delegates to `list_channels`, propagating endpoint/TLS/data-directory configuration exactly like existing commands.
8. Preserve adapter output conventions:
   - Pi publish success follows Pi's existing send/broadcast convention by printing the welcome envelope.
   - Claude publish success is silent.
   - Both channel-list commands print the raw `channels_ok` JSON.
9. Claude publish requires the active listener identity, ignores caller impersonation, and applies short-window duplicate suppression keyed by sender, channel, and text. Pi retains its existing user-level optional sender behavior.
10. Format Claude inbound channel delivery distinctly as `kind="channel" channel="<channel>"`; preserve existing direct/broadcast output byte-for-byte. Channel messages retain truncation, continuation lookup, receive deduplication, and sanitization behavior.
11. Pi listener output remains raw protocol JSON, so a channel message is distinguished by its `channel` field and lack of `to`.
12. Preserve reconnect deadlines, server auto-start behavior, permanent-error handling, listener ownership, status/disconnect behavior, and TLS propagation.
13. Update both Python adapter READMEs with implemented commands, output behavior, active-listener requirements, reconnect-only subscription retention, and no automatic subscriptions.
14. Add unit and live integration coverage for success, protocol errors, missing/stale listeners, reconnection resubscription, publish sender behavior, channel listing, distinct inbound formatting, duplicate suppression, and unchanged direct/broadcast behavior.

## Acceptance criteria

- Both adapter CLIs expose all four channel operations with the syntax and behavior above.
- Subscribe/unsubscribe affect the intended live agent session and survive a transient listener reconnect.
- An explicit disconnect/restart does not restore subscriptions automatically.
- Claude and Pi preserve their existing behavior outside channel operations.
- Local bridge files are private, bounded, and cleaned up safely.
- Relevant unit and live integration tests pass.
- The full repository gate passes.

## Checks

```bash
uv run pytest tests/test_adapter_control.py tests/test_claude_adapter_cli.py tests/test_claude_dedup.py tests/test_claude_listener.py tests/test_pi_adapter_cli.py tests/test_pi_listener.py tests/integration/test_claude_adapter_live.py tests/integration/test_pi_adapter_live.py
./run-checks.sh
```

## Executor stop conditions

Stop and report instead of improvising if the existing `AgentSession` API cannot support the bridge contract, the exact socket lifecycle is unsafe under an observed repository constraint, a core file appears to require modification, or any unlisted file is needed.

## End-to-end acceptance test (leader-run)

The leader runs this test after review; routine user action is not required.

1. Start the server and connect one Pi adapter listener and one Claude adapter listener.
2. Subscribe each listener to `updates` with its adapter command and confirm `subscribe_ok` JSON.
3. Run each adapter's `channels --json` and confirm both routing names appear under `updates`.
4. Publish to `updates` from each adapter and confirm the other listener receives a channel-distinct notification/frame while the publisher is excluded.
5. Restart the server without stopping the listeners and confirm they reconnect and remain subscribed.
6. Unsubscribe each listener and confirm `unsubscribe_ok`; publishing to the now-empty channel must fail with `UNKNOWN_CHANNEL`.
