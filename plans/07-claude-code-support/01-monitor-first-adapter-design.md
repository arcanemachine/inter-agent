# Monitor-First Adapter Design

Extra Phase: 7 — Claude Code Support

## Purpose

Design Claude Code support around the Monitor tool and the existing inter-agent core APIs before writing adapter code.

## Research basis

See `docs/CLAUDE_CODE_SUPPORT.md` for the durable research summary.

- Claude Code Monitor runs a background shell command and streams stdout lines into the active Claude Code session.
- `claude-code-inter-session` demonstrates a practical pattern: a Monitor-backed listener connects to a localhost WebSocket bus and prints inbound messages as Claude notifications.
- MCP Channels may be useful later for richer push behavior, but Monitor is the primary integration surface for this extra phase.

## Scope

- Choose the Claude Code installation shape.
- Define how Claude Code sessions identify themselves on the bus.
- Define how inbound bus messages become Claude Code notifications.
- Define what remains outside the extra phase.

## Work

1. Review Claude Code Monitor, plugin, skill, and command documentation against the current Claude Code version.
2. Review `projects/_git/claude-code-inter-session` prior art for Monitor listener behavior, lazy start, session state, deduplication, and reaction policy.
3. Choose the supported install shape: plugin, standalone skill, or both.
4. Define the Claude Code session identity model, including `session_id`, display label, stable default name, and user-provided name override.
5. Define the inbound notification format, including message ID, sender name, direct versus broadcast indicators, and continuation pointers for long messages.
6. Define the outbound command surface and how it maps to core operations.
7. Document security assumptions: local process execution, Monitor permissions, plugin trust, and localhost shared-token auth.
8. Write the design in the Claude adapter README before implementing the adapter.

## Acceptance criteria

- The design identifies Monitor as the primary inbound delivery mechanism.
- The design states when MCP Channels or Agent Teams are not required for this extra phase.
- The design preserves core protocol semantics and keeps Claude Code behavior inside the adapter boundary.
- The design includes install, naming, output, state, and security decisions.
- No adapter implementation proceeds until the design is accepted.

## Files likely to change

- `src/inter_agent/adapters/claude/README.md`
- `docs/CLAUDE_CODE_SUPPORT.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `IDEAS.md`

## Checks

- Documentation review against implemented core command APIs
- `uv run pytest`
