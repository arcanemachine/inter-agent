# Roadmap

`ROADMAP.md` records accepted medium- and long-term direction. It is not the active task list and does not describe supported product behavior unless explicitly marked as implemented.

Use [`.agents/PLAN.md`](.agents/PLAN.md) for the current short-term work. Use [`docs/IDEAS.md`](docs/IDEAS.md) for exploratory ideas that have not been accepted into the roadmap.

## Documentation boundaries

- `README.md` describes what users can do now.
- `.agents/PLAN.md` describes immediate active work only.
- `ROADMAP.md` describes accepted direction and prospective follow-on work.
- `docs/IDEAS.md` holds exploratory ideas and rough follow-ups.
- Archived execution notes live under `docs/archive/plans/`.
- Prospective implementation notes may live under `docs/plans/` when they are detailed enough to preserve.

Prospective integrations must not be listed as supported in `README.md`. When a prospective integration is implemented and validated, update `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, package docs, and this roadmap so the integration is no longer described as prospective.

## Status convention

Future agents should determine work state from these markers:

1. `.agents/PLAN.md` is authoritative for active work. If it says no implementation work is selected, no roadmap item is active.
2. Each roadmap item has a `Status:` line. `prospective` means researched or accepted direction, not implemented and not active.
3. Each roadmap item should name the next activation step. Work starts only after that concrete slice is copied into `.agents/PLAN.md`.
4. Files under `docs/archive/plans/` are historical. They explain completed work but do not define current phase state.

## Implemented baseline

The current implemented baseline is:

- local WebSocket message bus with shared-secret challenge-response authentication and optional TLS transport;
- protocol schemas, examples, canonical error codes, and conformance coverage;
- Python core server and helper commands;
- Pi extension and adapter;
- Claude Code plugin and adapter;
- packaging, release validation, and repository quality gate;
- localhost, single-user security model documented in `SECURITY.md`.

Completed execution notes are archived under `docs/archive/plans/` for reference. They are historical records, not active backlog items.

## Prospective protocol follow-ons

### Pub/sub channels

Status: Phases 1–3 implemented; Phase 4 partially implemented and not active.

Phase 1 (implemented) covers the core protocol operations (`subscribe`, `unsubscribe`, `publish`, `channels`), protocol schemas and examples, canonical errors and limits, conformance tests, capability advertisement, and present-behavior documentation. Direct messages and broadcast remain unchanged.

Phase 2 (implemented) adds typed core APIs and CLI entry points for publishing and channel diagnostics, plus a persistent `AgentSession` control surface that reuses an agent identity for subscribe, unsubscribe, and publish operations.

Phase 3 (implemented) adds subscribe, unsubscribe, publish, channel diagnostics, reconnect-aware membership, and distinct inbound channel formatting to the Pi and Claude Code Python adapters. A private local listener-control socket lets short-lived membership commands operate on the existing agent identity.

Phase 4 is partially implemented. Pi now provides user-invoked subscribe/unsubscribe commands and channel-aware notifications/context. Subscription control is intentionally not LLM-callable, and there are no automatic subscriptions. The installed Claude Code plugin channel UX and any separately accepted Pi publish/channel-list UX remain prospective.

Next activation step: inventory the installed Claude Code integration and copy one bounded Phase 4 plugin UX slice into `.agents/PLAN.md`.

Reference material:

- `docs/plans/pubsub-channels/00-design-seed.md`

## Prospective follow-on integrations

Near-term package/release readiness for the current implemented integrations, including stable PyPI release sources for the core runtime, remains important. Pub/sub channels should be addressed before new host-integration implementation. OpenCode is the accepted prospective host-integration direction ahead of Codex. Codex should be investigated after the current release work, pub/sub channel work, and OpenCode work are addressed.

### OpenCode support

Status: prospective; not implemented; not active.

Next activation step: copy the direct WebSocket spike and package-target validation into `.agents/PLAN.md` as the active slice.

OpenCode support has a researched design, but no OpenCode plugin package has been added and OpenCode is not a supported user-facing integration.

Reference material:

- `integrations/opencode/README.md` — consolidated prospective design/reference document.
- `docs/plans/opencode-support/` — detailed prospective execution notes.

Current design direction:

- one OpenCode npm package with separate `./tui` and `./server` plugin exports;
- TUI plugin owns listener, commands, notifications/toasts, state, and inbox;
- server plugin owns LLM-callable tools and any model-visible inbound-message path;
- shared TypeScript/Bun protocol client speaks the existing inter-agent WebSocket protocol directly;
- Python inter-agent server remains the canonical server;
- first release assumes the local server is already running;
- auto-start is deferred unless the user accepts a later design change.

Before implementation starts, move only the next concrete slice into `.agents/PLAN.md`. Required early spikes are direct WebSocket access from OpenCode and shared identity/state between the TUI and server plugin targets.

When OpenCode support is implemented and validated, update `README.md` to list it as supported and remove prospective wording from the relevant docs.

### Codex App Server sidecar support

Status: prospective; not implemented; not active.

Next activation step: after current release/PyPI package work, pub/sub channel work, and OpenCode work, copy a Codex App Server sidecar spike into `.agents/PLAN.md` as the active slice.

Codex support should not be planned as a plugin-only extension. Current Codex plugin surfaces can bundle skills, MCP servers, app connector metadata, and lifecycle hooks, but they do not provide a persistent background runtime that can own an inter-agent listener or push inbound messages into the Codex TUI automatically.

Reference material:

- `integrations/codex/README.md` — prospective App Server sidecar design/reference document.
- `docs/plans/codex-support/00-validation-spike.md` — first validation-spike plan.

Current design direction:

- a long-running sidecar process owns the inter-agent bus listener and Codex-specific runtime state;
- Codex App Server is the control surface for selected threads, turns, tools, and events;
- inbound messages should use conservative `thread/inject_items` delivery first, with bounded sidecar inbox fallback;
- `turn/steer` is opt-in future behavior because it affects an active Codex turn;
- outbound operations should be exposed through MCP, App Server dynamic tools, or both after a spike validates the UX;
- a Codex plugin may package skills, MCP config, and hooks, but plugin install alone must not imply automatic inbound delivery;
- no forked or patched Codex dependency is part of the target design.

Before implementation starts, validate App Server endpoint attachment, thread selection, injected-message behavior, outbound tool surface, sidecar lifecycle, and token-handling assumptions against a real Codex version.

## Packaging and repository split direction

Status: recorded direction; not active work.

The recorded split direction is:

- private `inter-agent-meta` wrapper;
- public `inter-agent/inter-agent` ecosystem superproject;
- independently deployable `inter-agent-core`, `inter-agent-claude-code`, `inter-agent-pi`, and future extension repositories.

Reference material:

- `docs/archive/plans/09-host-extension-packaging/01-repository-boundary-inventory.md`
- `docs/plans/repo-split/00-first-slices.md`

Start any physical repository/package extraction by copying a concrete, reviewable slice into `.agents/PLAN.md`.

## Other follow-up areas

Other follow-up ideas remain in `docs/IDEAS.md` until accepted into this roadmap or copied into `.agents/PLAN.md` as active work. Current idea areas include:

- extension publishing/discovery channels;
- stable runtime install sources;
- Pi direct WebSocket client refactor informed by the prospective OpenCode client;
- Codex App Server sidecar support after current release/PyPI package work and OpenCode work;
- remaining installed-integration pub/sub channel UX;
- policy middleware examples;
- remote transport mode with a separate threat model.
