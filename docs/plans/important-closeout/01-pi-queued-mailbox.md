# Pi queued mailbox

Status: active as closeout queue item 8

## Goal

Make inbound Pi inter-agent bodies queued by default so a receiving agent can continue independent reasoning and decide when to read messages. Support explicit immediate delivery without weakening bounds, untrusted-peer guidance, or existing transport behavior.

## Locked behavior

- Queue direct, broadcast, and channel messages consistently.
- Default delivery mode: `queued`.
- Alternative delivery mode: `immediate`.
- Initial mode comes from `interAgent.deliveryMode` in Pi settings.
- Add `/inter-agent delivery <queued|immediate>` with autocomplete. It changes only the current Pi session and does not rewrite settings.
- Mode changes affect future arrivals only. Existing queued messages remain queued.
- Mailbox state is in TypeScript extension memory. It survives listener disconnect/reconnect inside the same Pi extension session and clears on Pi session/process replacement.
- Store at most 128 unread messages. Evict the oldest unread message on overflow and emit an explicit warning.
- Use the server-issued `msg_id` as the selection ID.
- Never include queued message bodies in mailbox notices, notifications, render metadata intended for notices, logs, or errors.
- Register one model-callable tool, `inter_agent_read_messages`.
- With no IDs, the tool reads all unread messages. With IDs, it returns all valid requested messages and reports missing/already-read IDs without failing valid selections.
- Reading removes the selected messages. Tool results remain in ordinary Pi history.
- Configuration `interAgent.mailboxNoticeDebounceMs` controls notice coalescing; integer range 0–5000, default 0, recommended opt-in 200. It affects notices only, never storage.
- Queued-mode mailbox notices use non-steering follow-up delivery and trigger a mailbox-awareness turn without exposing bodies. While Pi is active they wait until the current run and queued continuations settle; a burst waiting behind active work triggers at most one new turn.
- Notice guidance tells the agent that unread metadata is available and to decide whether an explicit read advances current authorized work. It must not prescribe acknowledgment, reply, or any other outbound action.
- Immediate-mode bodies use non-steering follow-up delivery. They may trigger a turn when Pi is idle, but while Pi is active they wait until the current run and queued continuations settle.
- Every timer and asynchronous delivery captures the current extension runtime generation and must no-op after reload, session replacement, or shutdown.

## Required data model

Use explicit concrete types, not `any`:

- `DeliveryMode = "queued" | "immediate"`.
- `MessageKind = "direct" | "broadcast" | "channel"`.
- `MailboxMessage` contains `msgId`, resolved sender routing name, text, kind, optional channel, optional target, and arrival order/time needed for stable output.
- Preserve insertion order for read-all and overflow eviction.
- Reject or safely diagnose inbound `msg` frames without a non-empty string `msg_id`; never create an unselectable queued body.
- Duplicate live `msg_id` values must not overwrite a different unread body silently. Retain the first and warn, or reject the duplicate with a bounded warning.

## Notice behavior

Each emitted mailbox notice describes the complete current unread set using metadata only:

- total unread count;
- every unread message ID and sender;
- grouped sender counts where useful;
- message kind and channel may be shown, but never body text.

Use an `inter-agent-mailbox` custom message/renderer distinct from normal `inter-agent-message` bodies. Compact rendering shows unread count grouped by sender. Expanded rendering lists every ID, sender, kind, and channel when present. The model-visible notice must contain the complete selection metadata even if compact human rendering is shorter.

A notice must use Pi's `followUp` delivery mode with `triggerTurn: true`, never steering or aborting. It starts a mailbox-awareness turn when Pi is idle; while Pi is active it waits until the current run and queued continuations settle. Coalesce a burst waiting behind active work to the latest complete mailbox snapshot and trigger exactly one later awareness turn. Debounce must cancel/replace the pending timer safely and retain only the latest full mailbox snapshot. If more messages arrive before that snapshot is delivered, replace it rather than enqueueing stale intermediate notices. Clear timers and pending notice work on `session_shutdown`, and reject callbacks whose captured runtime generation is stale.

Persisted transcript notices are snapshots, not mailbox storage. On reload/restart the in-memory mailbox is empty; the read tool must report that previously shown IDs are no longer unread rather than reconstructing bodies from session history.

## Immediate mode

Immediate mode preserves the current bounded notification/context behavior:

- direct, broadcast, and channel formatting remain distinct;
- existing collaboration-input and reply-decision guidance remains attached, without prescribing any canned acknowledgment;
- use `deliverAs: "followUp"` with `triggerTurn: true`, never `steer` or `ctx.abort()`;
- when Pi is active, bodies wait for the current run and queued continuations to settle before delivery;
- a burst waiting behind one active run triggers at most one new turn, with any remaining bodies delivered as follow-up context rather than separate turn triggers;
- immediate messages never enter the unread mailbox.

## Configuration validation

- Invalid `deliveryMode` falls back to `queued` and emits one actionable warning after UI context is available.
- Invalid debounce values fall back to 0 and emit one actionable warning.
- Global settings load first; trusted project settings retain current override precedence.
- Do not add a debounce command.
- Document exact keys, defaults, bounds, lifecycle, and examples.

## Tool output

`inter_agent_read_messages` parameters:

- optional `ids`: unique array of message-ID strings, with a reasonable per-call bound no greater than the mailbox limit.

Return selected messages in mailbox arrival order. For every returned message include ID, sender, kind, optional channel/target, and full body. Include a concise missing-ID section after valid messages. Reading an empty mailbox is a successful result. Tool output and details must use bounded structures and existing truncation practices; individual bodies remain subject to existing inbound transport/message limits.

The tool reads only. It must not send, acknowledge, reply, subscribe, publish, or infer a response.

## Non-goals

- No protocol/schema/core/Python changes.
- No durable mailbox across Pi restarts.
- No subjects, priorities, generic metadata, request/reply correlation, pagination, or server-side history.
- No automatic message reading or reply generation.
- No mailbox implementation for Claude Code in this item.
- No changes to channel membership or publication semantics.

## Expected current files

The activation packet should normally allow the minimum necessary subset of:

- `integrations/pi/src/index.ts`
- `integrations/pi/README.md`
- `integrations/pi/package.json`
- `tests/test_pi_extension_static.py`
- new package-local TypeScript tests/test configuration if introduced
- root public docs only after behavior exists

Do not modify Python/core/spec files without a demonstrated packet deficiency and leader approval.

## Test requirements

Cover at minimum:

1. queued is the default with no config;
2. valid global/project configuration and session command override;
3. invalid config fallback/warning;
4. direct, broadcast, and channel bodies are absent from notices/model context until read;
5. complete metadata notice and compact/expanded rendering;
6. read-all, selected reads, multiple IDs, mixed valid/missing IDs, empty mailbox;
7. read removal and stable arrival order;
8. immediate future delivery with old queued messages retained;
9. switch back to queued;
10. 128-message overflow evicts oldest and warns;
11. reconnect preserves queue; session restart clears it;
12. debounce 0, burst coalescing, range validation, and timer cleanup;
13. malformed/duplicate IDs do not silently lose unread bodies;
14. no autonomous send/read/reply behavior;
15. queued notices use follow-up delivery, provoke a metadata-only mailbox-awareness turn, wait behind active work, trigger at most once per waiting burst, and never steer or abort;
16. immediate delivery waits behind active work, triggers at most once per waiting burst, and never steers or aborts;
17. stale timer/async callbacks after reload, session replacement, or shutdown cannot emit notices or bodies.

Prefer behavior-level TypeScript tests over brittle source-string assertions. Retain static assertions for security/tool-surface boundaries where appropriate.

## Focused checks

At activation, adapt exact commands to the extracted or current package layout. In the current monorepo they must include:

```bash
uv run pytest tests/test_pi_extension_static.py tests/test_pi_listener.py tests/integration/test_pi_adapter_live.py -q
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check src/index.ts README.md package.json
./run-checks.sh
git diff --check
```

## End-to-end acceptance

With two Pi sessions and one channel subscriber:

1. Start receiver in default queued mode.
2. Send direct, broadcast, and channel messages containing unique secret-marker text.
3. Confirm receiver gets IDs/senders/count/kinds and begins one mailbox-awareness turn without another user prompt, but none of the marker bodies enters model context before read.
4. Confirm the awareness guidance leaves the read decision to the agent and does not prescribe acknowledgment or outbound action.
5. Read one selected ID; confirm only that body appears and is removed.
6. Read all; confirm remaining bodies appear in arrival order and mailbox becomes empty.
7. Queue one message, switch to immediate, receive another; confirm old stays queued and new arrives immediately.
8. Disconnect/reconnect listener and confirm unread state remains. Restart the Pi session and confirm it clears.
9. Exercise overflow and debounce with automated coverage when manual generation is impractical.

Record observed results; steps written in docs are not evidence by themselves.
