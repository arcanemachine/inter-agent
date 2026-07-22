# Pi mailbox continuity across extension reload

Status: concrete; accepted direction; queued immediately after closeout item 8b

## Goal

Preserve the unread Pi queued mailbox across a same-process `/reload` of extensions without persisting message bodies to transcript entries, settings, disk, or server history. Continue clearing unread bodies across Pi process termination and real session replacement boundaries.

## Context

Closeout item 8 introduces a bounded mailbox whose bodies live only in the active Pi extension runtime. Its initial lifecycle intentionally clears on `session_shutdown`, including reload. Pi `/reload` emits `session_shutdown` with reason `reload`, rebuilds the extension runtime in the same process, then emits `session_start` with reason `reload`.

This item changes only that reload boundary. It depends on accepted item-8 mailbox behavior and must be dispatched as a separate bounded task to a different eligible executor after preceding active work is complete.

## Locked behavior

1. Preserve unread mailbox entries across same-process extension `/reload`:
   - server-issued message ID;
   - resolved sender routing name;
   - full body;
   - direct/broadcast/channel kind;
   - optional channel and target;
   - stable arrival order and overflow state needed for subsequent eviction/read behavior.
2. Preserve at most the existing 128 unread entries. Reload must not increase the bound, duplicate entries, change IDs, reorder bodies, or resurrect previously read/evicted messages.
3. After reload, `inter_agent_read_messages` reads selected/all restored messages exactly as before reload. Mixed valid/missing semantics and removal remain unchanged.
4. Preserve bodies only through a bounded one-use same-process memory handoff owned by the Pi extension process. Do not place bodies in:
   - Pi transcript/custom entries or message details;
   - mailbox notices or renderer metadata;
   - global/project settings;
   - environment variables or command arguments;
   - filesystem state, logs, errors, notifications, or server history.
5. Export the handoff only for `session_shutdown` reason `reload`, after the listener has stopped accepting new arrivals and before the old mailbox is cleared.
6. Consume the handoff only on the matching next `session_start` reason `reload`. Consumption is atomic and clears the carrier immediately.
7. A shutdown/start reason of `quit`, `new`, `resume`, or `fork` clears any mailbox and any pending reload handoff. A Pi process exit naturally destroys the in-memory handoff.
8. Resuming a terminated Pi session starts with an empty mailbox even if its transcript still contains old mailbox notices or explicit read results. Old unread IDs report missing/not unread.
9. A failed, canceled, interrupted, or incomplete reload cannot make mailbox bodies available to an unrelated later session. Use a versioned, expiring, generation-scoped carrier and fail closed by clearing incompatible/stale state.
10. Do not use an ordinary module variable if Pi's reload loader can instantiate a fresh module copy. Use the smallest verified process-global mechanism that survives extension-runtime replacement while remaining inaccessible outside this extension's private symbol/key.
11. Preserve current connection behavior independently: startup `--inter-agent` or transcript-restored connection state continues to reconnect through the existing `session_start` path. Mailbox restoration must not start a second listener or change routing identity.
12. Listener disconnect/reconnect inside one runtime continues to preserve the mailbox without using the reload handoff.
13. Session-only `/inter-agent delivery <queued|immediate>` override does not become durable. After reload, initial delivery mode is recomputed from current configuration. Restored unread entries remain queued and readable regardless of the mode selected for future arrivals.
14. Preserve notice/body separation and avoid duplicate awareness turns:
   - if a queued arrival had not yet produced its required awareness notice before reload, restore one latest complete metadata-only notice and trigger at most one awareness turn;
   - if a complete notice already entered Pi context, do not trigger another turn solely because reload occurred;
   - any restored notice describes the complete current unread set and contains no body.
