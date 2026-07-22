# Task 1 — Make user-invoked kick effective

Status: ready for dispatch

## Goal

Expose the existing `kick` operation as an explicit user command in Pi and Claude Code, and make a kicked listener stop automatic reconnecting until its user explicitly reconnects or reloads/restarts the host. Preserve immediate name reuse and every existing transport, auth, TLS, mailbox, startup-identity, channel, disconnect, and shutdown behavior.

## Context

Closeout item 8a was accepted in `6a8ad43`. The server currently removes a kicked session then closes its WebSocket, but current Pi and Claude listeners classify that close as reconnectable and immediately reclaim the name. This task implements a terminal `KICKED` protocol error before closure. It is not a ban: the name becomes available immediately and an explicit later connect/reload may use it again.

The accepted design is authoritative in `docs/plans/important-closeout/01a-user-invoked-kick.md`. Do not broaden or redesign it.

## Allowed files to modify

- `src/inter_agent/core/server.py`
- `src/inter_agent/core/errors.py`
- `src/inter_agent/adapters/pi/listener.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/pi/cli.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/cli.py`
- `spec/error-codes.md`
- `spec/schemas/error.json` only if the existing generic error schema requires it
- `tests/conformance/test_kick.py`
- `tests/conformance/test_channels.py`
- `tests/test_pi_listener.py`
- `tests/test_claude_listener.py`
- `tests/test_core_command_api.py` — only `test_kick_session_by_name_disconnects_target`, to assert the required terminal `KICKED` frame before closure
- `tests/test_pi_adapter_cli.py`
- `tests/test_claude_adapter_cli.py`
- `tests/test_pi_extension_static.py`
- `tests/test_claude_skill_static.py`
- `integrations/pi/src/index.ts`
- `integrations/pi/README.md`
- `integrations/claude-code/skills/inter-agent/SKILL.md`
- `integrations/claude-code/README.md`

Modify the minimum subset required. Stop and report if another file is necessary.

## Additional files allowed to read

- `AGENTS.md`
- `integrations/pi/AGENTS.md`
- `integrations/claude-code/AGENTS.md`
- `docs/plans/important-closeout/01a-user-invoked-kick.md`
- `spec/schemas/msg.json`
- `src/inter_agent/core/client.py`
- `src/inter_agent/adapters/pi/__init__.py`
- `src/inter_agent/adapters/claude/__init__.py`
- `tests/integration/test_pi_adapter_live.py`
- `tests/integration/test_claude_adapter_live.py`
- `tests/test_console_entry_points.py`
- current Pi extension API declarations/documentation only if needed for the command surface

Do not traverse or print dependency trees or `node_modules`. Do not expose shared secrets, credentials, private environment values, registry tokens, or UAT marker bodies.

## Non-goals

- No new model-callable `inter_agent_kick` tool or any other model kick surface.
- No persistent/temporary ban, blocklist, timeout, unkick operation, durable tombstone, or retry timer.
- No session-ID argument in Pi or Claude host commands.
- No change to generic `inter-agent-kick`/repository-wrapper APIs beyond terminal semantics required for a live target.
- No mailbox, reload-continuity, compaction-continuity, TLS, publication, extraction, package, channel, transport, auth, startup-identity, Claude-hook, or server-shutdown redesign.
- No global installation/update, credentials, remote changes, or publication.

## Requirements

1. Add `/inter-agent kick <name>` only to the Pi user command and Claude installed skill command surfaces. It accepts exactly one routing name, autocompletes where Pi currently supports it, and uses the existing short-lived authenticated adapter/helper control path without requiring an active listener.
2. Do not expose kick as an LLM-callable tool. Claude guidance must run it only for an explicit user request.
3. Preserve control authentication. Only control-role callers can kick; never put the shared secret in argv, output, logs, or model context.
4. Target only a registered agent-role connection. Reject a control-role target with a bounded role error without closing it. Unknown/already-removed targets retain bounded `UNKNOWN_TARGET` behavior.
5. Before closing a target, send one bounded generic protocol error with code `KICKED`. It must not reveal controller identity, session/private metadata, or secrets.
6. The server must resolve/remove the exact current target identity under its existing registry lock, retain one-time channel cleanup, and prevent late cleanup from a kicked old socket unregistering a newer same-name replacement.
7. Pi and Claude listeners must treat `KICKED` as terminal: stop their reconnect loops, leave the host listener disconnected through the existing bounded permanent-error path, and emit no traceback. Other normal/retryable closes and transient failures retain existing retry behavior.
8. `kick_ok` retains the current controller response identifying the removed name/session ID; host rendering is concise and bounded. The freed name must register again through an explicit later connect or host/session reload/restart.
9. Update only necessary host README/skill and canonical error-code wording. No temporary migration notes.
10. Add behavioral coverage; static checks may prove command/tool registration boundaries but must not replace server/listener race, terminal-error, retry, command, and secrecy tests.

## Acceptance criteria

- Pi and Claude expose user-only `/inter-agent kick <name>` through their existing helper paths, including while their local listener is disconnected.
- A kicked Pi or Claude listener receives `KICKED`, stops reconnecting cleanly, and does not reclaim the name automatically.
- The name is immediately free and explicit later connect/reload works; no ban/blocklist exists.
- Auth, control-target rejection, unknown target, exact-session race safety, and channel cleanup remain correct.
- No kick model tool exists and no secret/controller metadata leaks.
- Existing list, disconnect, shutdown, startup identity, mailbox, channels, transport, auth, and TLS behavior remains unchanged.
- Only allowed files change; generated outputs and UAT resources are removed; all checks pass.

## Checks

Run at minimum:

```bash
uv run pytest tests/conformance/test_kick.py tests/conformance/test_channels.py tests/test_pi_listener.py tests/test_claude_listener.py tests/test_pi_adapter_cli.py tests/test_claude_adapter_cli.py tests/test_pi_extension_static.py tests/test_claude_skill_static.py -q
uv run pytest tests/integration/test_pi_adapter_live.py tests/integration/test_claude_adapter_live.py -q
./run-checks.sh
git diff --check
```

Also run relevant Pi package typecheck/test/build and Claude static/plugin validation if command-surface changes require them. Never print `node_modules` or secrets.

## End-to-end acceptance

Use an isolated real server plus installed Pi and Claude integrations, with unique ephemeral names/markers and a secret never printed. Remove all temporary files, server processes, and tmux sessions after checking no clients are attached.

1. Start an auto-reconnecting Pi listener under a unique agent name and subscribe it to a channel.
2. From the Pi user command surface while its own listener is disconnected or has a different name, kick the target. Confirm bounded `kick_ok`, immediate list/channel removal, `KICKED` terminal handling, and no reconnect through multiple normal backoff intervals.
3. Explicitly reconnect or reload the kicked Pi host and confirm the name registers again.
4. Repeat the terminal/no-reconnect/explicit-reconnect case for an auto-reconnecting installed Claude listener kicked from the Claude user command surface.
5. Verify an unknown target yields bounded `UNKNOWN_TARGET`; use controlled protocol coverage for the protected control-target rejection.
6. Confirm neither host has a model-callable kick tool, and that output/process arguments contain no secret.
7. Disconnect all sessions and confirm registrations disappear.

## Completion report

Report changed files; exact terminal-error and race-safety behavior; user-command/helper routing; tool-boundary evidence; focused/package/plugin/full check results; installed Pi/Claude UAT observations; cleanup; allowed-file confirmation; limitations; and secret safety. Do not commit.
