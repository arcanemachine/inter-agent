# Pi compaction connection and mailbox continuity

Status: concrete; accepted direction; queued immediately after closeout item 8a

## Goal

Keep a live Pi inter-agent identity connected across native Pi compaction and the `pi-supercompact` workflow. Preserve the same live extension session's unread in-memory mailbox across those compactions and any listener restart they require, while keeping mailbox bodies unavailable after process termination or resumed/replaced sessions.

## Investigation findings

- A live `pi-supercompact` continuation was observed with the inter-agent tool state disconnected afterward; manual `/inter-agent connect` restored it. The disconnect is verified as an integration symptom, but its precise lifecycle trigger is not yet proven.
- Pi's native manual and automatic compaction paths rebuild the model context in the existing `AgentSession`. They emit `session_before_compact` and `session_compact`; they do not normally emit `session_shutdown` or `session_start` and do not intentionally replace the extension runtime.
- Native `AgentSession.compact()` temporarily disconnects Pi's internal agent-event subscription and reconnects it in `finally`. That internal subscription is unrelated to the inter-agent listener subprocess.
- `pi-supercompact` creates a canonical handoff, calls Pi's native `ctx.compact()`, observes `session_compact`, and restores context from its completion callback. Its documented and implemented happy path does not deliberately reload extensions.
- The Pi inter-agent extension stops its listener on `session_shutdown` and reconnects on `session_start` from the startup flag or transcript-restored connection state. It currently has no `session_compact` listener-health reconciliation.
- The queued mailbox introduced by closeout item 8 is extension-process memory. Under Pi's documented native compaction lifecycle it should remain intact automatically. Any fix must verify that behavior and must not serialize bodies into transcript entries, notices, settings, logs, or disk.

These findings mean the observed loss must not be described as an expected consequence of native compaction. The implementation task must first distinguish an unexpected listener exit/race from an undocumented runtime reload or wrapper-specific lifecycle transition, then fix the narrow proven boundary.

## Locked behavior

1. A Pi identity that is connected immediately before manual `/compact`, threshold compaction, overflow-recovery compaction, or `pi-supercompact` remains connected under the same routing name afterward.
2. Compaction must not create overlapping listeners, duplicate registrations, duplicate inbound delivery, or a transient second identity.
3. A Pi session that is intentionally disconnected before compaction remains disconnected. Compaction is not implicit connect.
4. Preserve unread mailbox entries, IDs, arrival order, overflow state, delivery mode, and pending metadata-only notice state across native compaction and a compaction-related listener restart within the same live extension process.
5. Messages arriving during compaction remain bounded and are neither lost nor delivered twice. Queued bodies remain hidden until explicit read; immediate-mode behavior retains its existing active-turn bounds.
6. Explicit quit, process termination, new session, resume of a terminated session, fork, and ordinary extension reload retain the accepted mailbox-clearing behavior. Do not make mailbox storage durable merely to survive compaction.
7. If investigation proves that a host-specific compaction path replaces the extension runtime, preserve mailbox state only through a bounded same-process, compaction-scoped in-memory handoff that can distinguish compaction from ordinary reload/session replacement. Clear that handoff on quit, new, resume, fork, timeout, failed/aborted compaction, and process exit.
8. Never persist mailbox bodies in Pi transcript entries, custom-message details, settings, filesystem state, server history, logs, errors, status text, or notifications.
9. Retain a session-local desired connection descriptor while connected so post-compaction health reconciliation does not depend on old transcript entries remaining in rebuilt model context. Clear intent on explicit disconnect and lifecycle termination.
10. After successful compaction, reconcile listener health once:
    - if the intended listener is healthy, do nothing;
    - if connection intent remains but the listener exited, reconnect once through the existing server-discovery and listener-start path;
    - if explicit disconnect cleared intent, do nothing.
11. A failed reconciliation emits one bounded actionable diagnostic and leaves Pi usable. Do not add an unbounded retry loop or automatic server/core redesign.
12. Every asynchronous reconciliation or handoff callback is generation-safe and cannot revive a stale identity after disconnect, rename, reload, session replacement, shutdown, or a newer listener start.
13. Preserve startup `--inter-agent` precedence, manual connect/rename/disconnect semantics, endpoint and state-directory defaults, helper resolution, auth, TLS, listener command protocol, pub/sub, and host-specific formatting.

## Required investigation before implementation

1. Reproduce separately with unique routing names against an isolated server:
   - native manual `/compact`;
   - a native automatic-compaction event or a faithful host-level trigger;
   - `pi-supercompact` continuation;
   - ordinary `/reload` as a negative lifecycle control.
