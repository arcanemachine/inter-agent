# Pub/sub channels design seed

Status: seed; not implemented; not active.

## Purpose

Add protocol-level pub/sub channels so agents can coordinate around named topics without using global broadcast for every multi-recipient message.

Channels should be implemented in the core protocol and adapters before new host integrations are built, so OpenCode and Codex can target the settled behavior from the start.

## Current baseline

Implemented messaging operations are:

- `send` — direct message to one target agent name;
- `broadcast` — message to all other connected agent sessions;
- `custom` — pass-through extension envelope;
- `list` — connected agent sessions.

The server already tracks authenticated connections, session IDs, names, roles, labels, and capabilities. Routing is in `src/inter_agent/core/server.py`; conformance tests live under `tests/conformance/`; protocol schemas/examples live under `spec/`.

## Candidate behavior

Initial channel support should be minimal and explicit:

1. Agent sessions subscribe to named channels.
2. Agent sessions unsubscribe from named channels.
3. Agent or control sessions publish a message to a channel.
4. Published channel messages are delivered to subscribed agent sessions, excluding the sender by default unless an explicit echo behavior is accepted.
5. Control clients can list channels and/or channel subscribers for diagnostics.
6. Direct send and broadcast semantics remain unchanged.

## Candidate protocol operations

Exact names and payload shapes must be finalized in a concrete design pass. Likely operations:

- `subscribe` with `channel`;
- `subscribe_ok` with `channel`;
- `unsubscribe` with `channel`;
- `unsubscribe_ok` with `channel`;
- `publish` with `channel`, `text`, and optional `from_name`;
- delivered `msg` includes `channel` and omits `to`;
- `channels` / `channels_ok` or `channel_list` / `channel_list_ok` for diagnostics.

Prefer names that match schema filenames and existing protocol style.

## Naming and limits

Design pass must choose validation rules and limits before implementation:

- channel name syntax;
- maximum channel name length;
- maximum subscriptions per connection;
- maximum channels per server;
- publish text limit, likely aligned with broadcast limit;
- whether empty channels are retained or removed immediately.

Recommended starting point: lowercase routing-like names with `/` or `.` only if there is a clear use case. Keep validation simple for conformance tests.

## Security and policy

Initial scope should use the existing authenticated bus trust model:

- no per-channel ACLs;
- no private channel claims beyond shared-secret authentication;
- no durable history;
- no cross-server federation;
- no model-visible privilege semantics.

Inbound channel messages remain untrusted collaboration context and do not override host instructions or policy.

## Adapter UX questions

A concrete design pass should decide Pi and Claude Code UX together:

- slash commands for subscribe/unsubscribe/publish/list;
- LLM-callable tools for publish and channel list;
- notification format for channel messages;
- whether connect should auto-subscribe to any default channel;
- whether broadcast should be documented as distinct from channel publish.

Recommended default: no automatic channel subscriptions in the first slice.

## Required concrete planning pass

Before coding, assign a bounded worker task to inspect these files and produce a concrete plan:

- `spec/asyncapi.yaml`
- `spec/schemas/*.json`
- `spec/examples/*.json`
- `spec/error-codes.md`
- `src/inter_agent/core/server.py`
- `src/inter_agent/core/send.py`
- `src/inter_agent/core/list.py`
- `src/inter_agent/adapters/pi/`
- `src/inter_agent/adapters/claude/`
- `tests/conformance/`
- relevant adapter CLI/static tests

The output should specify exact schema files, error codes if any, implementation functions, tests, docs, and acceptance criteria.

## Acceptance criteria for the future implementation

- Protocol schemas/examples validate.
- Conformance tests cover subscribe, unsubscribe, publish, delivery, sender exclusion or accepted echo behavior, unknown/invalid channel errors, and cleanup on disconnect.
- Core command helpers and Pi/Claude adapters expose channel operations consistently.
- README, ARCHITECTURE, SECURITY, and integration docs describe implemented behavior only.
- `./run-checks.sh` passes.
