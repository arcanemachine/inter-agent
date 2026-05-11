# Ideas

This file holds promising work that is not required for project completion as defined in `ROADMAP.md`. Move an idea into the roadmap and phase plans only when it becomes completion scope.

## Host adapters

### Claude Code adapter

A Claude Code adapter could expose the same core protocol through Claude Code-specific commands, hooks, or UI conventions.

Useful discovery questions:

1. What command or extension mechanism should receive and display bus messages?
2. How should Claude Code sessions choose stable agent names?
3. Should the adapter support the same command surface as the Pi adapter or a host-native subset?
4. What output shape is easiest for Claude Code tools to parse?

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
