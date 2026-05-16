# Ideas

This file holds promising work that is not required for project completion as defined in `AGENTS.PLAN.md`. Move an idea into the roadmap and phase plans only when it becomes completion scope.

## Misc. improvements

- Discuss with user: Server lifecycle QoL improvements
  - ~~IDEA: The server should be able to be started by an agentic coding harness (e.g. Pi coding agent, Claude Code).~~ — **Implemented.** The Claude Code listener auto-starts the server.
  - ~~IDEA: If started by a coding harness, perhaps the server should shut down automatically if no agents are connected to it for a given period of time? (e.g. 1 minute)~~ — **Implemented.** `--idle-timeout` with default 300 seconds.
  - ~~IDEA: Perhaps this feature could be gated by an opt-in flag used when starting the server?~~ — **Implemented.** `--idle-timeout <seconds>` (default 300) and `--idle-timeout 0` to disable.
  - How would agents behave if the server connection was lost (e.g. due to a crash)? Would they be notified? Should they attempt to reconnect? This process should be guided.
    — Partially implemented: the Claude Code listener reconnects with bounded backoff. Pi extension and direct clients do not yet reconnect.
  - IDEA: Perhaps the server could also be started externally (e.g. by the user), and would then run persistently until stopped by the user?
    — The server can be started manually with `uv run inter-agent-server` and runs until shutdown or idle timeout.

## Host adapters

### Claude Code adapter

Claude Code support is a completed host integration (Phase 7). Durable design notes live in `docs/CLAUDE_CODE_SUPPORT.md`. Keep new Claude Code ideas here only when they are outside that completed scope.

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

### Pi extension: direct WebSocket client

The current Pi extension (`integrations/pi/`) shells out to the Python CLI (`inter-agent-pi` for commands, `inter-agent-connect` for the listener). This requires Python/venv/uv to be available on the Pi side.

A future refactor could replace the Python CLI bridge with a direct TypeScript WebSocket client, adding `ws` as a runtime dependency and implementing a small client that handles hello handshake, token auth, send/broadcast/list/status/shutdown, and the listener loop. The protocol is simple JSON over WebSocket and token path, identity verification, and frame parsing already exist in the Python core and could be ported.

### Pi extension: project path auto-discovery

The current default for finding the inter-agent project is `~/.local/share/inter-agent` (hardcoded fallback) with optional `settings.json` override. Auto-discovery could check PATH first, then walk up from `process.cwd()` looking for `.venv/bin/inter-agent-pi`.

## Protocol extensions

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