15. Cancel old-runtime timers and callbacks. No stale pre-reload timer, immediate burst, listener callback, or notice flush may emit into the new runtime.
16. Pending immediate-mode bodies are not unread mailbox entries and are not preserved by this task. Reload retains the existing behavior for in-flight immediate delivery.
17. Preserve overflow warnings, duplicate/malformed handling, config validation, command/tool schemas, transport/auth/TLS, helper resolution, startup identity, pub/sub, and host formatting.

## Expected implementation boundary

The eventual active packet should normally be limited to the smallest necessary subset of:

- `integrations/pi/src/index.ts`
- `integrations/pi/src/mailbox.ts`
- `integrations/pi/tests/mailbox.test.ts`
- `integrations/pi/tests/extension-mailbox.test.ts`, if item 8 creates it or reload wiring needs a separate harness
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`
- package-local TypeScript test configuration introduced by item 8

Do not modify protocol/schema, Python core/helper/listener, server state, Claude integration, durable storage, compaction mechanics, packaging extraction, or publication behavior.

## Required tests

Behavior-level TypeScript coverage must include:

1. queue multiple direct/broadcast/channel messages, reload, and read the same IDs/bodies in original arrival order;
2. selected reads before reload do not return afterward, while remaining unread entries survive;
3. overflow/eviction before reload retains exactly the bounded remaining 128 entries and correct next eviction;
4. reload export occurs after listener stop and cannot miss a late accepted frame;
5. handoff is one-use and cannot duplicate entries on repeated `session_start` callbacks;
6. incompatible version, expired state, missing handoff, malformed carrier, and mismatched generation/session fail closed without body disclosure;
7. `quit`, process replacement, `new`, `resume`, and `fork` clear mailbox/handoff; old IDs are missing;
8. transcript mailbox notices never reconstruct bodies;
9. ordinary listener disconnect/reconnect remains in-memory and does not use or clear the reload handoff;
10. configured delivery mode is reapplied after reload while restored unread messages remain queued;
11. one pending pre-reload awareness notice is restored exactly once with the latest body-free snapshot;
12. a notice already delivered before reload is not duplicated solely by reload;
13. old timers/flushes/callbacks no-op after handoff and cannot emit notices or bodies;
14. connection restart remains single-listener and independent of mailbox import;
15. no body appears in handoff diagnostics, transcript entries, notice content/details, notifications, logs, settings, or filesystem fixtures.

Static assertions may protect the no-persistence/public-tool boundary but must not replace lifecycle behavior tests.

## End-to-end acceptance

Use a real installed Pi and isolated server with controlled unique marker bodies. Do not print shared secrets.

1. Connect the receiver, queue direct, broadcast, and channel messages, and record only their IDs/senders/kinds.
2. Verify the awareness notice is body-free, then run `/reload` before reading the bodies.
3. Confirm the inter-agent identity reconnects once with no overlap and the mailbox reports the same unread IDs.
4. Read one selected ID, then all remaining IDs; confirm exact bodies appear only through those reads and retain arrival order.
5. Queue another message, allow its awareness notice to enter context, reload, and confirm reload alone does not produce a duplicate awareness turn.
6. Queue a message while the receiver is in session-only immediate mode, switch as necessary to leave an unread entry, reload, and confirm configured mode is reapplied while the old unread entry remains readable.
7. Queue a final unread marker, terminate Pi completely, resume the old transcript in a new process, and confirm the marker ID is missing/not unread and its body is unavailable.
8. Exit cleanly and confirm no listener or reload carrier remains.

## Acceptance criteria

- Same-process `/reload` preserves the exact bounded unread mailbox without durable body storage.
- Terminated-session resume and true session replacement do not restore unread bodies.
- Reload neither duplicates nor loses awareness notices and never leaks a body before explicit read.
- Session-only delivery override resets to configuration; restored unread entries remain readable.
- Listener identity/reconnect remains single-instance and unchanged.
- Lifecycle, stale-callback, secrecy, focused package/static/live tests, installed Pi acceptance, and `./run-checks.sh` pass.
