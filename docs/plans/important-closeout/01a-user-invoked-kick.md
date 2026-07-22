# User-invoked effective kick

Status: concrete; accepted direction; queued immediately after closeout item 8a

## Goal

Expose the existing inter-agent `kick` operation as a user-invoked command in both Pi and Claude Code, and make a kicked Pi or Claude listener stop reconnecting until its user explicitly reconnects or restarts/reloads the host.

## Context and terminology

`kick` is the project's established term for force-disconnecting a registered session. Core protocol, server dispatch, generic client API, `inter-agent-kick` console script, repository wrapper, conformance tests, and security documentation already exist.

The current server removes the target from the registry and channel memberships, returns `kick_ok`, and closes its WebSocket. Current Pi and Claude listeners interpret that normal close as reconnectable, so a live listener immediately reclaims the same name. That behavior makes today's operation sufficient for a genuinely dead or half-open connection but ineffective for a still-running auto-reconnecting UAT listener.

This item promotes effective kick semantics rather than a temporary ban: the target receives a dedicated `KICKED` protocol error and treats it as terminal for that listener process. The routing name remains available immediately. A later explicit connect or host restart/reload may use it again.

## Locked behavior

1. Add `/inter-agent kick <name>` to the Pi extension command and Claude Code skill command surfaces.
2. `kick` is user-invoked only:
   - do not register `inter_agent_kick` or any other model-callable kick tool;
   - Pi exposes it only through `pi.registerCommand("inter-agent", ...)`;
   - Claude skill guidance runs it only when the user explicitly requests it.
3. The host command accepts one routing name. Existing lower-level protocol/core APIs may retain their current optional `session_id` support; do not expose session IDs in the Pi or Claude host command unless a later demonstrated need is approved.
4. The command does not require the invoking Pi or Claude listener to be connected. It uses a short-lived authenticated control connection through the existing adapter/helper path.
5. On success, preserve the existing controller response: `kick_ok` identifies the removed agent name and session ID. Present a concise bounded user result without secrets.
6. An unknown or already-removed name returns the existing bounded `UNKNOWN_TARGET` error and leaves the host usable.
7. Only an authenticated control-role connection may invoke kick. Preserve the existing shared-secret challenge/response and never place the secret in argv, output, logs, or model context.
8. Kick targets only registered `agent`-role sessions. Reject a control-role target with a bounded role error; the server itself is not a registered target.
9. Before closing the target WebSocket, send the target a protocol error with dedicated code `KICKED` and bounded text that does not identify the controller or expose private metadata.
10. Pi and Claude listeners classify `KICKED` as terminal for that listener process:
    - stop the automatic reconnect loop;
    - exit cleanly through the existing bounded permanent-error path;
    - let the host adapter mark the listener disconnected;
    - do not shut down the inter-agent server or the Pi/Claude host.
11. After kick, the removed routing name remains free. The kicked host may connect again only through an explicit connect action or a later host/session restart or reload that normally starts its listener.
12. Do not add a persistent or temporary name/session blocklist, ban duration, unkick operation, retry timer, durable tombstone, or server-restart persistence.
13. A target already closing or disconnected may race with kick. The result is either one `kick_ok` for the session actually removed or bounded `UNKNOWN_TARGET`; never remove a later replacement session accidentally.
14. Resolve by current connection identity under the existing server registry lock. Late cleanup from the kicked socket must not unregister a newer connection that subsequently claims the same name.
15. Removing an agent retains current channel cleanup: remove its subscriptions and empty channel state exactly once.
16. Preserve all existing list, disconnect, shutdown, send, broadcast, channel, auth, TLS, endpoint, helper-resolution, startup-identity, mailbox, and compaction behavior.
17. `disconnect` remains the local listener-stop command. `shutdown` remains the server-stop command. Do not rename or alias either to `kick`.

## Expected implementation boundary

The active packet should normally allow the minimum necessary subset of:

### Protocol and server terminal signal

