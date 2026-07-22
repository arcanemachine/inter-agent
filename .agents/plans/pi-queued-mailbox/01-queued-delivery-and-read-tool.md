# Task 1 — Pi queued mailbox and explicit immediate delivery

Status: active

## Goal

Make inbound Pi direct, broadcast, and channel message bodies queue by default so the receiving agent can continue independently and choose when to read them. Add an explicit immediate mode without weakening message bounds, untrusted-peer guidance, lifecycle isolation, or existing transport behavior.

## Context

The accepted product behavior is defined in `docs/plans/important-closeout/01-pi-queued-mailbox.md`. The Pi extension currently delivers inbound bodies immediately as `inter-agent-message` custom messages. This task changes only the Pi host extension: mailbox state remains bounded in TypeScript memory, notices contain metadata only, and one model-callable read tool reveals and removes selected unread bodies.

Closeout priority insertion 7a is implemented in `37aec5b`. This packet is closeout queue item 8; installed cross-adapter TLS acceptance remains next.

## Allowed files to modify

- `integrations/pi/src/index.ts`
- `integrations/pi/src/mailbox.ts` (new, only if used to isolate cohesive testable mailbox behavior)
- `integrations/pi/.gitignore` (only to ignore package-local generated test output)
- `integrations/pi/README.md`
- `integrations/pi/package.json`
- `integrations/pi/package-lock.json`
- `integrations/pi/tsconfig.json`
- `integrations/pi/tsconfig.test.json` (new, only if required by the test runner)
- `integrations/pi/tests/mailbox.test.ts` (new)
- `integrations/pi/tests/extension-mailbox.test.ts` (new, only if behavior wiring needs a separate harness)
- `tests/test_pi_extension_static.py`

## Additional files allowed to read

- `integrations/pi/AGENTS.md`
- `tests/test_pi_listener.py`
- `tests/integration/test_pi_adapter_live.py`
- `src/inter_agent/adapters/pi/listener.py`
- `src/inter_agent/adapters/pi/commands.py`
- `docs/plans/important-closeout/01-pi-queued-mailbox.md`
- the installed Pi extension API type declarations and documentation needed to verify `sendMessage`, `registerMessageRenderer`, `registerTool`, `session_start`, `session_shutdown`, `agent_settled`, `isIdle`, and pending-message semantics

Do not read or modify other files without reporting why this packet is insufficient. Do not expose shared secrets, private environment values, or test marker bodies outside the explicitly selected read-tool result and controlled acceptance assertions.

## Non-goals

- No protocol/schema, core, Python helper/adapter, server, auth, TLS, endpoint-default, listener-connect/reconnect, channel membership, or publication changes.
- No durable mailbox, transcript reconstruction, server-side history, pagination, subjects, priorities, generic metadata, acknowledgments, correlation IDs, or Claude Code mailbox.
- No automatic read, send, broadcast, reply, subscribe, publish, or model-generated acknowledgment.
- No steering, active-turn abort, canned peer response, or peer-triggered privileged action.
- No debounce slash command and no settings rewrite.
- No packaging/repository extraction, external publication, credentials, remote changes, or unrelated formatting/documentation churn.

## Locked behavior and data model

1. Define concrete types without `any`:
   - `DeliveryMode = "queued" | "immediate"`.
   - `MessageKind = "direct" | "broadcast" | "channel"`.
   - `MailboxMessage` with `msgId`, resolved sender routing name, body text, kind, optional channel, optional target, and stable arrival order/time.
2. Queue direct, broadcast, and channel messages consistently. Default delivery mode is `queued`; alternative mode is `immediate`.
3. Load initial mode from `interAgent.deliveryMode`. Global settings load first and trusted project settings retain the extension's current override precedence.
4. Add `/inter-agent delivery <queued|immediate>` with autocomplete. It changes only the current Pi extension session, never rewrites settings, and affects future arrivals only. Existing unread messages remain queued.
5. Mailbox state lives only in TypeScript extension memory. It survives listener disconnect/reconnect within the same extension session and clears on Pi session/process or extension-runtime replacement, reload, and shutdown.
6. Store at most 128 unread messages in insertion order. On the 129th unread arrival, evict exactly the oldest unread message and emit one explicit bounded warning for that eviction event without including any body.
7. Use the server-issued `msg_id` as the selection ID. Reject or safely diagnose inbound `msg` frames lacking a non-empty string `msg_id`; never create an unselectable queued message.
8. A duplicate live `msg_id` must never overwrite or replace the first unread body silently. Retain the first and emit a bounded metadata-only warning, or reject the duplicate with that warning.
9. Never include queued bodies in mailbox notices, notifications, notice renderer details/metadata, logs, errors, status, autocomplete, or command output. Bodies may appear only through a valid explicit read-tool result or immediate-mode body delivery.
10. Preserve the current resolved sender routing-name behavior and distinct direct/broadcast/channel metadata. Individual bodies remain subject to existing inbound transport/message limits.

