# Task 1 — Preserve Pi unread mailbox through same-process reload

Status: ready for dispatch

## Goal

Preserve the exact bounded unread Pi mailbox through a same-process extension `/reload`, using a one-use in-memory handoff. Preserve body secrecy and all current mailbox behavior. A terminated Pi process/session, true replacement, `new`, `resume`, `fork`, or failed/incompatible reload must start empty.

## Context

Item 8 queued mailbox behavior was accepted in `7c208d2`; item 8a aligned it with current Pi in `6a8ad43`; item 8b was accepted in `6210ed6`. Current reload intentionally clears the mailbox. This task changes only the same-process reload boundary. The accepted design is authoritative in `docs/plans/important-closeout/01b-pi-mailbox-reload-continuity.md`; do not broaden or redesign it.

## Allowed files to modify

- `integrations/pi/src/index.ts`
- `integrations/pi/src/mailbox.ts`
- `integrations/pi/tests/mailbox.test.ts`
- `integrations/pi/tests/extension-mailbox.test.ts`
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`

Modify the minimum subset required. Stop and report before modifying any other file, including package metadata, test configuration, Python source, protocol/schema, server state, Claude integration, or documentation outside this list.

## Additional files allowed to read

- `AGENTS.md`
- `integrations/pi/AGENTS.md`
- `docs/plans/important-closeout/01b-pi-mailbox-reload-continuity.md`
- `integrations/pi/package.json`
- `integrations/pi/tsconfig.json`
- `integrations/pi/tsconfig.test.json`
- current installed Pi extension API lifecycle declarations/documentation only as needed to verify reload/session reasons and a process-global one-use carrier

Do not traverse or print `node_modules` or dependency trees. Do not expose shared secrets, credentials, private environment values, registry tokens, mailbox body fixtures, or UAT marker bodies.

## Non-goals

- No durable mailbox/body storage in transcript entries, custom entries, message details, settings, environment, command arguments, filesystem, logs, errors, notifications, or server history.
- No protocol/schema, Python helper/listener/server, Claude, TLS, kick, compaction-continuity, packaging/extraction, publication, or global-update work.
- No change to 128-entry capacity, ID/dedup/overflow/read semantics, immediate delivery behavior, transport/auth, startup identity, connection replacement, pub/sub, or current reload-clearing behavior outside the precise same-process handoff.
- No ordinary module-local handoff variable that fails when Pi reload instantiates a fresh extension module.

## Requirements

1. On `session_shutdown` with reason exactly `reload`, after the old listener stops accepting arrivals and before old runtime mailbox state clears, export a complete bounded snapshot of unread entries and state required to preserve subsequent read/overflow behavior.
2. Preserve message ID, resolved sender name, body, direct/broadcast/channel kind, optional channel/target, stable arrival order, capacity, and overflow state. Do not exceed 128, duplicate, reorder, resurrect read/evicted entries, or preserve immediate-mode in-flight bodies.
3. Store the snapshot only in the smallest verified process-global private carrier that survives Pi extension module replacement. The carrier must be versioned, generation/session-scoped, expiring, and one-use. Do not expose it through settings, transcript, Pi context entries, tools, notices, diagnostics, or public/global ordinary keys.
4. Consume atomically only on the matching next `session_start` with reason exactly `reload`; clear the carrier before restoring. Missing, malformed, stale, expired, incompatible-version, mismatched-generation/session, canceled, interrupted, or repeated starts must fail closed, clear state, and disclose no body.
5. Any shutdown/start reason `quit`, `new`, `resume`, or `fork` clears both mailbox and pending handoff. A process exit naturally loses it. A terminated-session resume must report old unread IDs missing/not unread even when historical notices/read results remain in the transcript.
6. Restore messages as queued unread entries regardless of the configuration-selected mode for future arrivals. Recompute session-only delivery mode from current configuration; do not persist its override.
7. Keep existing listener disconnect/reconnect inside one runtime in-memory and independent of the handoff. Reload restoration must not start a second listener, change routing identity, or alter startup `--inter-agent`/transcript restoration.
8. Preserve metadata-only awareness notices and no duplicate turns: restore at most one latest complete body-free pending notice only when old runtime had not entered a complete notice; do not notify merely because a complete notice had already entered context. Cancel/invalidate every old timer, immediate burst, listener callback, and flush before handoff so none can emit into the new runtime.
9. Keep all bodies absent from notices, renderer metadata/details, transcript entries, settings, diagnostics, logs, errors, notifications, static fixture content, and filesystem. Bodies appear only through explicit `inter_agent_read_messages` or existing immediate delivery for new arrivals.
10. Update only necessary evergreen Pi documentation, explicitly distinguishing same-process reload preservation from terminated-session/replacement clearing.

## Required tests

Add behavior-level TypeScript coverage for:

1. direct/broadcast/channel messages surviving reload with same IDs, bodies, and arrival order, and explicit selected/all reads;
2. pre-reload reads and evictions staying absent after reload; 128-entry overflow state and next eviction staying correct;
3. export ordering after listener stop, one-use atomic import, no duplication, stale callbacks/timers/flushes unable to affect new runtime;
4. missing, malformed, expired, incompatible, mismatched, canceled/interrupted, and repeated lifecycle cases failing closed without body disclosure;
5. `quit`, `new`, `resume`, `fork`, replacement, and terminated-session resume clearing mailbox/handoff and reporting old IDs missing;
6. ordinary listener disconnect/reconnect remaining in-memory without carrier use;
7. config delivery mode reapplying after reload while restored unread remain queued; pending immediate bodies remaining unpreserved;
8. exactly one body-free awareness notice when one was pending, and none duplicated after an already-delivered notice;
9. one listener/reconnect path and unchanged routing identity;
10. static secrecy/tool-boundary assertions in addition to—not instead of—lifecycle tests.

## Checks

Run at minimum:

```bash
npm --prefix integrations/pi test
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
uv run pytest tests/test_pi_extension_static.py -q
./run-checks.sh
git diff --check
```

Run any existing package lifecycle harness needed to exercise actual Pi reload events. Remove generated `integrations/pi/dist`, `integrations/pi/dist-tests`, UAT files, processes, and tmux sessions after verification; do not kill a tmux session with attached clients.

## End-to-end acceptance

Use an isolated installed Pi plus real server, unique ephemeral marker bodies, and a secret never printed.

1. Connect a receiver; queue direct, broadcast, and channel messages. Record only IDs/senders/kinds and confirm awareness notices contain no bodies.
2. Run actual `/reload` before reading. Confirm exactly one routing identity reconnects, no overlap/second listener, and the same unread IDs remain.
3. Read one selected ID and then all remaining IDs, confirming bodies appear only through explicit reads and preserve arrival order.
4. Verify no duplicate awareness turn for a notice already entered before reload; verify one latest body-free notice for a pre-reload pending notice.
5. Exercise a session-only immediate-mode change, reload, and confirm configuration re-applies for future arrivals while restored unread remains readable.
6. Terminate Pi, resume its old transcript in a new process, and confirm a final unread ID is missing/not unread and its body is unavailable.
7. Exit all resources cleanly; confirm no listener, carrier, temp artifact, secret, or body leak remains.

If the available installed Pi environment cannot drive native `/reload`/resume, report the exact environmental limitation after running the verified lifecycle harness; do not simulate a successful installed UAT or broaden scope.

## Completion report

Report changed files; carrier mechanism and verification that it survives module replacement; lifecycle/reason matrix; body-secrecy and notice behavior; connection/identity evidence; focused/package/static/full checks; installed UAT or precise limitation; cleanup; allowed-file confirmation; limitations; and secret safety. Do not commit.
