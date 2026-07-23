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
4. **Pub/sub Phase 4 closeout** — run cross-integration acceptance, align evergreen documentation, and mark Phase 4 implemented. **Status: implemented in `e7b44fa`.**
5. **Pi disconnect reliability** — reproduce and fix the flaky `/inter-agent disconnect` behavior recorded in `TODO.md`. **Status: implemented in `6d557c8`.**
6. **Pi pre-connect list behavior** — make `/inter-agent list` return an intentional result instead of erroring before connection. **Status: implemented in `6244234`.**
7. **Claude Code sandbox connect failure** — reproduce and resolve the installed `/inter-agent connect` exit-127 failure recorded for the interline sandbox, or document a verified environment constraint. **Status: implemented in `247881f` (documented setup-needed signal plus bounded wrapper diagnostics for unrunnable helpers).**
7a. **Pi startup inter-agent identity** — add `pi --inter-agent <name>` so an installed Pi worker connects under an explicit routing name through the existing listener path, including session replacement/reload and bounded nonfatal failures. **Status: implemented in `37aec5b`.**
8. **Pi queued mailbox** — queue direct, broadcast, and channel message bodies by default; add explicit immediate mode, metadata-only notices, bounded in-memory storage, and selected/all message reads. **Status: implemented in `7c208d2`.**
8a. **Pi current-release compatibility baseline** — align the Pi integration's development, type, package, and installed acceptance targets with the current stable Pi distribution at activation, explicitly resolving the `@mariozechner` versus `@earendil-works` package lineage without bundling unrelated product behavior. **Status: implemented in `6a8ad43`.**
8b. **User-invoked effective kick** — expose `/inter-agent kick <name>` in Pi and Claude Code without a model-callable tool, restrict targets to agents, and make kicked listeners stop reconnecting until explicit reconnect or host reload/restart. **Status: implemented in `6210ed6`.**
8c. **Pi mailbox continuity across extension reload** — preserve the bounded unread mailbox through same-process `/reload` with a one-use in-memory handoff, while terminated-session resume and true replacement remain empty. **Status: implemented in `ad4de46`.**
8d. **Pi compaction connection and mailbox continuity** — verify first whether item 8c already resolved the previously observed disconnect; keep a live Pi routing identity connected through native and supercompaction paths, preserve the same live process's unread mailbox, and retain clearing on terminated-session resume or true replacement boundaries. **Status: closed verification-only after `ad4de46`: post-supercompaction identity continuity and real two-way inter-agent messaging passed; no additional product change was justified.**
9. **Installed cross-adapter TLS acceptance** — prove Pi and Claude helper/listener paths interoperate over `wss://`, including pub/sub, reconnect, certificate failures, and config propagation. **Status: completed in `d77579f`; the automated matrix and installed Pi/Claude UAT passed without a product defect.**
10. **Migration checkpoint and private meta repository** — freeze a tested source state, confirm remote/registry ownership and authorization, establish private `inter-agent-meta`, and approve the extraction mapping. **Status: active at shallow slice 10A, local freeze preflight; packet ready in `.agents/plans/migration-checkpoint/01-local-freeze-preflight.md` but not dispatched. Later slices remain separately gated and are planned just in time.**
11. **Pi repository extraction** — create independent `inter-agent-pi` npm/Pi and Python-helper package boundaries with package-local tests and no monorepo runtime dependency. **Status: queued after item 10 if migration is authorized.**
12. **Claude Code repository extraction** — create independent `inter-agent-claude-code` plugin/marketplace and Python-helper package boundaries. **Status: queued after item 11.**
13. **Core repository extraction and naming** — create clean `inter-agent-core`, retain the `inter_agent` import namespace and generic CLI names, and remove host assets/adapters from core artifacts. **Status: queued after item 12.**
14. **Public ecosystem superproject and pre-publication acceptance** — create `inter-agent/inter-agent` with real core/Pi/Claude submodules and prove candidate artifacts interoperate before publication. **Status: queued after item 13.**
15. **Core release-source audit and candidate validation** — recheck package ownership, metadata, entry points, artifact contents, versioning, and clean wheel/sdist behavior for `inter-agent-core`. **Status: queued after item 14.**
16. **Core PyPI publication checkpoint** — obtain authorization and publish the exact validated core artifacts without exposing credentials. **Status: user-gated after item 15.**
17. **Published-core installation acceptance** — install only from public PyPI in clean environments and verify generic CLI, auth, TLS, routing, and channels. **Status: queued after item 16 or maintainer publication.**
18. **Extension release candidate validation** — validate Pi npm/Python artifacts, Claude plugin/Python artifacts, independent versions, core dependency ranges, and stable bootstrap replacements. **Status: queued after item 17.**
19. **Pi extension publication checkpoint** — publish authorized `inter-agent-pi` Python and npm artifacts plus a tagged Git release, then verify Pi package discovery and clean install. **Status: user-gated after item 18.**
20. **Claude Code extension publication checkpoint** — publish the authorized Python helper and tagged standalone marketplace/plugin repository, then verify clean installed-plugin setup. **Status: user-gated after item 19.**
21. **Stable runtime source migration** — replace floating default-branch archives and monorepo paths with released extension-helper/core packages while preserving explicit development overrides. **Status: queued after items 19–20.**
22. **Released ecosystem acceptance** — validate registry/tag installations and the recursive public superproject across mailbox, reliability, TLS, pub/sub, shared-state, and isolation scenarios. **Status: queued after item 21.**
23. **Important-action closeout** — confirm every current product/release/split item is accepted, public/private docs are correctly separated, and the released ecosystem is ready for maintainer use. **Status: queued after item 22.**
24. **OpenCode direct-WebSocket and package-target spike** — validate plugin loading, split TUI/server targets, WebSocket access, authentication, and package targeting against the selected OpenCode version. **Status: deferred; first promotion candidate only after item 23 and user activation.**
25. **OpenCode extension design finalization** — update and accept the target-version architecture and spike findings. **Status: deferred after item 24.**
26. **OpenCode package scaffold and installation** — add the split-export npm package scaffold and install path. **Status: deferred after item 25.**
27. **OpenCode direct protocol client** — implement shared TypeScript/Bun transport, authentication, TLS, control operations, listener frames, and error mapping. **Status: deferred after item 26.**
28. **OpenCode TUI listener, state, inbox, and notifications** — implement the persistent TUI-owned receive path and lifecycle. **Status: deferred after item 27.**
29. **OpenCode commands, tools, and reaction policy** — implement the user command surface, server-plugin tools, shared sender identity, and collaboration-input boundaries. **Status: deferred after item 28.**
30. **OpenCode live tests and fixtures** — add reliable protocol/integration coverage and complete the available manual UAT. **Status: deferred after item 29.**
31. **OpenCode packaging, documentation, and quality gate** — validate the package, update supported-integration docs, and run its repository/ecosystem gates. **Status: deferred after item 30.**
32. **Codex App Server sidecar validation spike** — validate endpoint attachment, thread selection, `thread/inject_items`, visibility, and bounded-inbox fallback against a real target version. **Status: deferred until OpenCode is accepted.**
33. **Codex implementation decision** — use the spike findings to accept a production sidecar plan, a reduced integration, or explicit deferral. **Status: deferred user decision after item 32.**
34. **Final project completion review** — confirm every accepted item is complete or explicitly deferred and prepare the maintainer completion report. **Status: deferred until the promoted integration program is resolved.**

