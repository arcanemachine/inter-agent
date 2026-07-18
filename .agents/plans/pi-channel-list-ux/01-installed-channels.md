# Task 1 — Pi installed channel-list UX

Status: active

## Goal

Expose the existing Pi adapter channel diagnostics through an explicit user-invoked, read-only Pi command:

```text
/inter-agent channels
```

The extension must use the existing short-lived authenticated helper operation, present useful channel/subscriber diagnostics, preserve the no-autonomous/no-LLM-tool boundary, and leave Python/protocol behavior unchanged.

## Context

The Python adapter already implements `inter-agent-pi channels --json`. It opens a short-lived authenticated connection to the configured server, prints raw `channels_ok` JSON, and succeeds when the response operation is `channels_ok`. It does not require the current Pi listener. Each channel entry has `name` and sorted subscriber routing names; an empty array is successful.

## Allowed files to modify

- `integrations/pi/src/index.ts`
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ROADMAP.md`
- `docs/plans/pubsub-channels/00-design-seed.md`

## Additional files allowed to read

- `integrations/pi/AGENTS.md`
- `integrations/pi/package.json`
- `src/inter_agent/adapters/pi/cli.py`
- `src/inter_agent/adapters/pi/commands.py`
- `tests/test_pi_adapter_cli.py`
- `tests/integration/test_pi_adapter_live.py`

Do not read or modify other files without recording why this packet is insufficient.

## Non-goals

- No Python, protocol, schema, conformance, server, or packaging changes.
- No listener lifecycle or channel membership changes.
- No LLM-callable channel-list tool.
- No automatic polling, post-operation diagnostics, inferred diagnostics, monitoring, or peer-triggered listing.
- No changes to publish, subscribe, unsubscribe, direct, or broadcast behavior.

## Requirements

1. Add `channels` to `/inter-agent` autocomplete and grouped usage.
2. Dispatch `/inter-agent channels` from the grouped command handler.
3. Reject non-whitespace arguments with `usage: /inter-agent channels`.
4. Invoke the existing helper exactly with `channels` and `--json`.
5. Do not require `listenerReady` or `currentConnection`; diagnostics use a short-lived authenticated server connection.
6. Parse `channels_ok` JSON and show current channel names with subscriber routing names in a bounded Pi notification.
7. Treat an empty `channels` array as success and report that no channels currently have subscribers.
8. Treat malformed/non-`channels_ok` output as an invalid response; surface helper failures through the existing bounded diagnostic path.
9. Keep the command read-only and explicit-user-only. Do not register `inter_agent_channels`, add it to tool/system-prompt guidance, call it from another operation, poll, or run it from peer-message handling.
10. Document command syntax, short-lived authenticated lifecycle, no-listener behavior, read-only semantics, output meaning, empty success, failure behavior, and no-tool/no-autonomous boundaries.
11. Update Phase 4 documentation to implemented only after this slice and the cross-integration acceptance in item 4 are correctly distinguished: item 3 completes the installed UX surfaces, while item 4 remains the Phase 4 closeout gate.
12. Add focused static tests for autocomplete, usage, dispatch, no-argument parsing, exact helper args, no listener gate, success formatting, empty success, invalid response/error handling, and absence of an LLM-callable diagnostics tool.
13. Keep assertions focused on behavior rather than irrelevant formatting.

## Acceptance criteria

- `/inter-agent channels` is available from the installed Pi extension.
- It works without an active Pi listener when the configured server is reachable and authenticated.
- It is read-only, user-invoked only, and not LLM-callable or autonomous.
- Empty and populated `channels_ok` responses are intentional successes.
- Focused tests, Pi type/build/format checks, live round-trip, and the full repository gate pass.
- `git diff --check` is clean and only allowed files are modified.

## Checks

Run at minimum:

```bash
uv run pytest \
  tests/test_pi_extension_static.py \
  tests/test_pi_adapter_cli.py \
  tests/integration/test_pi_adapter_live.py::test_pi_subscribe_unsubscribe_publish_channels_round_trip \
  -q
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check src/index.ts README.md package.json
./run-checks.sh
git diff --check
```

## End-to-end acceptance test

Run:

```bash
uv run pytest \
  tests/integration/test_pi_adapter_live.py::test_pi_subscribe_unsubscribe_publish_channels_round_trip \
  -q
```

Observed acceptance requires a live server to return `channels_ok` containing the subscribed `updates` channel and `pi-agent-a` routing name during the full subscribe/publish/unsubscribe round trip. If an interactive Pi environment is available, additionally run `/inter-agent channels` before connecting (against an already-running server), with a populated channel, and after the last unsubscribe. Confirm no-listener success, populated output, and empty success. Interactive host validation is supplementary; the live integration test is the required fallback.

## Completion report

Record changed files, behavior/docs/tests, exact checks, live acceptance, interactive limitations, and allowed-file confirmation.
