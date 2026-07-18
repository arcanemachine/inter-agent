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

## Closeout execution queue

This queue preserves continuity between active slices. Complete items in order unless a finding changes a dependency or the user explicitly reprioritizes them. Only the current concrete slice belongs in `.agents/PLAN.md`; when that slice is accepted, update its status here, remove its active packet, and activate the next ready item. Inclusion in this queue does not bypass user approval for external publication, credential use, or physical repository migration.

1. **Claude Code installed channel-list UX** — expose the existing read-only `channels` adapter command through the installed `/inter-agent` skill with focused documentation, static/wrapper coverage, and live acceptance. **Status: implemented in `4d9e986`.**
2. **Pi installed publish UX** — expose explicit user-invoked channel publication through the Pi extension without autonomous or peer-triggered publishing. **Status: implemented in `17789e2`.**
3. **Pi installed channel-list UX** — expose read-only channel diagnostics through the Pi extension. **Status: implemented in `e3153a9`.**
4. **Pub/sub Phase 4 closeout** — run cross-integration acceptance, align evergreen documentation, and mark Phase 4 implemented. **Status: active; packet linked from `.agents/PLAN.md`.**
5. **Pi disconnect reliability** — reproduce and fix the flaky `/inter-agent disconnect` behavior recorded in `TODO.md`. **Status: queued after pub/sub closeout.**
6. **Pi pre-connect list behavior** — make `/inter-agent list` return an intentional result instead of erroring before connection. **Status: queued after item 5.**
7. **Claude Code sandbox connect failure** — reproduce and resolve the installed `/inter-agent connect` exit-127 failure recorded for the interline sandbox, or document a verified environment constraint. **Status: queued after item 6.**
8. **Core release-source audit** — verify current versioning, build metadata, artifacts, and the intended stable PyPI install source. **Status: queued after TODO defects.**
9. **Core PyPI publication checkpoint** — obtain explicit authorization and publish the validated core release, or record the maintainer-owned publication step without handling credentials in agent context. **Status: user-gated after item 8.**
10. **Published-core installation acceptance** — install from the stable release source in a clean environment and smoke-test the server plus Pi and Claude helper resolution. **Status: queued after item 9 or maintainer publication.**
11. **OpenCode direct-WebSocket and package-target spike** — validate plugin loading, split TUI/server targets, WebSocket access, authentication, and package targeting against the selected OpenCode version. **Status: queued after current integration and release work.**
12. **OpenCode extension design finalization** — update and accept the target-version architecture and spike findings. **Status: queued after item 11.**
13. **OpenCode package scaffold and installation** — add the split-export npm package scaffold and install path. **Status: queued after item 12.**
14. **OpenCode direct protocol client** — implement shared TypeScript/Bun transport, authentication, TLS, control operations, listener frames, and error mapping. **Status: queued after item 13.**
15. **OpenCode TUI listener, state, inbox, and notifications** — implement the persistent TUI-owned receive path and lifecycle. **Status: queued after item 14.**
16. **OpenCode commands, tools, and reaction policy** — implement the user command surface, server-plugin tools, shared sender identity, and collaboration-input boundaries. **Status: queued after item 15.**
17. **OpenCode live tests and fixtures** — add reliable protocol/integration coverage and complete the available manual UAT. **Status: queued after item 16.**
18. **OpenCode packaging, documentation, and quality gate** — validate the package, update supported-integration docs, and run the repository gate. **Status: queued after item 17.**
19. **Codex App Server sidecar validation spike** — validate endpoint attachment, thread selection, `thread/inject_items`, visibility, and bounded-inbox fallback against a real target version. **Status: queued after OpenCode.**
20. **Codex implementation decision** — use the spike findings to accept a production sidecar plan, a reduced integration, or explicit deferral. **Status: user decision after item 19.**
21. **Repository-split migration checkpoint** — confirm remote ownership, package names, transition install paths, test ownership, and authorization for physical extraction. **Status: user-gated after product/release work.**
22. **Pi extension extraction** — move the independent Pi TypeScript package while retaining transitional core-helper compatibility. **Status: queued after item 21 if migration is authorized.**
23. **Claude Code integration extraction** — move Claude Code plugin assets and adapter helper packaging. **Status: queued after item 22.**
24. **Core package extraction and naming** — establish the independent core repository/package while preserving practical CLI compatibility. **Status: queued after item 23.**
25. **Ecosystem superproject and private meta repository** — create the public ecosystem wrapper and move private workflow material to the private meta repository. **Status: queued after item 24.**
26. **Cross-repository interoperability acceptance** — verify core, Pi, Claude Code, and implemented future integrations across their independent package boundaries. **Status: queued after item 25.**
27. **Final project completion review** — confirm every accepted item is complete or explicitly deferred, clear active planning state, run final local gates, and prepare the maintainer closeout report. **Status: final queue item.**

## Prospective protocol follow-ons

### Pub/sub channels

Status: Phases 1–3 implemented; Phase 4 partially implemented and not active.

Phase 1 (implemented) covers the core protocol operations (`subscribe`, `unsubscribe`, `publish`, `channels`), protocol schemas and examples, canonical errors and limits, conformance tests, capability advertisement, and present-behavior documentation. Direct messages and broadcast remain unchanged.

Phase 2 (implemented) adds typed core APIs and CLI entry points for publishing and channel diagnostics, plus a persistent `AgentSession` control surface that reuses an agent identity for subscribe, unsubscribe, and publish operations.

Phase 3 (implemented) adds subscribe, unsubscribe, publish, channel diagnostics, reconnect-aware membership, and distinct inbound channel formatting to the Pi and Claude Code Python adapters. A private local listener-control socket lets short-lived membership commands operate on the existing agent identity.

Phase 4 is partially implemented. Pi provides user-invoked subscribe/unsubscribe commands and channel-aware notifications/context. The installed Claude Code `/inter-agent` skill exposes user-invoked subscribe/unsubscribe, user-invoked publish, and channel-aware notifications/context. Subscription control and publish are intentionally not LLM-callable, and there are no automatic subscriptions. The installed Claude Code channel-list UX and any separately accepted Pi publish/channel-list UX remain prospective.

Next activation step: copy one bounded Phase 4 slice for installed Claude Code channel-list UX (or accepted Pi publish/channel-list UX) into `.agents/PLAN.md`.

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
