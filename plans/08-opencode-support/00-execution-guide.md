# OpenCode Support Execution Guide

Extra Phase: 8 — OpenCode Support

## Purpose

This is the worker-facing guide for executing the OpenCode support plan.

Follow the plan files in order. Do not jump directly into implementation. The plan assumes a reasonably competent agent who may not have the original research context, so this file states the sequence, required checkpoints, and stop conditions.

## Phase goal

Build an OpenCode host-native integration for inter-agent.

The target user experience is similar to the Pi extension where OpenCode supports it:

- OpenCode users can connect to the inter-agent bus from inside OpenCode.
- OpenCode users can send, broadcast, list, check status, disconnect, inspect recent inbound messages, and shut down through documented commands.
- OpenCode agents can call LLM tools for send, broadcast, list, and status.
- Incoming messages appear through OpenCode notifications/toasts and are retained in a bounded inbox.
- The OpenCode plugin speaks the inter-agent WebSocket protocol directly unless an early spike proves this is not practical.

## Non-goal: Codex extension

Do not implement a Codex extension in this phase.

Codex's no-fork extension surfaces do not currently provide the background message delivery and control surface needed for an inter-agent extension comparable to Pi or OpenCode. Any future Codex work should be tracked separately as an App Server sidecar investigation, not as a Codex extension.

## Required execution order

Complete these plan files in order:

1. `plans/08-opencode-support/01-opencode-extension-design.md`
2. `plans/08-opencode-support/02-package-scaffold-and-installation.md`
3. `plans/08-opencode-support/03-direct-protocol-client.md`
4. `plans/08-opencode-support/04-tui-listener-state-and-notifications.md`
5. `plans/08-opencode-support/05-command-tool-surface-and-reaction-policy.md`
6. `plans/08-opencode-support/06-live-tests-and-fixtures.md`
7. `plans/08-opencode-support/07-packaging-docs-and-quality-gate.md`

Do not implement later files before the acceptance criteria for earlier files are met, except for small scaffolding changes that are explicitly required by the current file.

## Required early spike

Before building the full TypeScript protocol client, prove that direct WebSocket access from an OpenCode plugin is practical.

The spike should prove the smallest useful path:

1. A local OpenCode TUI plugin can load.
2. The plugin can open a WebSocket connection from the OpenCode runtime.
3. The plugin can read the inter-agent token and server metadata from the configured data directory.
4. The plugin can send a valid `hello` envelope to a live inter-agent server.
5. The plugin can receive a `welcome` frame.
6. If possible, the plugin can receive one `msg` frame from another inter-agent client.

If this spike fails, stop and report before implementing the rest of the OpenCode package. Do not silently fall back to a Python CLI bridge without an accepted design change.

## Expected architecture

Use this architecture unless a plan update is accepted:

1. **OpenCode TUI plugin**
   - Owns the persistent listener.
   - Registers user-facing commands.
   - Stores connection state and inbox data.
   - Displays incoming messages through notifications/toasts.
   - Cleans up with OpenCode lifecycle APIs.

2. **OpenCode server plugin**
   - Registers LLM-callable inter-agent tools.
   - Uses short-lived control WebSocket connections for send, broadcast, list, and status.
   - Uses the active OpenCode connection name as `from_name` when sending.

3. **Shared TypeScript protocol client**
   - Implements token loading, server identity verification, hello handshake, control operations, listener frames, and protocol error handling.
   - Does not depend on Python, `uv`, or subprocess calls for routine OpenCode behavior.

## Important implementation constraints

1. Keep OpenCode behavior inside `integrations/opencode/` unless core changes are explicitly required and documented.
2. Do not change the inter-agent protocol for OpenCode-specific convenience.
3. Do not modify `/workspace/projects/_git/opencode`; it is a reference clone.
4. Keep OpenCode package exports split by target: `./tui` and `./server`.
5. Do not default-export both TUI and server plugin behavior from one module.
6. Do not store the inter-agent token in OpenCode KV or logs.
7. Verify server identity before sending the token.
8. Preserve sender identity with `from_name`; do not let routine sends appear as `control`.
9. Do not make peer messages higher-priority than system, developer, user, tool, permission, or security rules.
10. Do not add TODO/FIXME comments to code.

## Stop and ask conditions

Stop and ask the user, or update the plan and get acceptance, if any of these occur:

1. OpenCode's current plugin API no longer supports long-lived TUI plugin tasks.
2. OpenCode's current plugin API no longer supports separate `./tui` and `./server` package targets.
3. Direct WebSocket access from an OpenCode plugin does not work.
4. The plugin cannot read the token or identity metadata from the inter-agent data directory.
5. Server identity verification cannot be implemented safely enough to preserve the security model.
6. Server plugin tools cannot determine the active OpenCode sender identity.
7. Implementing a feature would require forking or patching OpenCode.
8. Implementing a feature would require changing the core protocol.
9. Interactive OpenCode behavior materially differs from the researched behavior.
10. Tests cannot be made reliable without requiring an interactive OpenCode TUI in the required quality gate.

## Contingency guidance

The preferred path is direct WebSocket from an OpenCode plugin. The fallbacks below are not permission to silently change architecture. They are intended to help a worker agent make a good recommendation if a stop condition occurs.

### If direct WebSocket fails

First determine why it failed:

1. If WebSocket is unavailable in the plugin runtime, re-check whether the failure is specific to the TUI plugin, the server plugin, or the test scaffold.
2. If WebSocket works but filesystem/token access fails, see the token and metadata fallback below.
3. If WebSocket works but protocol handshake fails, fix the TypeScript protocol client rather than changing architecture.