- `src/inter_agent/core/server.py`
- `src/inter_agent/core/errors.py`
- `spec/error-codes.md`
- protocol error examples/schemas only if the existing generic error schema requires an update
- `tests/conformance/test_kick.py`
- `tests/conformance/test_channels.py`

### Listener behavior

- `src/inter_agent/adapters/pi/listener.py`
- `src/inter_agent/adapters/claude/listener.py`
- `tests/test_pi_listener.py`
- `tests/test_claude_listener.py`

### Adapter command surfaces

- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/pi/cli.py`
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/cli.py`
- `integrations/pi/src/index.ts`
- `integrations/claude-code/skills/inter-agent/SKILL.md`
- `integrations/pi/README.md`
- `integrations/claude-code/README.md`
- `tests/test_pi_adapter_cli.py`
- `tests/test_claude_adapter_cli.py`
- `tests/test_pi_extension_static.py`
- `tests/test_claude_skill_static.py`

Do not modify mailbox storage/delivery, generic server shutdown, core send/list/channel semantics, Claude hooks, packaging extraction, or publication behavior. Do not add a model-callable tool.

## Required tests

1. Authenticated control kick of an agent returns `kick_ok`, removes the exact registry entry, removes channel memberships, and closes the target.
2. Target receives `KICKED` before closure; the diagnostic contains no controller identity or secret.
3. Non-control sender still receives `BAD_ROLE`.
4. Attempt to target a control connection is rejected and does not close it.
5. Unknown/already-removed target returns `UNKNOWN_TARGET`.
6. A late close callback from the kicked socket cannot unregister a newer same-name agent.
7. Pi and Claude listeners stop retrying after `KICKED`, exit through bounded terminal handling, and do not emit a traceback.
8. Other reconnectable closes and transient failures retain current retry behavior.
9. Explicit later Pi/Claude connect succeeds under the kicked name.
10. Pi `/inter-agent kick <name>` parses, autocompletes, invokes the existing helper/control path without requiring a listener, and renders success/error boundedly.
11. Claude `/inter-agent kick <name>` is documented and routed through the existing wrapper/helper only on explicit user request.
12. Static/security tests prove no kick tool is registered or described as model-callable.
13. Existing generic `inter-agent-kick`, repository wrapper, conformance, disconnect, shutdown, startup identity, mailbox, channels, auth, and TLS tests remain green.

## End-to-end acceptance

Use an isolated real server and installed Pi and Claude integrations. Do not print shared secrets.

1. Start an auto-reconnecting Pi listener under a unique name and subscribe it to a channel.
2. From the Pi user command surface, kick that name while the invoking Pi listener is disconnected or under a different name.
3. Observe `kick_ok`, immediate removal from list/channel membership, bounded `KICKED` handling in the target, and no reconnect after multiple normal backoff intervals.
4. Explicitly reconnect or reload the kicked Pi host and verify the same name can register again.
5. Repeat with an auto-reconnecting Claude listener and the Claude Code user command surface.
6. Kick an unknown name and verify bounded `UNKNOWN_TARGET` behavior.
7. Attempt the protected control-target case through a controlled protocol test and verify rejection without disrupting the control operation.
8. Confirm no `inter_agent_kick` model tool exists in either host and no secrets appear in output or process arguments.
9. Exit all sessions cleanly and confirm listeners disappear.

## Acceptance criteria

- Both host surfaces expose idiomatic `/inter-agent kick <name>` only to explicit user invocation.
- Kicked current Pi and Claude listeners do not automatically reconnect.
- Explicit later reconnect/reload remains possible; there is no ban or blocklist.
- Only agent-role targets may be kicked, with race-safe registry/channel cleanup.
- `KICKED`, `UNKNOWN_TARGET`, and authorization failures are bounded and secret-safe.
- Existing transport, auth, TLS, commands, mailbox, startup identity, and channels remain intact.
- Focused protocol/listener/adapter/static tests, installed cross-host UAT, and `./run-checks.sh` pass.
