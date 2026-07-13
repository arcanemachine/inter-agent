# Pub/sub channels implementation plan

Status: Phases 1–2 implemented; Phases 3–4 are concrete, sequenced follow-up work.

## Purpose

Add protocol-level pub/sub channels so authenticated sessions can coordinate around named topics without using global broadcast for every multi-recipient message. Direct send, broadcast, and custom routing remain unchanged.

Channel behavior must settle in the core protocol before new host integrations are implemented. Existing Pi and Claude Code integrations receive channel UX in explicit follow-up phases.

## Accepted protocol design

### Operations

- `subscribe` — agent session requests membership with `channel`.
- `subscribe_ok` — confirms membership with `channel`.
- `unsubscribe` — agent session removes membership with `channel`.
- `unsubscribe_ok` — confirms removal with `channel`.
- `publish` — agent or control session publishes `text` to `channel`; optional `from_name` follows existing send/broadcast behavior.
- `channels` — control-only diagnostic request.
- `channels_ok` — returns active channels and subscribers.

A published channel message is delivered as `msg` with `channel` and without `to`. The publisher is excluded, including when it is subscribed. Publish has no success acknowledgment, matching broadcast behavior.

Subscriptions are agent-only. Control sessions may publish and query channels but do not subscribe or receive channel deliveries. There are no automatic subscriptions.

### Diagnostic response

`channels_ok.channels` is sorted by channel name. Each entry has `name` and `subscribers`; subscriber routing names are sorted.

```json
{
  "op": "channels_ok",
  "channels": [
    {
      "name": "build",
      "subscribers": ["agent-a", "agent-b"]
    }
  ]
}
```

### Naming, lifecycle, and limits

- Channel names match `[a-z0-9][a-z0-9-]{0,39}`.
- The default channel-name limit is 40 UTF-8 bytes.
- The default maximum is 32 subscriptions per agent session.
- The default maximum is 256 active channels per server.
- Publish text uses the broadcast UTF-8 byte limit.
- Empty channels are removed immediately.
- Subscribing to an existing membership is idempotent and returns `subscribe_ok`.
- Unsubscribing from an absent membership returns `NOT_SUBSCRIBED`.
- Publishing to a nonexistent or empty channel returns `UNKNOWN_CHANNEL`.
- Disconnect and kick cleanup remove all memberships held by the session.

Configuration uses `INTER_AGENT_CHANNEL_NAME_MAX`, `INTER_AGENT_SUBSCRIPTIONS_MAX`, and `INTER_AGENT_CHANNELS_MAX` with the defaults above.

### Errors

Add these canonical error codes:

- `BAD_CHANNEL` — channel is missing, non-string, empty, syntactically invalid, or over the configured name limit.
- `CHANNEL_LIMIT_REACHED` — subscribing would exceed either the per-session subscription limit or server active-channel limit.
- `NOT_SUBSCRIBED` — the session requested unsubscribe without an active membership.
- `UNKNOWN_CHANNEL` — publish names no active channel.

Existing errors remain applicable: `BAD_ROLE` for role-restricted operations, `BAD_TEXT` for non-string publish text, and `TEXT_TOO_LARGE` for publish text over the broadcast limit.

### Capability

`welcome.capabilities.channels` changes from `false` to `true` when the core implementation lands. `core.version` remains `0.1` unless implementation review identifies an accepted compatibility reason to change it.

### Security model

Initial channels use the existing authenticated, localhost, single-user trust model:

- no channel ACLs or ownership claims;
- no durable history;
- no federation;
- no model-visible privilege semantics;
- inbound channel messages remain untrusted collaboration context.

## Phases

### Phase 1 — core protocol (implemented)

Implemented schemas, examples, AsyncAPI references, canonical errors, limits, in-memory membership/routing, cleanup, capability advertisement, black-box conformance coverage, and present-behavior documentation.

Phase 1 itself did not add command helpers, adapter commands, extension tools, or automatic subscriptions.

### Phase 2 — core command APIs (implemented)

Phase 2 adds typed core APIs and command surfaces for publish and channel diagnostics. A long-running `AgentSession` control surface lets a connected agent subscribe, unsubscribe, and publish without creating a separate identity. The implementation covers parsing, protocol errors, TLS/config propagation, and live operation.

### Phase 3 — Python host adapters

Expose consistent subscribe, unsubscribe, publish, and channel-list behavior through the Pi and Claude Python adapters. Preserve each adapter's connection lifecycle, output conventions, duplicate suppression, and message continuation behavior. Format inbound channel messages distinctly from direct and broadcast messages.

Activate this phase only after Phase 2 and a focused adapter inventory.

### Phase 4 — installed extension UX

Add user-facing channel functionality to both existing integrations:

- Pi extension commands and LLM-callable tools;
- Claude Code plugin commands/skills or tools supported by its integration surface;
- channel-aware notifications and documentation for both;
- static packaging tests and live acceptance coverage.

No integration auto-subscribes to a default channel. This phase is required follow-up work and must not be dropped when core support is completed.

Activate this phase only after Phase 3 and a focused inventory of `integrations/pi/` and `integrations/claude-code/`.

## Whole-feature acceptance criteria

- Protocol schemas and examples validate.
- Conformance tests cover subscribe, idempotent subscribe, unsubscribe, absent-membership errors, publish, sender exclusion, invalid/unknown channels, limits, diagnostics, and disconnect/kick cleanup.
- Direct send, broadcast, and custom semantics remain unchanged.
- Core command APIs and Pi/Claude adapters expose channel operations consistently.
- Pi and Claude Code extension UX exposes the accepted channel operations without automatic subscriptions.
- README, ARCHITECTURE, SECURITY, integration docs, and roadmap describe only behavior that exists at each phase.
- `./run-checks.sh` passes for every implementation phase.
