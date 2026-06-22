# Ideas

This file holds promising work that is not required for project completion as defined in `AGENTS.PLAN.md`. Move an idea into the roadmap and phase plans only when it becomes completion scope.

## User-suggested improvements (do not edit these; remove when completed)

- Ensure that the inter-agent server automatically disconnects after the configured timeout.

- In Pi, when connecting to the inter-agent session, add a message to the context so that the agent knows that it has been connected to the session and doesn't need to use the `whoami` command. (This should not prompt a reply from the agent... It should just be part of the "next turn" when the user prompts again).
  - *May* also be able to tweak the user's personal inter-agent handoff sub-skill so that the "whoami" check is no longer *required* to perform a handoff.
    - Make sure the user tests this behavior manually if any changes are made!

- Show a better error message if running the `start` script when a session has already started.
  - It currently crashes with a decent error message at the end, but the whole process could be a little cleaner.

## Misc. improvements

- Server lifecycle QoL improvements
  - Manual server starts run until explicit shutdown by default, with `--idle-timeout <seconds>` available when an idle timeout is wanted.
  - Pi and Claude Code auto-start server paths use an explicit 300-second idle timeout.
  - How would agents behave if the server connection was lost (e.g. due to a crash)? Would they be notified? Should they attempt to reconnect? This process should be guided.
    — Implemented: both the Claude Code and Pi listeners now reconnect with bounded backoff and eventual give-up.

## Host adapters

### Claude Code adapter

Claude Code support is a completed host integration (Phase 7). User-facing plugin docs live in `integrations/claude-code/README.md`. Keep new Claude Code ideas here only when they are outside that completed scope.

### Claude Code MCP and Channels follow-up

Monitor is the primary Claude Code integration surface (now implemented). MCP tools, MCP Channels, hooks, and Agent Teams may become useful additions.

Possible follow-up work:

1. MCP tools for structured send, broadcast, list, and status actions.
2. MCP resources for session lists or recent messages.
3. MCP Channels for push delivery independent of Monitor stdout.
4. Hooks that notify the bus after selected Claude Code lifecycle events.
5. Agent Team patterns that bridge team mailboxes with inter-agent messages.

### Additional host adapters

Other coding-agent hosts can be added once the adapter boundary is stable. New adapters should use core APIs and must not redefine protocol semantics.

### Pi extension:

#### Direct WebSocket client

The current Pi extension (`integrations/pi/`) shells out to the Python CLI (`inter-agent-pi` for commands, `inter-agent-connect` for the listener). This requires Python/venv/uv to be available on the Pi side.

A future refactor could replace the Python CLI bridge with a direct TypeScript WebSocket client, adding `ws` as a runtime dependency and implementing a small client that handles hello handshake, token auth, send/broadcast/list/status/shutdown, and the listener loop. The protocol is simple JSON over WebSocket and token path, identity verification, and frame parsing already exist in the Python core and could be ported.

#### Project path auto-discovery

The current default for finding the inter-agent project is `~/.local/share/inter-agent` (hardcoded fallback) with optional `settings.json` override. Auto-discovery could check PATH first, then walk up from `process.cwd()` looking for `.venv/bin/inter-agent-pi`.

#### Quality gate and testing

- `run-checks.sh` currently only runs Python checks. Decision needed: should it also validate the Pi extension TypeScript?
- The existing inter-agent test suite is entirely Python. Decision needed: what level of testing is acceptable for the TypeScript extension — structural Python tests, a smoke test, or manual validation only?
- Full interactive testing inside Pi (running the full set of commands in a live session) has not been done.

## Protocol extensions

### Kick reconnect block

The `kick` op force-disconnects a session, but auto-reconnecting listeners (Pi, Claude Code) will reclaim their name within a fraction of a second, making kick ineffective for stale-session reaping. A server-side blocklist would make kick useful for that use case.

Considerations:

1. Keep an in-memory `kicked_names` map (name → expiry timestamp) populated on kick.
2. Reject `hello` for a blocked name with a dedicated `KICKED` error until the block expires.
3. Default block duration (e.g. 60s), optionally configurable via `INTER_AGENT_KICK_BLOCK_S`.
4. Block by name only (agent names are unique) or also by session_id.
5. Listeners should treat `KICKED` as non-permanent and retry with normal backoff so they recover automatically once the block lifts.
6. The block is in-memory only and does not survive a server restart.

### Channel pub/sub

Add channel-based routing behind explicit capability flags. This would allow agents to subscribe to named topics instead of receiving only direct messages or global broadcasts.

Considerations:

1. Channel naming and validation rules.
2. Subscribe/unsubscribe operations.
3. Interaction with direct messages and global broadcast.
4. Capability negotiation and fallback behavior.
5. Conformance tests and schemas.

### Policy middleware examples

Add examples for rate limits or allowlists using the router middleware boundary.

Considerations:

1. Middleware API shape.
2. Error behavior when a policy blocks routing.
3. Per-agent and global policy configuration.
4. Tests that prove middleware runs before delivery.

### Remote transport mode

The security model is localhost-only. A remote mode would require a separate threat model and stronger transport/authentication design.

Considerations:

1. TLS or mTLS.
2. Token lifecycle and revocation.
3. Host identity and trust bootstrap.
4. Multi-user authorization boundaries.
5. Network exposure defaults.

## Developer experience

### Local pre-commit hooks

A pre-commit configuration could run formatting and linting before commits. This is convenience tooling, not a substitute for the project-local quality gate.

### Coverage reporting

Coverage measurement could help identify untested protocol or adapter paths after the conformance suite is expanded.
