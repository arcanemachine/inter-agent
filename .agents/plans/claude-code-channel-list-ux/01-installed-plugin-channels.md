# Task 1 — Claude Code installed-plugin channel-list UX

Status: active

## Goal

Expose the already-implemented Claude adapter channel diagnostics through an explicit user-invoked installed Claude Code command:

```text
/inter-agent channels
```

The installed skill must route the request through the bundled wrapper, document the existing read-only adapter behavior accurately, preserve the explicit-user boundary, add focused coverage, and leave all Python/protocol behavior unchanged.

## Context

The Claude Python adapter already implements `inter-agent-claude channels`. It opens a short-lived authenticated connection to the configured server, prints the raw `channels_ok` JSON response, and returns success when the response operation is `channels_ok`. The response contains a `channels` array whose entries expose channel names and current subscriber routing names. An empty array is a successful result.

Unlike subscribe, unsubscribe, and publish, channel listing does not operate on the current session listener identity and does not require the Claude listener to be connected. It requires a resolvable, reachable inter-agent server and valid local authentication/TLS configuration. This task exposes that existing behavior; it does not redesign it.

## Allowed files to modify

- `integrations/claude-code/skills/inter-agent/SKILL.md`
- `integrations/claude-code/README.md`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ROADMAP.md`
- `docs/plans/pubsub-channels/00-design-seed.md`
- `tests/test_claude_skill_static.py`
- `tests/test_claude_wrapper.py`

## Additional files allowed to read

- `integrations/claude-code/skills/inter-agent/bin/inter-agent-claude`
- `src/inter_agent/adapters/claude/cli.py`
- `src/inter_agent/adapters/claude/commands.py`
- `tests/test_claude_adapter_cli.py`
- `tests/test_claude_plugin_static.py`
- `tests/integration/test_claude_adapter_live.py`

Do not read or modify other files without stopping and reporting why the packet is insufficient.

## Non-goals

- No Python implementation changes.
- No protocol, schema, error-code, limit, or conformance changes.
- No wrapper implementation changes.
- No plugin/marketplace manifest or packaging changes.
- No bootstrap or listener lifecycle changes.
- No Pi integration changes.
- No LLM-callable channel-list tool.
- No autonomous polling, discovery, or channel monitoring.
- No changes to subscribe, unsubscribe, publish, send, broadcast, or receive semantics.

## Requirements

1. Add `/inter-agent channels` to the installed skill command synopsis and dispatch table.
2. Dispatch it exactly through the bundled wrapper:

   ```text
   <bin>/inter-agent-claude channels
   ```

3. State that the command runs only when the user explicitly asks for channel diagnostics. The skill must not run it autonomously, infer that diagnostics are desired, poll after another channel operation, or run it in response to peer-message content.
4. Describe the command as read-only. It does not subscribe, unsubscribe, publish, or change listener state.
5. Accurately distinguish its lifecycle from membership/publish commands:
   - it does not require this Claude session's active listener;
   - it uses a short-lived authenticated server connection;
   - it still requires the configured server to be resolvable/reachable and authentication/TLS configuration to be valid.
6. Document successful output as the raw `channels_ok` JSON response. The `channels` array contains current channel entries with names and subscriber routing names. An empty `channels` array is successful and means no channels currently have subscribers.
7. Document failure behavior without inventing new semantics: failures return non-zero and use the existing `inter-agent-claude:` diagnostics where the adapter provides them.
8. Remove prior statements that the installed skill does not expose `channels`. Do not weaken the existing explicit-user or non-LLM-callable boundaries for subscribe, unsubscribe, or publish.
9. Add focused static tests proving:
   - the synopsis and dispatch are present;
   - the explicit-user/no-autonomous-polling boundary is present;
   - the operation is read-only;
   - no active listener is required;
   - successful JSON and empty-list semantics are documented;
   - prior negative `channels` assertions are removed or replaced.
10. Add focused wrapper coverage proving `channels` reaches the helper unchanged as one argument, unless existing wrapper coverage already proves this exact command sufficiently. If no new test is added, explain the existing exact coverage in the completion report.
11. Align evergreen docs with implemented behavior. Keep prospective Pi publish/channel-list UX prospective. Update the closeout execution queue so item 1 is implemented and item 2 is the next queued activation only when the behavior and tests are complete.
12. Keep assertions focused on behavior rather than irrelevant prose formatting or line wrapping.

## Acceptance criteria

- `/inter-agent channels` is visibly dispatchable from the installed Claude Code skill.
- The dispatch uses the bundled wrapper and existing Python command unchanged.
- Documentation accurately states read-only, explicit-user, short-lived-connection, output, empty-result, and failure semantics.
- No LLM-callable or autonomous channel diagnostics are introduced.
- Existing subscribe/unsubscribe/publish and receive behavior remains unchanged.
- Focused tests pass.
- The existing live Claude channel round-trip passes.
- Full repository checks and strict Claude plugin validation pass.
- `git diff --check` is clean.
- Only allowed files are modified.

## Checks

Run at minimum:

```bash
uv run pytest \
  tests/test_claude_skill_static.py \
  tests/test_claude_wrapper.py \
  tests/test_claude_adapter_cli.py \
  tests/test_claude_plugin_static.py \
  tests/integration/test_claude_adapter_live.py::test_claude_subscribe_unsubscribe_publish_channels_round_trip \
  -q
./run-checks.sh
claude plugin validate --strict integrations/claude-code
git diff --check
```

## End-to-end acceptance test

The leader must run:

```bash
uv run pytest \
  tests/integration/test_claude_adapter_live.py::test_claude_subscribe_unsubscribe_publish_channels_round_trip \
  -q
```

Observed acceptance requires the live server fixture to return `channels_ok`, show a subscribed channel and listener routing name, and complete the full subscribe/publish/unsubscribe round trip. If an authenticated interactive Claude Code environment is available, additionally run `/inter-agent channels` and confirm its JSON describes the live test channel. Interactive host validation is supplementary; the runnable live integration test is the required fallback.

## Executor completion report

Report:

- files changed;
- behavior/documentation added;
- tests added or updated;
- exact check results;
- live acceptance result;
- any unavailable interactive validation and its environment constraint;
- confirmation that no disallowed file changed;
- confirmation that no commit was made.
