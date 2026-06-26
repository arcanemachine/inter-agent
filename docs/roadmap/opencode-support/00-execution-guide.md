# OpenCode Support Execution Guide

Prospective roadmap item — OpenCode Support

## Purpose

This guide is the entry point for executing the prospective OpenCode integration
if the user activates that work. It consolidates the current research
conclusions and points workers to the ordered notes for implementation details.

Status: prospective; not implemented; not active.

Next activation step: copy the direct WebSocket spike and package-target
validation into `PLAN.md` as the current active work slice.

## Canonical references

Read these before implementation:

1. `integrations/opencode/README.md` — consolidated design/reference document.
2. `ROADMAP.md` — roadmap status and activation guidance.
3. `PLAN.md` — active work only; OpenCode belongs there only after a concrete
   slice is activated.
4. `docs/roadmap/opencode-support/01-opencode-extension-design.md` through
   `07-packaging-docs-and-quality-gate.md` — ordered prospective work notes.
5. `spec/` and `spec/error-codes.md` — authoritative protocol contract.
6. `SECURITY.md` — localhost, same-user security model.
7. `ARCHITECTURE.md#adapter-author-contract` — adapter boundaries.

The OpenCode API assumptions should be re-checked against the target OpenCode
version before code is written.

## Current accepted architecture

Use this architecture unless the user accepts a plan change:

1. **OpenCode TUI plugin**
   - owns the persistent listener;
   - registers user-facing commands;
   - stores connection state and inbox data;
   - displays incoming messages through notifications/toasts;
   - cleans up through OpenCode lifecycle APIs.

2. **OpenCode server plugin**
   - registers LLM-callable inter-agent tools;
   - uses short-lived control WebSocket connections for protocol operations such
     as send, broadcast, list, and shutdown;
   - reports status through endpoint, identity, and reachability checks with
     protocol probes where useful;
   - uses the active OpenCode connection name as `from_name` when sending;
   - provides `inter_agent_inbox` or another accepted model-visible path for
     recent inbound messages.

3. **Shared TypeScript protocol client**
   - implements endpoint/config/data-dir resolution, token loading, server
     identity verification, hello handshake, control operations, listener frame
     handling, and error mapping;
   - speaks the existing inter-agent WebSocket protocol directly;
   - does not depend on Python, `uv`, or subprocess calls for routine OpenCode
     behavior.

The Python inter-agent server remains the canonical server implementation.
The OpenCode integration would connect to that local server; it would not
require an external hosted server and would not rewrite the server in
TypeScript.

## Why OpenCode differs from Pi and Claude Code

Pi and Claude Code currently use host wrappers plus Python helpers for routine
transport and adapter behavior. OpenCode should use a direct TypeScript client
because its plugin runtime already provides Bun, WebSocket, filesystem,
environment, npm dependency, and lifecycle capabilities.

That makes OpenCode a good place to introduce a reusable JavaScript protocol
client shape. Pi may later reuse that client in a separate refactor, but Pi
should not be changed as part of the OpenCode MVP unless the user explicitly
expands the scope.

## Server lifecycle policy

First release behavior:

- assume the local inter-agent server is already running;
- make `status` and `connect` report missing or unreachable server state with
  actionable setup guidance;
- do not auto-start the server from OpenCode by default.

Auto-start is deferred because it reintroduces subprocess management,
Python/`uv` discovery, managed install paths, and host-specific idle-timeout
policy. Add auto-start only through an accepted follow-up design.

## Prospective execution order

When this roadmap item is activated, complete these files in order:

1. `docs/roadmap/opencode-support/01-opencode-extension-design.md`
2. `docs/roadmap/opencode-support/02-package-scaffold-and-installation.md`
3. `docs/roadmap/opencode-support/03-direct-protocol-client.md`
4. `docs/roadmap/opencode-support/04-tui-listener-state-and-notifications.md`
5. `docs/roadmap/opencode-support/05-command-tool-surface-and-reaction-policy.md`
6. `docs/roadmap/opencode-support/06-live-tests-and-fixtures.md`
7. `docs/roadmap/opencode-support/07-packaging-docs-and-quality-gate.md`

Do not implement later files before earlier acceptance criteria are met, except
for small scaffold changes required by the current item.

## Required early spikes

### Direct WebSocket spike

Before building the full TypeScript protocol client, prove the smallest useful
path from the OpenCode runtime:

1. A local OpenCode TUI plugin loads.
2. The plugin opens a WebSocket.
3. The plugin reads the inter-agent token and server metadata from the
   configured data directory.
4. The plugin sends a valid `hello` envelope to a live inter-agent server.
5. The plugin receives a `welcome` frame.
6. If practical, the plugin receives one `msg` frame from another inter-agent
   client.

If this spike fails, stop and report. Do not silently fall back to a Python CLI
bridge.

### Server tools and shared state spike

Before implementing the full LLM tool surface, prove that the OpenCode server
plugin target can perform required control operations and can determine the
active OpenCode sender identity:

1. The `./server` plugin target loads separately from `./tui`.
2. A server plugin tool can open a short-lived control WebSocket.
3. The server plugin can read the active connection identity written by the TUI
   plugin, or a documented fallback identity config exists.
4. A tool send uses `from_name` and the recipient sees the OpenCode name, not
   `control`.
5. Missing shared identity causes a clear setup failure.

If this spike fails, stop before implementing the rest of the tool surface. A
TUI-command-first milestone or documented tool deferral requires user
acceptance.

