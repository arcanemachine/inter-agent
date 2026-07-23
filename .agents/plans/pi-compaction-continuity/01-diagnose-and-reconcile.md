# Task 1 — Diagnose and preserve Pi continuity across compaction

Status: ready for dispatch

## Goal

Verify whether item 8c already resolved the previously observed Pi inter-agent disconnect around native compaction and `pi-supercompact`. Reproduce and classify any remaining failure, then implement only a narrow demonstrated inter-agent fix. If controlled native and supercompact paths pass, close this item as verification-only without adding reconciliation code. A connected identity must remain connected under the same routing name without overlap; an intentionally disconnected identity must remain disconnected. Preserve the same live extension process's unread mailbox without durable body storage.

## Context

Queued mailbox behavior is accepted in `7c208d2`, current Pi compatibility in `6a8ad43`, terminal user kick in `6210ed6`, and same-process reload mailbox continuity in `ad4de46`. The accepted investigation and behavior contract is authoritative in `docs/plans/important-closeout/01c-pi-compaction-continuity.md`. Native Pi compaction normally keeps the same extension runtime and emits `session_before_compact`/`session_compact`, not shutdown/start. `pi-supercompact` normally calls native `ctx.compact()`. Do not assume compaction should disconnect or reload; first identify the actual boundary.

## Allowed files to modify

Use the minimum subset required:

- `integrations/pi/src/index.ts`
- `integrations/pi/src/mailbox.ts`
- `integrations/pi/tests/extension-mailbox.test.ts`
- `integrations/pi/tests/mailbox.test.ts`
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`
- `tests/integration/test_pi_adapter_live.py`

Stop and report before modifying any other file. In particular, do not modify protocol/schema, Python core/helper/listener/server, Claude integration, package metadata/configuration, TLS/auth, packaging/extraction/publication, or `/workspace/projects/pi` in this packet.

## Additional files allowed to read

- `AGENTS.md`
- `integrations/pi/AGENTS.md`
- `.agents/PLAN.md`
- this packet
- `docs/plans/important-closeout/01c-pi-compaction-continuity.md`
- current versions of the allowed files
- `integrations/pi/package.json`, `tsconfig.json`, and `tsconfig.test.json`
- installed maintained Pi 0.81.1 lifecycle declarations/docs and the smallest relevant runtime source for native compaction/reload event order
- `/workspace/projects/pi/AGENTS.md`
- `/workspace/projects/pi/packages/pi-supercompact/AGENTS.md`
- `/workspace/projects/pi/packages/pi-supercompact/{README.md,CHANGELOG.md,package.json,src/index.ts,tests/index.test.ts}` strictly read-only to verify the existing supercompact lifecycle

Do not traverse or print `node_modules` or dependency trees. Do not expose credentials, secrets, private environment values, or mailbox/UAT marker bodies.

## Required investigation before implementation

1. Use isolated servers and unique names to reproduce separately:
   - native manual `/compact`;
   - native automatic/overflow-recovery compaction, or the closest faithful host-level trigger available;
   - `pi-supercompact` continuation;
   - ordinary `/reload` as a negative lifecycle control.
2. Capture only bounded lifecycle facts: `session_before_compact`, `session_compact`, any shutdown/start reason, listener exit/close classification, active generation, and server-visible name presence. Never capture secrets or bodies.
3. Classify the observed symptom as one of: listener child exit/race while runtime survives; runtime reload/replacement; `pi-supercompact` lifecycle defect; or non-reproducible after controlled native/supercompact runs.
4. Prefer an inter-agent extension fix. If evidence demonstrates responsibility in `pi-supercompact`, stop without modifying it and report the exact cross-repository boundary so the leader can prepare a separate packet. Do not speculate or alter its submodule/superproject.
5. If no disconnect reproduces after item 8c, verify mailbox/identity continuity and close this item as verification-only. Do not add speculative listener-health reconciliation, restart machinery, or product code. Add regression coverage or documentation only when it protects a concrete observed lifecycle contract.

## Locked behavior

1. A connected identity immediately before manual, automatic, overflow-recovery, or supercompact compaction remains under the same name afterward. No overlapping listeners, duplicate registration/delivery, or transient second identity.
2. Explicitly disconnected state remains disconnected. Compaction is never implicit connect.
3. Only if reproduction proves transcript rebuilding removes required connection intent, retain the minimum session-local desired descriptor needed by a demonstrated fix. Clear it on explicit disconnect, terminal kick, rename replacement as appropriate, shutdown, and true session replacement.
4. Only if reproduction proves a listener exits during compaction, reconcile health once after successful compaction: healthy intended listener → no action; intended listener exited → reconnect once through the existing path; cleared intent → no action. Failure is bounded/nonfatal with no retry loop.
5. Any demonstrated reconciliation callback must be generation-safe and cannot revive an old identity after disconnect, rename, kick, reload, replacement, shutdown, or a newer start.
6. Preserve unread entries, IDs, order, overflow state, delivery mode, and pending metadata-only notice state across healthy compaction and any same-runtime repair. Arrivals during compaction remain bounded and exactly once. Bodies remain hidden until explicit reads.
7. Do not serialize bodies to transcript/custom entries, message details, notices, settings, filesystem, server history, logs, errors, status, or notifications. Do not make mailbox state durable.
8. Preserve item-8c reload handoff semantics and clearing on quit/process exit/new/resume/fork/replacement. Do not use reload handoff for ordinary same-runtime compaction.
9. Preserve current Pi 0.81.1 API targeting, startup flag precedence, connect/rename/disconnect, terminal kick, helper resolution, transport/auth/TLS, channels, commands/tools, and formatting.

## Required tests

Behavior-level coverage must prove:

1. healthy listener across faithful `session_before_compact`/`session_compact` remains the identical child with no restart;
2. listener exit during compaction causes exactly one post-success restart under the intended same name;
3. old child close/error callbacks cannot clear or replace the repaired listener;
4. disconnect prevents restart; rename/stale callbacks preserve only newest intent; kick remains terminal until explicit host lifecycle action;
5. reconnect failure is bounded/nonfatal and does not retry indefinitely;
6. queued bodies/IDs, overflow ordering, delivery mode, pending notice coalescing, and arrivals during compaction survive exactly once and body-free until read;
7. failed/aborted compaction leaves existing connection/mailbox usable and does not run successful reconciliation;
8. reload still uses item-8c handoff, while quit/new/resume/fork/replacement clears; old IDs after terminated resume are missing;
9. no body persistence or diagnostic disclosure;
10. native and supercompact event order is represented faithfully, without source-string tests replacing behavior coverage.

## Checks

Run at minimum:

```bash
npm --prefix integrations/pi test
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
uv run pytest tests/test_pi_extension_static.py tests/integration/test_pi_adapter_live.py -q
./run-checks.sh
git diff --check
```

Remove `integrations/pi/dist`, `integrations/pi/dist-tests`, all investigation/UAT files, isolated state, processes, and unattached tmux sessions. Never kill a tmux session with attached clients.

## End-to-end acceptance

Use installed maintained Pi 0.81.1, an isolated server, unique ephemeral names/bodies, and an unprinted secret.

1. Connect and queue at least two unread messages; record only IDs/senders/kinds and prove notices are body-free.
2. Run native `/compact`; verify the name remains exactly once and unread IDs/bodies survive until selected/all explicit reads.
3. Queue more unread, run actual `pi-supercompact` continuation, and verify the same connection/mailbox properties exactly once.
4. Send during a controlled compaction window when practical; otherwise rely on timing behavior coverage and report the limitation.
5. Verify immediate mode remains immediate without duplicate turns.
6. Explicitly disconnect, compact, and prove no reconnect.
7. Reconnect; run `/reload` and terminated-session resume controls, proving reload continuity per item 8c and no body restoration after true termination/replacement.
8. Exit cleanly and prove no listener/handoff/resource remains.

If installed native/supercompact acceptance cannot be driven, report the precise environment limitation after running the faithful lifecycle harness. Never simulate a successful installed UAT.

## Completion report

Report reproduction/classification; bounded lifecycle evidence; exact changed files; connection-intent/reconciliation/generation design; mailbox/body-secrecy evidence; native/supercompact/reload/termination matrix; focused/package/full checks; installed UAT or exact limitation; cleanup; allowed-file compliance; limitations; and secret safety. Do not commit. Send all questions, blockers, status, and completion reports only to `inter-agent-leader`.