## Queued notices

11. Register a custom `inter-agent-mailbox` message and renderer distinct from body-bearing `inter-agent-message`.
12. Every emitted notice is a full metadata-only snapshot of the current unread set. Model-visible content includes total unread count and every unread ID and sender; kind plus channel may be included. Grouped sender counts may supplement but never replace complete selection metadata. Include neutral guidance that the read tool is available and the agent should decide whether reading advances current authorized work; never prescribe acknowledgment, reply, or another outbound action.
13. Compact human rendering shows unread count grouped by sender. Expanded rendering lists every unread ID, sender, kind, and channel when present. Renderer details must contain metadata only, never bodies.
14. Deliver notices with `deliverAs: "followUp"` and `triggerTurn: true`, never `steer` and never `ctx.abort()`. A notice provokes a metadata-only mailbox-awareness turn when Pi is idle. While Pi is active it waits until the current run and queued continuations settle. A burst waiting behind active work triggers at most one new turn; later complete snapshot metadata becomes non-triggering follow-up context rather than a separate turn trigger.
15. Configuration `interAgent.mailboxNoticeDebounceMs` accepts integers from 0 through 5000 inclusive; default is 0 and documented recommended opt-in is 200. It affects notice coalescing only, never storage.
16. Debounce cancels/replaces the pending timer and retains only the latest complete mailbox snapshot. A burst awaiting notice delivery must not enqueue stale intermediate snapshots.
17. Every timer and asynchronous delivery captures the current extension runtime generation and no-ops if stale after reload, session replacement, or shutdown. Clear all pending notice timers/work on `session_shutdown`.
18. Persisted transcript notices are snapshots, not storage. Never reconstruct unread bodies from history; after replacement/reload, reads of old displayed IDs report them missing/not unread.

## Read tool

19. Register exactly one new model-callable tool named `inter_agent_read_messages`. It reads only and must not send, acknowledge, reply, subscribe, publish, infer a response, or trigger a model turn.
20. Parameters contain optional `ids`: a unique array of non-empty message-ID strings with maximum 128 items. With no `ids`, read all unread messages. An explicitly empty array is a successful empty selection.
21. Return valid selected messages in mailbox arrival order, regardless of requested-ID order. Each returned message includes ID, sender, kind, optional channel/target, and full body.
22. Remove only successfully selected messages. Mixed valid and missing/already-read IDs return all valid selections and a concise missing-ID section without failing the call. Reading an empty mailbox succeeds.
23. After removal, subsequent notices/snapshots describe the complete remaining unread set; do not expose removed bodies in notice metadata.
24. Tool content and details use bounded structures and existing truncation practices. Tool results remain in ordinary Pi history, which is the intended durable record of explicitly read bodies.

## Immediate mode

25. Immediate messages never enter the unread mailbox.
26. Preserve current direct, broadcast, and channel formatting plus collaboration-input and reply-decision guidance, without prescribing canned acknowledgment.
27. Deliver immediate bodies with `deliverAs: "followUp"` and `triggerTurn: true`; never use `steer` and never call `ctx.abort()`.
28. While Pi is active, immediate bodies wait until the current run and all queued continuations settle. A burst waiting behind one active run triggers at most one new turn; remaining bodies become follow-up context rather than separate turn triggers.
29. Switching from queued to immediate leaves existing unread messages intact and routes only future arrivals immediately. Switching back routes future arrivals to the mailbox.
30. Immediate asynchronous callbacks also capture the runtime generation and no-op when stale.

## Configuration and diagnostics

31. Invalid `deliveryMode` falls back to `queued`. Invalid debounce values (non-integer or outside 0–5000) fall back to 0. Emit exactly one actionable warning for each invalid configured key after UI context is available, without exposing unrelated settings or secrets.
32. Document exact keys, values, defaults, bounds, global/project precedence, lifecycle, examples, delivery command, read tool, overflow behavior, notice/body separation, and the recommended opt-in debounce of 200 ms.
33. Keep current config path resolution, runtime resolution precedence, endpoint/auth/TLS propagation, listener identity, pub/sub behavior, startup `--inter-agent` behavior, and connection-state semantics unchanged.

## Tests

