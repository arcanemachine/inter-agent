# OpenCode Extension Design

Extra Phase: 8 — OpenCode Support

## Purpose

Design OpenCode support as a first-class host-native extension before writing implementation code.

Read `plans/08-opencode-support/00-execution-guide.md` before executing this plan item. Follow the execution guide's order, spike requirement, and stop conditions.

The OpenCode integration should follow the successful Pi extension UX where OpenCode supports it: host-native commands, LLM-callable tools, a persistent listener, visible notifications, state persistence, and safe handling of incoming peer messages.

## Research basis

Local OpenCode research found a dual plugin architecture:

- TUI plugins expose commands, keybindings, lifecycle cleanup, KV state, toasts, attention notifications, slots, and event subscriptions.
- Server plugins expose hooks and LLM-callable tools.
- Plugin packages must expose separate target modules for `./tui` and `./server`; one module must not export both.
- TUI plugins run as normal Bun modules with WebSocket, fetch, filesystem, environment, and npm dependency access.
- TUI plugins can own long-lived background tasks through `api.lifecycle.signal` and `api.lifecycle.onDispose()`.

Key OpenCode reference files from the local clone:

- `packages/plugin/src/tui.ts`
- `packages/plugin/src/index.ts`
- `packages/opencode/src/cli/cmd/tui/plugin/runtime.ts`
- `packages/opencode/src/plugin/shared.ts`
- `packages/opencode/src/plugin/install.ts`
- `packages/opencode/src/cli/cmd/tui/feature-plugins/system/notifications.ts`
- `packages/opencode/src/cli/cmd/tui/attention.ts`

## Scope

- Add an OpenCode integration package under `integrations/opencode/`.
- Use direct TypeScript WebSocket protocol access from the OpenCode plugin; do not require Python, `uv`, or subprocess CLI bridges for routine OpenCode use.
- Provide TUI commands and server-side LLM tools for the standard inter-agent operations.
- Implement a persistent listener inside the TUI plugin.
- Keep all OpenCode-specific behavior inside the integration boundary.
- Preserve the existing core protocol and security model.

## Non-goals

- Do not add OpenCode-specific semantics to the core protocol.
- Do not depend on a patched or forked OpenCode.
- Do not build Codex support in this phase. Codex does not currently expose a no-fork extension surface that can provide the same background message delivery UX; any future Codex work should be treated as an App Server sidecar investigation, not a Codex extension plan.
- Do not rely on prompt injection as the primary message delivery path. Use notifications and an inbox first; add prompt insertion only if the current OpenCode API supports it cleanly.

## Design decisions to confirm before implementation

1. **Package shape**
   - One npm package in `integrations/opencode/`.
   - Separate exports for `./tui` and `./server`.
   - Shared implementation modules imported by both entry points.

2. **Protocol strategy**
   - Implement a direct TypeScript client for the inter-agent WebSocket protocol.
   - Port only the client-side pieces needed by OpenCode: token loading, server identity verification, hello handshake, control operations, listener loop, error handling, and message formatting.
   - Keep subprocess CLI fallback out of the first implementation unless a spike proves direct WebSocket is not viable.

3. **Session identity**
   - Default name should be explicit and user-controllable.
   - Persist active connection state with OpenCode TUI KV.
   - Use the active listener name as `from_name` for outgoing tool and command messages.
   - Reject invalid names using the same name rules as the core server.

4. **Inbound delivery**
   - The TUI plugin owns the persistent listener.
   - Incoming messages produce bounded OpenCode attention notifications and toasts.
   - Full message content is stored in a plugin inbox when notification text is truncated.
   - Incoming messages do not override system, developer, user, tool, permission, or OpenCode safety rules.

5. **Command and tool model**
   - TUI commands provide human-facing slash and palette actions.
   - Server plugin tools provide LLM-callable operations.
   - Tool calls use short-lived control connections unless a safe shared-connection bridge is designed and tested.

6. **Security model**
   - Stay within inter-agent's local, same-user, localhost threat model.
   - Verify server identity before sending the shared token.
   - Read tokens and state from the configured inter-agent data directory.
   - Keep any plugin-owned state files restrictive where OpenCode APIs allow it.

## Work

1. Re-check the current OpenCode plugin API against the local clone before implementation begins.
2. Write a concise design note in `integrations/opencode/README.md` or a dedicated integration design file.
3. Define the OpenCode install model, including local development install with `file://` plugin specs.
4. Define default config keys: data directory, host, port, connection name, label, notification length, inbox length, and auto-connect behavior.
5. Define the exact TUI command names and slash aliases.
6. Define the exact LLM tool names, parameters, and result shapes.
7. Define notification, toast, inbox, truncation, and continuation behavior.
8. Define reaction policy text for incoming messages.
9. Define the manual user acceptance test before implementation.
10. Only then proceed to scaffold and protocol implementation.

## Acceptance criteria

- The design explains why OpenCode uses direct WebSocket rather than the Pi CLI bridge.
- The design identifies the TUI plugin as the listener owner.
- The design identifies the server plugin as the LLM tool owner.
- The design includes install, identity, state, notification, command, tool, security, and testing decisions.
- The design states that Codex extension development is out of scope because Codex's no-fork extension surface cannot provide equivalent background delivery.

## Files likely to change

- `integrations/opencode/README.md`
- `integrations/opencode/package.json`
- `integrations/opencode/src/`
- `plans/08-opencode-support/`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`

## Checks

- Documentation review against current OpenCode plugin APIs
- `npm run typecheck` inside `integrations/opencode/` once the package exists
- `./run-checks.sh` before phase completion