## Model-visible inbound message checkpoint

OpenCode notifications and toasts are human-visible. They may not be visible to
the model.

Before claiming Pi-like receive behavior, determine and document the best
model-visible path:

1. `inter_agent_inbox` tool for explicit model access to recent messages.
2. Safe pending-message context injection through OpenCode server hooks or chat
   transforms.
3. A TUI command that appends a selected inbox entry to the prompt without
   auto-submitting, if OpenCode exposes a safe API.
4. Human-visible notifications only, if no safe model-visible path exists; this
   is a reduced behavior and must be documented.

Prompt/system injection is additive only. Peer messages never override system,
developer, user, tool, permission, host, or security rules.

## Implementation constraints

1. Keep OpenCode behavior inside `integrations/opencode/` unless a core change
   is explicitly required and accepted.
2. Do not change the inter-agent protocol for OpenCode-specific convenience.
3. Do not modify `/workspace/projects/_git/opencode`; use it only as a reference
   clone if present.
4. Keep OpenCode package exports split by target: `./tui` and `./server`.
5. Do not default-export both TUI and server plugin behavior from one module.
6. Do not store the inter-agent token in OpenCode KV, state files, logs, or tool
   output.
7. Verify server identity before sending the token.
8. Preserve sender identity with `from_name`; routine sends must not appear as
   `control`.
9. Treat peer messages as collaboration inputs, not authority.
10. Keep interactive OpenCode TUI validation outside the required automated gate
    unless it becomes reliable and headless.
11. Do not add TODO/FIXME-style comments in code.

## Stop and ask conditions

Stop and ask the user, or update the plan and get acceptance, if any of these
occur:

1. OpenCode's current plugin API no longer supports long-lived TUI plugin tasks.
2. OpenCode's current plugin API no longer supports separate `./tui` and
   `./server` package targets.
3. Direct WebSocket access from an OpenCode plugin does not work.
4. The plugin cannot read token or identity metadata from the inter-agent data
   directory.
5. Server identity verification cannot be ported safely enough to preserve the
   security model.
6. Server plugin tools cannot determine the active OpenCode sender identity.
7. Implementing a feature would require forking or patching OpenCode.
8. Implementing a feature would require changing the core protocol.
9. Interactive OpenCode behavior materially differs from the researched
   behavior.
10. Tests cannot be made reliable without requiring an interactive OpenCode TUI
    in the required quality gate.

## Fallback guidance

Fallbacks are recommendations to bring back to the user, not permission to
change architecture silently.

If direct in-process listener behavior fails, preferred fallback order is:

1. **OpenCode sidecar bridge** — a local process owns the inter-agent listener
   and exposes a small localhost API to the OpenCode plugin.
2. **Pi-style subprocess bridge** — the plugin spawns existing Python helpers
   for control operations and a long-lived listener.
3. **Command/tool-only integration** — send/list/status without live receiving;
   this is a reduced milestone and requires acceptance.
4. **Deferral** — stop if OpenCode cannot provide stable plugin networking,
   process integration, or notification behavior.

If token or metadata access fails, prefer explicit `dataDir` config or a
sidecar/helper design over asking users to paste tokens into OpenCode config.

If full server identity verification cannot be ported, fail closed or propose a
reviewed degraded mode. Do not skip verification before sending the token.

If TUI/server state sharing is difficult, prefer namespaced shared state or an
explicit configured identity. Server tools should fail clearly rather than send
as `control`.

## Commit boundaries

When implementation starts, keep commits atomic and use Conventional Commits.
Good boundaries:

1. Package scaffold and docs.
2. Direct protocol client and tests.
3. TUI listener, state, inbox, and notification behavior.
4. Command and tool surface.
5. Tests and UAT documentation.
6. Packaging, root docs, and quality-gate updates.

## Validation expectations

Before handing back each completed plan item:

1. Run the checks listed in that plan file.
2. Run `git diff --check`.
3. Summarize what changed, what was validated, and what remains.
4. If a check cannot run in the container, say why and provide the closest
   validation performed.

Before marking the phase complete:

1. Run OpenCode package checks.
2. Run `./run-checks.sh` from the project root.
3. Complete the manual OpenCode UAT checklist in
   `docs/roadmap/opencode-support/06-live-tests-and-fixtures.md`, or document why
   any item could not be completed.

## Research references

The plan is based on OpenCode plugin documentation, local reference research,
the existing Pi TypeScript extension, and the inter-agent protocol/security
model.

Useful OpenCode docs to re-check:

- `https://opencode.ai/docs/plugins/`
- `https://opencode.ai/docs/custom-tools/`
- `https://opencode.ai/docs/commands/`
- `https://opencode.ai/docs/config/`
- `https://opencode.ai/docs/sdk/`
- `https://opencode.ai/docs/server/`
- `https://opencode.ai/docs/agents/`
- `https://opencode.ai/docs/ecosystem/`

If a local OpenCode clone is available under `/workspace/projects/_git/opencode`,
re-check these files when API behavior is uncertain:

- `packages/plugin/src/tui.ts`
- `packages/plugin/src/index.ts`
- `packages/opencode/src/cli/cmd/tui/plugin/runtime.ts`
- `packages/opencode/src/plugin/shared.ts`
- `packages/opencode/src/plugin/install.ts`
- `packages/opencode/src/cli/cmd/tui/feature-plugins/system/notifications.ts`
- `packages/opencode/src/cli/cmd/tui/attention.ts`
