# Task packet: pub/sub channels Phase 1 core protocol

## Goal

Implement the accepted in-memory pub/sub channel protocol in the Python core, protocol contract, conformance suite, and present-behavior documentation.

## Allowed files to read and modify

- `spec/asyncapi.yaml`
- `spec/error-codes.md`
- `spec/schemas/envelope.json`
- `spec/schemas/error.json`
- `spec/schemas/msg.json`
- `spec/schemas/welcome.json`
- `spec/schemas/subscribe.json` *(new)*
- `spec/schemas/subscribe_ok.json` *(new)*
- `spec/schemas/unsubscribe.json` *(new)*
- `spec/schemas/unsubscribe_ok.json` *(new)*
- `spec/schemas/publish.json` *(new)*
- `spec/schemas/channels.json` *(new)*
- `spec/schemas/channels_ok.json` *(new)*
- `spec/examples/welcome.json`
- `spec/examples/subscribe.json` *(new)*
- `spec/examples/subscribe_ok.json` *(new)*
- `spec/examples/unsubscribe.json` *(new)*
- `spec/examples/unsubscribe_ok.json` *(new)*
- `spec/examples/publish.json` *(new)*
- `spec/examples/channels.json` *(new)*
- `spec/examples/channels_ok.json` *(new)*
- `src/inter_agent/core/errors.py`
- `src/inter_agent/core/server.py`
- `src/inter_agent/core/shared.py`
- `tests/conformance/helpers.py`
- `tests/conformance/test_capabilities.py`
- `tests/conformance/test_channels.py` *(new)*
- `tests/conformance/test_connection_and_payload_limits.py`
- `tests/conformance/test_error_semantics.py`
- `tests/conformance/test_message_size_boundaries.py`
- `tests/test_spec_examples.py`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ROADMAP.md`

If implementation or configured checks require another file, stop and report the required scope expansion to the leader.

## Non-goals

- Core publish/channel-list command helpers or CLI entry points.
- Changing `iter_client_frames` or adding a long-running client command channel.
- Pi or Claude Python adapter commands.
- Pi extension or Claude Code plugin commands, tools, notifications, or packaging.
- Automatic/default subscriptions.
- Durable messages, history, ACLs, ownership, federation, or remote security changes.
- Changes to direct send, broadcast, custom, list, kick, or shutdown semantics except membership cleanup during kick/disconnect.
- Moving channel routing into middleware as part of this phase.

## Exact requirements

### Protocol operations

1. `subscribe` requires `channel` and is accepted only from an authenticated agent session.
2. A valid new subscription creates membership and returns `{"op":"subscribe_ok","channel":"<name>"}`.
3. Repeating an existing subscription is idempotent and returns the same success response without consuming another subscription.
4. `unsubscribe` requires `channel` and is accepted only from an authenticated agent session.
5. A valid active membership is removed and returns `{"op":"unsubscribe_ok","channel":"<name>"}`.
6. Unsubscribing without an active membership returns `NOT_SUBSCRIBED`.
7. Empty channels are removed immediately.
8. `publish` requires `channel` and string `text`, and is accepted from authenticated agent and control sessions.
9. Publishing to no active channel returns `UNKNOWN_CHANNEL`.
10. Publish text uses `broadcast_text_max`; invalid text returns `BAD_TEXT`, and oversized UTF-8 encoded text returns `TEXT_TOO_LARGE`.
11. A publish delivers one `msg` to every currently subscribed agent except the publisher. Delivery includes `channel`, omits `to`, and includes the normal `msg_id`, `from`, `from_name`, `text`, and `ts` fields.
12. Publisher identity follows current send/broadcast behavior: `from_name` defaults to the connection name and may be overridden by the request.
13. Publish sends no success acknowledgment.
14. `channels` is control-only. Agent use returns `BAD_ROLE`.
15. `channels_ok.channels` is sorted by channel name; each entry contains `name` and a sorted list of subscriber routing names.
16. Control sessions cannot subscribe or unsubscribe; those attempts return `BAD_ROLE`.
17. Disconnect, `bye`, and kick remove every membership for the departing session and remove newly empty channels.

### Validation and limits

1. Channel names match `[a-z0-9][a-z0-9-]{0,39}` and must also fit `channel_name_max` UTF-8 bytes.
2. Invalid channel values return `BAD_CHANNEL`.
3. Extend `Limits` with:
   - `channel_name_max` from `INTER_AGENT_CHANNEL_NAME_MAX`, default 40;
   - `subscriptions_max` from `INTER_AGENT_SUBSCRIPTIONS_MAX`, default 32;
   - `channels_max` from `INTER_AGENT_CHANNELS_MAX`, default 256.
4. A new membership over the session subscription limit returns `CHANNEL_LIMIT_REACHED`.
5. Creating a new channel over the server channel limit returns `CHANNEL_LIMIT_REACHED`.
6. Joining an existing channel does not consume a server channel slot.
7. Validate and mutate membership state safely relative to connection registration and cleanup.

### Contract and capability

1. Add schemas and examples named exactly after each new `op`.
2. Register every operation and response in `spec/asyncapi.yaml`.
3. Extend `msg.json` with optional `channel`; existing direct and broadcast examples remain valid.
4. Add the four accepted canonical errors to the enum, error schema, and error-code documentation: `BAD_CHANNEL`, `CHANNEL_LIMIT_REACHED`, `NOT_SUBSCRIBED`, `UNKNOWN_CHANNEL`.
5. Change the advertised and specified `welcome.capabilities.channels` value to `true`.
6. Keep `core.version` at `0.1`.

### Documentation

Update current-behavior documentation only after implementation exists:

- `README.md`: describe core channel support without claiming adapter/extension commands exist.
- `ARCHITECTURE.md`: describe membership/routing, limits, operations, diagnostics, and core surfaces that actually exist.
- `SECURITY.md`: describe channels within the existing trust model and explicitly exclude privacy/ACL/history claims.
- `ROADMAP.md`: mark only Phase 1 as implemented and retain Phases 2–4 as sequenced follow-up work, explicitly including both Pi and Claude extension UX.

## Tests

Add black-box conformance coverage for:

- subscribe success and idempotency;
- unsubscribe success and `NOT_SUBSCRIBED`;
- invalid channel types, syntax, and configured byte limit;
- agent and control publish;
- delivery fields and sender exclusion;
- multiple subscribers and unsubscribed non-delivery;
- `UNKNOWN_CHANNEL`;
- publish text type and exact/over UTF-8 byte boundary;
- per-session subscription and server channel limits;
- existing-channel joins at the server channel limit;
- sorted control diagnostics and agent `BAD_ROLE`;
- control subscribe/unsubscribe `BAD_ROLE`;
- disconnect, bye, and kick cleanup;
- unchanged direct and broadcast behavior through the existing suite;
- schema/example validation and capability advertisement.

Prefer extending the listed focused test files over unrelated changes.

## Acceptance criteria

- Every exact requirement is implemented.
- All new schemas and examples validate through the repository's existing spec test.
- Channel state does not retain disconnected sessions or empty channels.
- Existing direct, broadcast, custom, list, kick, and shutdown tests remain green.
- User-facing docs do not claim unavailable adapter or extension UX.
- `./run-checks.sh` passes.

## Checks

Run from the project root:

```bash
./run-checks.sh
```

Report changed files, the full-gate result, remaining concerns, and blockers. Do not commit.

## User acceptance test

After leader review and commit:

1. Start `uv run inter-agent-server` in one terminal.
2. Connect two authenticated agent WebSocket clients and one control client.
3. Subscribe both agents to `build` and observe `subscribe_ok`.
4. Publish `hello` to `build` from the control client and observe one channel `msg` on each agent.
5. Unsubscribe one agent, publish again, and confirm only the subscribed agent receives it.
6. Request `channels` from control and confirm the sorted channel/subscriber response.
