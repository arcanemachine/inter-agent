# Task 1 — Pi installed publish UX

Status: active

## Goal

Expose the existing Pi adapter channel publication through an explicit user-invoked Pi command:

```text
/inter-agent publish <channel> <text>
```

The extension must publish with the current Pi listener's routing name, preserve user control, provide normal Pi notification/history UX, add focused coverage, and leave Python/protocol behavior unchanged.

## Context

The Python adapter already implements `inter-agent-pi publish <channel> <text> --from <name>`. It opens a short-lived authenticated connection, publishes through the existing core API, prints the welcome envelope on success, and returns non-zero with `inter-agent-pi:` diagnostics for local/protocol failures. The installed extension already tracks the ready listener identity and uses it internally for send, broadcast, subscribe, and unsubscribe.

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

- No Python implementation changes.
- No protocol, schema, conformance, error-code, limit, or server changes.
- No Pi `channels` command; that is closeout item 3.
- No LLM-callable publish tool.
- No autonomous, inferred, peer-triggered, or automatic publication.
- No subscription, direct-send, broadcast, listener, connection, or receive-semantics changes.
- No caller-selected sender identity.

## Requirements

1. Add `publish` to `/inter-agent` autocomplete and grouped usage.
2. Dispatch `/inter-agent publish <channel> <text>` from the grouped command handler.
3. Require exactly a non-whitespace channel token and non-empty message text; otherwise show `usage: /inter-agent publish <channel> <text>`.
4. Require the current Pi listener to be ready and connected, using the existing connection guidance.
5. Invoke the existing helper exactly with `publish`, channel, text, `--from`, and `currentConnection.name`. The user must not provide or choose `from_name`.
6. On helper failure, show a Pi error notification using existing bounded helper diagnostics.
7. On success, notify that publication succeeded for the channel and add the normal outbound-history entry using `showOutgoingInContext(..., "on <channel>")`.
8. Keep publication explicit-user-only. Do not register `inter_agent_publish`, add publish to the system prompt/tool guidance, publish from peer-message handling, or provide any autonomous path.
9. Preserve peer-channel guidance: there remains no publish *tool*, so agents reply directly unless the user explicitly invokes the slash command.
10. Document command syntax, active-listener identity, publisher exclusion, subscription independence, success/failure behavior, `UNKNOWN_CHANNEL`, and explicit-user/no-tool/no-autonomous boundaries.
11. Keep Pi channel-list UX prospective until item 3.
12. Add focused static tests for autocomplete, usage, dispatch, parsing, connection gate, exact helper arguments, success UX, error UX, current identity, and absence of an LLM-callable publish tool.
13. Keep assertions focused on behavior rather than irrelevant line wrapping.

## Acceptance criteria

- `/inter-agent publish <channel> <text>` is available from the installed Pi extension.
- The current listener routing name is always the publisher identity.
- Publication is user-invoked only and no publish tool/autonomous path exists.
- Existing Python/protocol behavior is unchanged.
- Focused tests, Pi type/build/format checks, live round-trip, and full repository gate pass.
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
npx --prefix integrations/pi prettier --check \
  integrations/pi/src/index.ts integrations/pi/README.md integrations/pi/package.json
./run-checks.sh
git diff --check
```

## End-to-end acceptance test

The leader/executor must run:

```bash
uv run pytest \
  tests/integration/test_pi_adapter_live.py::test_pi_subscribe_unsubscribe_publish_channels_round_trip \
  -q
```

Observed acceptance requires the live Pi listener to subscribe, publish under `pi-agent-a`, receive the distinct channel delivery, unsubscribe, and receive `UNKNOWN_CHANNEL` when no subscriber remains. If an interactive Pi environment is available, additionally run `/inter-agent publish <channel> <text>` with a second subscriber and verify the success notification, outbound history, sender identity, and subscriber delivery. Interactive host validation is supplementary; the live integration test is the required fallback.

## Completion report

Record:

- files changed;
- installed behavior and documentation added;
- tests added or updated;
- exact check and live-acceptance results;
- any unavailable interactive validation and its environment constraint;
- confirmation that no disallowed file changed.
