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

### Phase 3 — Python host adapters (implemented)

Phase 3 exposes consistent subscribe, unsubscribe, publish, and channel-list behavior through the Pi and Claude Python adapters. It preserves each adapter's connection lifecycle and output conventions, retains desired memberships across transient reconnects, and formats inbound channel messages distinctly from direct and broadcast messages. A private local listener-control socket lets short-lived membership commands reuse the existing agent session.

### Phase 4 — installed extension UX (implemented)

The Pi and Claude Code installed integrations provide user-invoked subscribe/unsubscribe/publish commands, explicit-user read-only channel diagnostics, and channel-aware notifications/context. Subscription control, publish, and channel diagnostics are deliberately not exposed as LLM-callable tools, memberships are not persisted across listener restart, process restart, host reload, or resumed sessions, and nothing subscribes, publishes, or polls automatically. Channel diagnostics use a short-lived authenticated server connection and do not require or change the active listener.

Short-lived publishers use the active listener routing name. Because the protocol excludes the publishing connection while adapter publishers use separate control connections, each adapter listener suppresses channel deliveries whose `from_name` matches its own routing name. This preserves identity-level publisher exclusion in installed host UX without changing server routing semantics.

Cross-adapter live acceptance proves both adapter listeners can subscribe to one server, both diagnostics surfaces report the same subscribers, Claude publication reaches Pi, Pi publication reaches Claude, and neither listener surfaces its own routing name's publication. Static installed-surface coverage, Pi package checks, strict Claude plugin validation, conformance/spec checks, and the full repository gate complete Phase 4 acceptance.

## Whole-feature acceptance criteria

- Protocol schemas and examples validate.
- Conformance tests cover subscribe, idempotent subscribe, unsubscribe, absent-membership errors, publish, sender exclusion, invalid/unknown channels, limits, diagnostics, and disconnect/kick cleanup.
- Direct send, broadcast, and custom semantics remain unchanged.
- Core command APIs and Pi/Claude adapters expose channel operations consistently.
- Pi user subscription UX and any later accepted Claude Code plugin channel UX expose only their implemented operations without automatic subscriptions.
- README, ARCHITECTURE, SECURITY, integration docs, and roadmap describe only behavior that exists at each phase.
- `./run-checks.sh` passes for every implementation phase.