## Protocol status and follow-ons

### Pub/sub channels

Status: Phases 1–4 implemented.

Phase 1 (implemented) covers the core protocol operations (`subscribe`, `unsubscribe`, `publish`, `channels`), protocol schemas and examples, canonical errors and limits, conformance tests, capability advertisement, and present-behavior documentation. Direct messages and broadcast remain unchanged.

Phase 2 (implemented) adds typed core APIs and CLI entry points for publishing and channel diagnostics, plus a persistent `AgentSession` control surface that reuses an agent identity for subscribe, unsubscribe, and publish operations.

Phase 3 (implemented) adds subscribe, unsubscribe, publish, channel diagnostics, reconnect-aware membership, and distinct inbound channel formatting to the Pi and Claude Code Python adapters. A private local listener-control socket lets short-lived membership commands operate on the existing agent identity.

Phase 4 (implemented) provides user-invoked subscribe, unsubscribe, publish, and read-only channel diagnostics through both installed Pi and Claude Code integrations, plus channel-aware notifications/context. These operations are intentionally not LLM-callable; there are no automatic subscriptions, publications, or diagnostics. Short-lived publishers use the active listener routing name, and each adapter listener suppresses its own routing name's channel delivery so publisher exclusion remains consistent at the installed UX boundary. Cross-adapter live acceptance proves Pi and Claude publication, subscription, diagnostics, and delivery interoperate on one server.

Next activation step: obtain explicit user authorization to dispatch closeout slice 10A, the local freeze preflight. Do not create repositories, use credentials, publish, change remotes, or prepare extraction work under that slice.

Reference material:

- `docs/plans/pubsub-channels/00-design-seed.md`

## Prospective follow-on integrations

The current product reliability, mailbox, TLS acceptance, clean repository split, publication, and released-artifact acceptance queue takes priority. OpenCode remains the first accepted prospective host-integration direction after important-action closeout; Codex remains sequenced after OpenCode. Neither is active before the user promotes item 24.

### OpenCode support

Status: prospective; not implemented; not active.

Next activation step: after closeout queue item 23 is accepted, ask the user whether to promote item 24; only then copy the direct WebSocket/package-target spike into `.agents/PLAN.md`.

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

Next activation step: only after the important-action closeout and accepted OpenCode outcome, ask the user whether to promote the Codex App Server sidecar spike.

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

Status: accepted and queued after current reliability, mailbox, and TLS work.

The locked split direction is:

- private `inter-agent-meta` maintainer superproject containing private workflow and the public ecosystem as a submodule;
- public `inter-agent/inter-agent` ecosystem superproject containing real submodules at `core/`, `extensions/pi/`, and `extensions/claude-code/`;
- independently deployable `inter-agent-core`, `inter-agent-pi`, and `inter-agent-claude-code` repositories;
- PyPI core distribution `inter-agent-core` retaining the `inter_agent` import namespace and generic CLI names;
- extension-owned Python helper packages `inter_agent_pi` and `inter_agent_claude` preserving `inter-agent-pi` and `inter-agent-claude` commands;
- split before initial publication so release artifacts contain no transitional monorepo clutter;
- stable README links and semantic compatibility documentation; submodule commit pins remain Git metadata rather than copied README instructions.

Reference material:

- `docs/archive/plans/09-host-extension-packaging/01-repository-boundary-inventory.md`
- `docs/plans/repo-split/00-first-slices.md`
- `docs/plans/important-closeout/00-execution-guide.md`

Physical migration remains user-gated. Activate only the next bounded queue item after verifying the current repository state.

## Other follow-up areas

Other follow-up ideas remain in `docs/IDEAS.md` until accepted into this roadmap or copied into `.agents/PLAN.md` as active work. Current idea areas include:

- Pi direct WebSocket client refactor informed by a future host-native client;
- policy middleware examples;
- remote transport mode with a separate threat model.

Extension publishing and stable runtime sources are accepted queue items rather than exploratory ideas. The Pi queued mailbox is implemented product behavior.