34. Add behavior-level package-local TypeScript tests. Use the smallest maintainable test setup; prefer Node's built-in test runner plus the existing TypeScript toolchain or a minimal dev-only runner over a production dependency. Static source assertions alone are insufficient for mailbox state, timers, lifecycle, and body-secrecy behavior.
35. Cover at minimum:
   - queued default; valid global/project config and session command override; invalid fallback/warnings;
   - direct, broadcast, and channel bodies absent from notices/model context until read;
   - complete metadata snapshots and compact/expanded rendering;
   - read-all, selected/multiple/mixed/empty reads, arrival ordering, and removal;
   - immediate future delivery with old queued messages retained, then switching back;
   - 128-message eviction and warning;
   - disconnect/reconnect preservation and session/runtime replacement clearing;
   - debounce 0, burst coalescing, bounds, timer replacement, and shutdown cleanup;
   - malformed and duplicate IDs;
   - no autonomous send/read/reply behavior;
   - queued follow-up notices provoke a metadata-only awareness turn, wait behind active work, trigger at most once per waiting burst, and never steer/abort;
   - immediate waiting/follow-up behavior with at most one trigger per waiting burst and no steer/abort;
   - stale timer/async callbacks after reload, replacement, or shutdown.
36. Retain focused static assertions only for security and public tool/command surfaces where they add value. Do not replace behavior tests with large brittle source-string assertions.
37. Add a package `test` command and ensure new test/config files are included in typechecking/format checks as appropriate. Keep new dependencies dev-only and update the lockfile if the manifest changes.
38. Keep all changes inside the allowed-file boundary.

## Acceptance criteria

- Queued is the verified default and no queued body reaches model-visible notice content or notice rendering/details before explicit read.
- Direct, broadcast, and channel messages share one bounded 128-entry mailbox with stable IDs/order, safe malformed/duplicate handling, and explicit oldest eviction.
- Metadata notices are complete, coalesced, body-free, generation-safe, and provoke one non-steering mailbox-awareness turn per idle arrival/coalesced active burst.
- The read tool correctly handles all/selected/mixed/missing/empty reads, reveals only selected bodies, removes them, and performs no outbound action.
- Immediate mode preserves current body/guidance formatting, uses non-steering follow-up delivery, waits behind active work, triggers at most once per waiting burst, and does not enter the mailbox.
- Mode switching, reconnect, session replacement, reload, shutdown, config validation, and stale callbacks match the locked lifecycle.
- Startup identity flag, existing commands/tools, transport/auth/TLS, pub/sub, and listener behavior remain intact.
- Behavior-level TypeScript tests, focused Python/static/live tests, package checks, end-to-end acceptance, and the full repository gate pass.
- `git diff --check` is clean and only allowed files are modified.

## Checks

Run at minimum:

```bash
npm --prefix integrations/pi test
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check "src/**/*.ts" "tests/**/*.ts" README.md package.json tsconfig.json "tsconfig*.json"
uv run pytest tests/test_pi_extension_static.py tests/test_pi_listener.py tests/integration/test_pi_adapter_live.py -q
./run-checks.sh
git diff --check
```

If an optional listed test/config glob does not exist, adapt the Prettier invocation without weakening coverage. Remove ignored generated build output before reporting completion.

## End-to-end acceptance test

Use two real Pi sessions and one channel subscriber on an isolated real server. Use unique marker bodies only inside controlled sends and explicit read assertions; never print shared-secret values.

1. Start the receiver in default queued mode and confirm its identity on the bus.
2. Send unique direct, broadcast, and subscribed-channel messages from another session/helper.
3. Confirm the receiver receives IDs, senders, count, and kinds and begins one mailbox-awareness turn without another user prompt, but none of the marker bodies appears in notice content/details, notifications, or model context before read.
4. Confirm the notice leaves the read decision to the agent and does not prescribe acknowledgment or outbound action; an active-work burst waits and provokes at most one later turn.
5. Read one selected ID; confirm only that body appears and is removed. Read all; confirm remaining bodies appear in arrival order and mailbox becomes empty.
6. Queue one message, switch to immediate, then receive another. Confirm the old message stays unread while the new body arrives through follow-up delivery.
7. While Pi is active, send an immediate burst. Confirm it waits, triggers at most one later turn, and never steers or aborts.
8. Switch back to queued and confirm future arrivals queue.
9. Disconnect/reconnect the listener and confirm unread state remains. Reload or replace the Pi session and confirm mailbox state clears and old notice IDs read as missing/not unread.
10. Exercise malformed/duplicate IDs, overflow, debounce/coalescing, and stale-generation behavior through automated behavior coverage when manual generation is impractical.
11. Exit all sessions cleanly and confirm listeners disappear.

Record actual observations and any environment limitation. Written steps or mocks alone are not complete acceptance evidence; use automated behavior coverage for timing/overflow cases that are impractical to generate manually.

## Completion report

Report changed files, architecture/test-harness choice, config and command behavior, body-secrecy evidence, queue/read/immediate/lifecycle results, exact focused/package/full checks, real Pi/server observations, timing cases covered automatically, environment limitations, secret-safety confirmation, and allowed-file confirmation. Do not commit.
