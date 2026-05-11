# Ideas

This file holds promising work that is not required for project completion as defined in `ROADMAP.md`. Move an idea into the roadmap and phase plans only when it becomes completion scope.

## Host adapters

### Claude Code adapter

Claude Code support is planned as `ROADMAP.md` Extra Phase 7. Durable research notes live in `docs/CLAUDE_CODE_SUPPORT.md`. Keep new Claude Code ideas here only when they are outside that phase.

### Claude Code MCP and Channels follow-up

Monitor is the primary planned Claude Code integration surface. MCP tools, MCP Channels, hooks, and Agent Teams may become useful after the Monitor-backed adapter exists.

Possible follow-up work:

1. MCP tools for structured send, broadcast, list, and status actions.
2. MCP resources for session lists or recent messages.
3. MCP Channels for push delivery independent of Monitor stdout.
4. Hooks that notify the bus after selected Claude Code lifecycle events.
5. Agent Team patterns that bridge team mailboxes with inter-agent messages.

### Additional host adapters

Other coding-agent hosts can be added once the adapter boundary is stable. New adapters should use core APIs and must not redefine protocol semantics.

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
