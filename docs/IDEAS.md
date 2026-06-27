# Ideas

Purpose: this file preserves future protocol, adapter, packaging, developer-experience, security, and host-integration ideas that should remain visible without becoming active scope.

Status: deferred and exploratory unless a current plan promotes an item.

## How to use this file

1. Read the relevant section when planning work that touches that topic.
2. Do not treat every idea here as required implementation.
3. Promote ideas into `ROADMAP.md` only when the user accepts them as medium- or long-term direction.
4. Copy only the next concrete slice into `PLAN.md` when work becomes active.
5. Put concrete, actionable follow-ups in `docs/ideas/` as individual items (see `docs/ideas/ideas.sh`) when they are too specific for this idea bank but not active or ordered enough for `ROADMAP.md`.
6. Keep concrete near-term ideas above more speculative material.
7. When an idea becomes implemented architecture, move the current truth to `docs/ARCHITECTURE.md`.

## Concrete follow-up items

Individual, actionable items live in `docs/ideas/*.md` with YAML frontmatter and can be listed or filtered with `docs/ideas/ideas.sh`.

## Prioritized follow-up ideas

These items are user-prioritized follow-ups, but they are not active unless promoted into `ROADMAP.md` or copied into `PLAN.md` as a concrete work slice. See the corresponding files under `docs/ideas/` for full detail.

- Channel pub/sub routing behind explicit capability flags.
- Publish or register the Claude Code and Pi extensions in their appropriate distribution and discovery channels.
- Replace temporary GitHub `main.zip` runtime install sources with stable PyPI, release-tag, or pinned-archive sources.
- Refine local install layout and path handling for application files versus runtime state.
- Investigate Claude Code command autocomplete for `/inter-agent` commands.

## Host adapters

### Claude Code adapter

Claude Code support is a completed host integration. User-facing plugin docs live in `integrations/claude-code/README.md`. Keep new Claude Code ideas here only when they are outside that completed scope.

Possible follow-up work includes MCP tools/resources/channels, lifecycle hooks, and Agent Team patterns that bridge team mailboxes with inter-agent messages. Concrete items are in `docs/ideas/`.

### Additional host adapters

Other coding-agent hosts can be added once the adapter boundary is stable. New host ideas belong here until the user accepts them as roadmap direction or active work. New adapters should use core APIs, preserve shared bus defaults, and must not redefine protocol semantics.

Potential future hosts should follow the thin-adapter pattern used by Pi and Claude Code: host-native UX and notification handling around the shared core protocol, with runtime installation kept separate from bus endpoint and token state.

### Pi extension

The Pi extension (`integrations/pi/`) currently shells out to Python helper entry points. Future refactor ideas include a direct TypeScript WebSocket client, project-path auto-discovery, and quality-gate/testing coverage for the TypeScript extension. Concrete items are in `docs/ideas/`.

## Protocol extensions

Future protocol work includes a kick reconnect block, channel pub/sub, policy middleware examples, and a remote transport mode with a separate threat model. Concrete items are in `docs/ideas/`.

## Developer experience

Future tooling improvements include local pre-commit hooks and coverage reporting. Concrete items are in `docs/ideas/`.

## User ideas

User-sourced ideas and suggestions are preserved in `docs/IDEAS.USER.md`. Agents must not modify that file.