2. Capture only bounded lifecycle facts: `session_before_compact`, `session_compact`, `session_shutdown` reason, `session_start` reason, listener child exit/close classification, active generation, and server-visible routing-name presence. Do not capture secrets or message bodies.
3. Determine whether the observed failure is:
   - an inter-agent listener child exit or close race while the extension runtime survives;
   - an extension runtime reload/session replacement;
   - a `pi-supercompact` integration defect;
   - or a non-reproducible prior environment event.
4. Prefer an inter-agent Pi extension fix. Change `pi-supercompact` only if reproduction demonstrates that its lifecycle contract causes or fails to expose the transition and the fix cannot be safely contained in inter-agent.
5. If cross-repository work is demonstrated, prepare separate bounded packets and obey the `pi-supercompact` child-repository then superproject commit order. Do not couple the packages speculatively.

## Expected implementation boundary

The eventual active packet should normally be limited to the smallest necessary subset of:

- `integrations/pi/src/index.ts`
- `integrations/pi/src/mailbox.ts`, if created by item 8
- `integrations/pi/tests/extension-mailbox.test.ts`, if created by item 8
- `integrations/pi/tests/mailbox.test.ts`, if created by item 8
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`
- `tests/integration/test_pi_adapter_live.py`
- package-local TypeScript test configuration already introduced by item 8

Only demonstrated cross-extension responsibility may add a separately reviewed change in:

- `/workspace/projects/pi/packages/pi-supercompact/src/index.ts`
- `/workspace/projects/pi/packages/pi-supercompact/tests/index.test.ts`
- `/workspace/projects/pi/packages/pi-supercompact/README.md`
- `/workspace/projects/pi/packages/pi-supercompact/CHANGELOG.md`
- the `/workspace/projects/pi` superproject submodule pointer

No protocol/schema, core transport, Python listener/helper, server, auth/TLS semantics, channel semantics, Claude integration, durable mailbox, packaging extraction, or publication changes are expected.

## Test requirements

Behavior-level TypeScript coverage must include:

1. healthy connected listener plus `session_before_compact`/`session_compact` remains the same listener with no restart;
2. listener exit during compaction triggers exactly one post-compaction restart under the same identity;
3. late close/error callbacks from the old child cannot clear or replace the restarted listener;
4. explicit disconnect before compaction prevents restart;
5. rename before or during a stale callback preserves only the newest intended identity;
6. reconnect failure is bounded and nonfatal;
7. queued mailbox bodies and IDs survive healthy compaction and compaction-related listener restart without entering notices or logs;
8. arrivals during compaction are retained exactly once and remain within the 128-message bound;
9. delivery-mode state and pending notice coalescing remain valid across compaction;
10. failed or aborted compaction leaves the existing connection and mailbox usable;
11. ordinary reload, new, resume, fork, shutdown, and process replacement clear the mailbox and stale compaction handoff;
12. an old displayed ID after terminated-session resume is missing/not unread;
13. no body persistence to transcript, settings, disk, diagnostics, or cross-session state;
14. native compaction and `pi-supercompact` event order are represented faithfully in the integration harness.

Retain focused Python/static coverage for public lifecycle and security boundaries, but do not substitute source-string assertions for behavior tests.

## End-to-end acceptance

Use a real installed Pi, an isolated inter-agent server, and controlled unique marker bodies without printing shared secrets.

1. Connect a receiver and queue at least two messages through item 8 behavior.
2. Run native `/compact`; verify the routing name never disappears or is restored without overlap, unread IDs remain selectable, and bodies remain absent until explicit read.
3. Read one message and confirm exactly that body is returned and removed.
4. Queue another message and run `pi-supercompact` with continuation; verify connection continuity and that all remaining unread IDs/bodies survive exactly once.
5. Send a message during a controlled compaction window when practical; otherwise rely on behavior-level timing coverage and record the limitation.
6. Exercise immediate mode across compaction and confirm it neither becomes queued nor triggers duplicate turns.
7. Explicitly disconnect, compact, and verify no reconnect occurs.
8. Reconnect, then perform ordinary reload and terminated-session resume controls. Verify accepted identity behavior is preserved, but unread mailbox bodies are not restored after the terminated/replaced session boundary.
9. Confirm final shutdown removes the listener and leaves no process-local handoff capable of restoring old bodies.

## Acceptance criteria

- The exact observed disconnect path is reproduced or explicitly classified as non-reproducible after native and `pi-supercompact` controls.
- Connected identity survives every verified compaction path with no duplicate listener or delivery.
- Explicitly disconnected state remains disconnected.
- The item 8 mailbox survives same-process compaction and compaction-related listener repair without durable body storage.
- Terminated-session resume and ordinary replacement boundaries do not restore unread bodies.
- Failure diagnostics are bounded, generation-safe, and nonfatal.
- Existing transport, auth, TLS, helper resolution, startup identity, commands, channels, and host behavior remain unchanged.
- Package-local behavior tests, focused live/static tests, real installed-Pi acceptance, and `./run-checks.sh` pass.
