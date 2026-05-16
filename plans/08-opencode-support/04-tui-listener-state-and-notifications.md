# TUI Listener, State, and Notifications

Extra Phase: 8 — OpenCode Support

## Purpose

Implement the OpenCode TUI plugin behavior that keeps a session connected to the inter-agent bus and surfaces incoming messages safely to the user.

## Scope

- Long-lived listener owned by the TUI plugin.
- Lifecycle cleanup through OpenCode's TUI plugin APIs.
- Connection state persistence.
- Duplicate listener prevention within one OpenCode TUI process.
- Notifications, toasts, status display, and inbox behavior.

## Work

1. Implement the TUI plugin entry point in `src/tui.ts`.
   - Load config.
   - Initialize state.
   - Register commands.
   - Restore persisted connection state only if auto-connect is enabled by design.
   - Register cleanup through `api.lifecycle.onDispose()`.
   - Use `api.lifecycle.signal` to stop background work.

2. Implement listener ownership.
   - One active listener per OpenCode TUI plugin instance.
   - Store listener state in a module-local controller object.
   - Treat repeated connect requests as idempotent when name, label, host, and port match.
   - Return a clear error when a different connection is already active.

3. Implement reconnect behavior.
   - Reconnect on transient network failures with bounded exponential backoff.
   - Start at approximately 250 ms and cap near 4 s, following the Claude adapter pattern.
   - Add jitter to avoid synchronized reconnect loops.
   - Stop on permanent protocol errors.
   - Stop immediately when `api.lifecycle.signal` is aborted.

4. Persist connection state with OpenCode KV.
   - Store configured host, port, name, label, connected flag, and last successful connection timestamp.
   - Do not store the shared token in OpenCode KV.
   - Keep inbox metadata small and bounded.
   - Recover defensively from malformed or stale KV entries.

5. Add a recent-message inbox.
   - Store recent inbound message metadata and full text up to a bounded count.
   - Include message ID, sender, direct/broadcast kind, target, timestamp, truncation status, and text.
   - Expose an inbox command for users to inspect recent messages.
   - Use the inbox as the continuation path when notifications are truncated.

6. Surface incoming messages.
   - Use `api.attention.notify()` for attention/desktop notification behavior.
   - Use `api.ui.toast()` for in-app visibility.
   - Truncate notification/toast bodies to a safe configured length.
   - Include sender and direct/broadcast metadata in the title.
   - Store full text in the inbox when truncated.

7. Add status display if OpenCode exposes a stable slot/status mechanism.
   - Prefer a lightweight status-bar/sidebar slot if available and stable.
   - If status slots are too invasive, provide `/inter-agent-status` and toasts instead.
   - Do not block core listener work on status display polish.

8. Avoid automatic prompt mutation in the first implementation.
   - OpenCode supports prompt append indirectly, but the TUI plugin API does not expose a simple `api.prompt.append()` method.
   - Do not auto-submit prompts in response to peer messages.
   - Consider a later explicit command such as `/inter-agent-reply` or `/inter-agent-use-last` if prompt insertion is accepted.

9. Echo outgoing messages locally.
   - When a TUI command sends or broadcasts, add a non-triggering local toast or inbox entry so the user can see what was sent.
   - Keep outgoing echoes visually distinct from incoming messages.

10. Clean up on plugin disposal.
   - Abort reconnect loops.
   - Close WebSocket connections.
   - Unregister commands and event handlers through OpenCode-provided disposers.
   - Persist disconnected state only for explicit disconnect, not for plugin reload unless the design requires it.

## Acceptance criteria

- The TUI plugin can connect to the inter-agent bus and receive direct messages.
- The TUI plugin can receive broadcasts.
- The listener stops cleanly when OpenCode unloads or disposes the plugin.
- Transient server restarts trigger bounded reconnect behavior.
- Permanent protocol errors stop the listener and notify the user.
- Incoming messages produce bounded attention notifications and toasts.
- Long messages have a continuation path through the inbox.
- Connection state survives OpenCode session reload according to the accepted auto-connect setting.

## Files likely to change

- `integrations/opencode/src/tui.ts`
- `integrations/opencode/src/state.ts`
- `integrations/opencode/src/inbox.ts`
- `integrations/opencode/src/format.ts`
- `integrations/opencode/src/client.ts`
- `integrations/opencode/README.md`

## Checks

```bash
cd integrations/opencode
npm run typecheck
npm run build
```

Manual validation against OpenCode is required before this item is complete.