Possible backup designs, in preferred order:

1. **OpenCode sidecar bridge** — a separate local process owns the inter-agent WebSocket listener and exposes a small localhost API to the OpenCode plugin. This preserves OpenCode notifications/commands but adds another process. Prefer this over a per-command CLI bridge if OpenCode cannot keep a listener alive.
2. **Pi-style subprocess bridge** — the plugin spawns existing inter-agent Python CLIs for control operations and a long-lived listener process for inbound messages. This is proven by Pi but less desirable because it requires Python/`uv`/project-path configuration and stdout parsing.
3. **Command-only integration** — expose send, broadcast, list, and status commands/tools without live receiving. This is a major UX regression and should not be accepted as Phase 8 completion without user approval.
4. **Defer OpenCode support** — if OpenCode cannot provide stable plugin networking or process integration, stop and report.

### If token or metadata access fails

Expected path: read `INTER_AGENT_DATA_DIR` or `~/.inter-agent` directly from the OpenCode plugin runtime.

Possible backup designs:

1. Add explicit OpenCode plugin config for `dataDir`, then retry direct file access.
2. If sandboxing prevents file access entirely, use a sidecar bridge that reads token/metadata outside OpenCode and exposes only safe local operations to the plugin.
3. If only token creation fails, require the server or an inter-agent CLI command to be run once before OpenCode connects.
4. Do not ask users to paste the shared token into OpenCode config unless the security model is reviewed and accepted.

### If server identity verification cannot be fully ported

Expected path: port the Python metadata checks closely enough to preserve `SECURITY.md` behavior.

Possible backup designs:

1. Implement strict verification on Linux and fail closed on unsupported platforms for the first release.
2. Document a user-enabled degraded mode only after explicit acceptance. The degraded mode must warn that server identity verification is weaker.
3. Use a sidecar or Python bridge for identity verification if direct TypeScript verification is the only blocker.

Do not silently skip identity verification before sending the token.

### If TUI and server plugin state sharing is difficult

Expected path: store active connection identity in a shared OpenCode/plugin-accessible state location so server tools can send with `from_name`.

Possible backup designs, in preferred order:

1. Persist active identity in OpenCode KV or another state file readable by both plugin targets.
2. Add explicit plugin config for the default sender name, and require it to match the connected listener name.
3. Make server tools fail with a clear message until a connected identity is available.
4. Ship TUI commands first and defer LLM tools only if the user accepts a reduced first milestone.

Do not let routine tool sends appear as `control`; that makes peer messages confusing and breaks the intended UX.

### If OpenCode cannot keep a long-lived listener alive

Possible backup designs:

1. Use an external sidecar listener and let the TUI plugin display messages received through a localhost bridge.
2. Use a Pi-style long-lived child process if OpenCode can spawn and supervise child processes but cannot keep an in-process WebSocket listener.
3. Fall back to manual inbox polling only as a reduced, user-approved milestone.

This is a high-severity issue because live receiving is part of the Phase 8 completion criteria.

### If separate `./tui` and `./server` package targets fail

Possible backup designs:

1. Re-check OpenCode package resolution and install configuration; this may be a packaging bug rather than an API limitation.
2. Split the integration into two packages, one TUI plugin and one server plugin.
3. Ship TUI-only support first only if the user accepts deferring LLM tools.

### If prompt injection is not viable

This is not a blocker.

The planned first release does not require prompt injection. Use notifications, toasts, and inbox entries for incoming messages. Add prompt insertion later only if OpenCode exposes a stable API and the behavior is safe.

### If tests require an interactive OpenCode TUI

Do not put interactive OpenCode tests in the required quality gate.

Backup validation strategy:

1. Keep pure TypeScript unit tests in the package gate.
2. Keep live inter-agent protocol tests outside the interactive TUI.
3. Use structural package tests for exports and metadata.
4. Document manual OpenCode UAT separately and run it before declaring the phase complete.

### If implementation would require forking OpenCode or changing the core protocol

Stop.

The accepted plan is no OpenCode fork and no OpenCode-specific core protocol changes. Recommend a reduced integration, sidecar bridge, or deferral instead.

## Commit boundaries

Make commits at logical milestones:

1. Package scaffold and docs.
2. Direct protocol client and tests.
3. TUI listener/state/notification behavior.
4. Command and tool surface.
5. Tests and UAT documentation.
6. Packaging/docs/quality-gate updates.

Keep commit messages brief and use Conventional Commits style.

## Validation expectations

Before handing back each completed plan item:

1. Run the checks listed in that plan file.
2. Run `git diff --check`.
3. Summarize what changed, what was validated, and what remains.
4. If a check cannot run in the container, say why and provide the closest validation performed.

Before marking the phase complete:

1. Run OpenCode package checks.
2. Run `./run-checks.sh` from the project root.
3. Complete the manual OpenCode UAT checklist in `plans/08-opencode-support/06-live-tests-and-fixtures.md` or document exactly why any item could not be completed.

## Research references

The plan was based on local research of the OpenCode clone under `/workspace/projects/_git/opencode`.

Key files to re-check if OpenCode behavior is uncertain:

- `packages/plugin/src/tui.ts`
- `packages/plugin/src/index.ts`
- `packages/opencode/src/cli/cmd/tui/plugin/runtime.ts`
- `packages/opencode/src/plugin/shared.ts`
- `packages/opencode/src/plugin/install.ts`
- `packages/opencode/src/cli/cmd/tui/feature-plugins/system/notifications.ts`
- `packages/opencode/src/cli/cmd/tui/attention.ts`

Use targeted research if these files have changed or if the local OpenCode version differs from the researched version.
