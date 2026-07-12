# Codex sidecar validation spike

Status: seed; not implemented; not active.

## Purpose

Validate the first Codex App Server sidecar assumption before any Codex integration implementation is planned.

Codex remains sequenced after OpenCode. This file preserves the smallest validation slice and current assumptions so a future worker can start from a bounded task.

## References

- `integrations/codex/README.md`
- Local Codex checkout when available: `/workspace/projects/_git/codex`
- Codex App Server documentation for the target Codex version

## Smallest validation slice

Prove that a sidecar process can attach to a live Codex App Server endpoint and inject one inbound inter-agent-style message into a selected loaded thread.

The validation should demonstrate:

1. reliable discovery or explicit configuration of the Codex App Server endpoint;
2. WebSocket-over-Unix-socket attachment when using Codex unix socket transport;
3. thread discovery and user-understandable thread selection;
4. `thread/inject_items` behavior against a selected loaded thread;
5. whether injected items are model-visible, human-visible in the active CLI/TUI, both, or neither;
6. safe fallback to a bounded sidecar inbox when no thread is selected.

## Known assumptions to revalidate

- Codex plugins are not enough for automatic inbound delivery; they can package skills, MCP servers, hooks, and app metadata but do not provide a persistent listener runtime.
- Unix socket App Server transport is WebSocket over a Unix socket with HTTP Upgrade, not raw JSONL.
- Dynamic tools require experimental API capability opt-in.
- App Server WebSocket auth/token behavior must be checked for the target Codex version.
- `turn/steer` remains opt-in future behavior because it changes an active turn.

## Non-goals for the spike

- No production sidecar package.
- No automatic daemon lifecycle.
- No plugin-only implementation claim.
- No forked Codex dependency.
- No broad MCP or dynamic-tool surface unless needed to validate outbound behavior after endpoint/injection succeeds.

## Concrete worker task template

When activated, assign a worker this bounded task:

1. Read `AGENTS.md`, `integrations/codex/README.md`, and this file.
2. Inspect `/workspace/projects/_git/codex` read-only if present.
3. Verify current App Server transport, auth, and `thread/inject_items` APIs against local source and docs.
4. Produce a minimal spike design: command to start/attach App Server, sidecar transport library/API, payload shape, manual UAT steps, and safety checks.
5. Do not edit implementation files unless the spike is explicitly promoted into `.agents/PLAN.md`.

## Acceptance criteria for a future spike

- A sidecar can attach to Codex App Server without a forked Codex build.
- A selected thread receives an injected collaboration message.
- The user can observe whether the message is visible in the target Codex UI and model context.
- Sidecar state and inter-agent secrets are not injected into Codex-visible content.
- Findings update `integrations/codex/README.md` or a concrete plan file before implementation begins.
