# inter-agent for Codex

Codex support is a prospective integration for the `inter-agent` localhost
message bus. It has not been implemented or added as a supported integration.
This document records the current design direction after reviewing the public
Codex documentation and an OpenAI Codex source checkout.

The recommended direction is not a plugin-only Codex extension. The viable
integration path is a Codex App Server sidecar.

## Current conclusion

A Codex plugin can package useful supporting assets, but it is not sufficient
for a Pi- or OpenCode-style inter-agent integration. Codex plugins can bundle
skills, MCP servers, app connector metadata, and lifecycle hooks. Those surfaces
are useful for instructions and request/response tools, but they do not provide a
persistent background runtime inside the Codex TUI that can own an inter-agent
listener or push inbound messages to the user automatically.

The prospective architecture is:

```text
inter-agent Python server/core
        ^
        | JSON frames over localhost WebSocket
        v
Codex sidecar process
        ^
        | JSON-RPC over Codex App Server transport
        v
Codex App Server
        ^
        | loaded threads, turns, tools, events
        v
Codex CLI/TUI or another App Server client
```

The sidecar would be the long-running process. It would connect to the
inter-agent bus as a named agent session, listen for inbound bus messages, and
use Codex App Server APIs to deliver those messages into selected Codex threads.

## Why not a plugin-only extension

Codex extension surfaces have clear boundaries:

- **Plugins** package skills, MCP server configuration, app connector metadata,
  and hooks for installation and sharing.
- **Skills** provide reusable instructions and references. They do not run
  background listeners.
- **Hooks** run command subprocesses at lifecycle events such as `SessionStart`,
  `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStart`, and
  `SubagentStop`. They are event-scoped command executions, not persistent
  extension runtimes.
- **MCP servers** expose request/response tools and resources. They are a strong
  fit for outbound operations such as send, broadcast, list, status, and inbox
  lookup, but MCP is not an inbound push-notification surface.

A plugin-only design can make Codex better at using inter-agent when the model or
user asks for it. It cannot by itself provide automatic inbound message delivery
comparable to the existing Pi and Claude Code integrations or the prospective
OpenCode TUI plugin design.

## App Server sidecar direction

Codex App Server is the closest fit because it exposes a bidirectional JSON-RPC
control surface for rich clients. The local Codex source and App Server docs show
these relevant APIs:

- `thread/list`, `thread/read`, `thread/resume`, and `thread/loaded/list` for
  discovering and selecting target threads;
- `thread/inject_items` for appending raw Responses API items to a loaded
  thread's model-visible history without starting a user turn;
- `turn/steer` for adding user input to an already in-flight regular turn when a
  safe policy allows that;
- dynamic tools, when the client opts into the experimental API, for
  client-handled tool calls during a turn;
- `mcpServer/*`, `plugin/*`, `skills/*`, and `hooks/*` APIs for inspecting or
  configuring supporting extension assets;
- event notifications for turn, item, approval, hook, MCP, and thread status
  changes.

The sidecar should use the App Server unix-socket transport where practical.
The WebSocket transport exists but is documented as experimental and unsupported
for production workloads. A first spike should avoid depending on unsupported
WebSocket behavior unless unix-socket attachment is not viable for the target
workflow.

## Sidecar responsibilities

The Codex sidecar would own Codex-specific runtime behavior:

1. Resolve and connect to the shared inter-agent bus endpoint and secret.
2. Authenticate with inter-agent challenge-response without sending the raw secret.
3. Connect as a persistent inter-agent agent session with a user-selected routing
   name and optional label.
4. Maintain a connection to Codex App Server through a local control transport.
5. Track the selected Codex thread or explicit thread-selection policy.
6. Deliver inbound direct and broadcast messages into Codex according to a safe
   delivery policy.
7. Expose outbound operations through App Server dynamic tools, an MCP server, or
   both, depending on the validated Codex UX.
8. Store sidecar state separately from inter-agent bus state and Codex secrets.
9. Reconnect with bounded backoff when either the bus or App Server becomes
   temporarily unavailable.

## Inbound delivery policy

Inbound messages are collaboration inputs. They do not override Codex system,
developer, user, tool, permission, sandbox, approval, or security rules.

The first delivery policy should be conservative:

- Prefer `thread/inject_items` for passive, model-visible delivery into a
  selected loaded thread.
- Store a bounded sidecar inbox so messages are not lost when no Codex thread is
  selected or App Server is unavailable.
- Provide a model-callable inbox/status tool so Codex can inspect pending
  messages explicitly.
- Use `turn/steer` only for an accepted, opt-in mode because it affects an active
  turn as if new user input arrived.
- Bound injected text size, truncate display fragments, and preserve full content
  only in sidecar-owned state with documented limits.
- Include sender, direct/broadcast metadata, and delivery time in the injected
  context.

Human-visible notification behavior is an open question. App Server can stream
events to connected clients, but a sidecar is not automatically the active TUI
renderer. A spike must confirm whether injected items, thread events, or another
Codex client path produce acceptable user-visible feedback.

## Outbound commands and tools

Codex should be able to send messages through explicit operations. Candidate
surfaces are:

- a bundled MCP server exposing `send`, `broadcast`, `list`, `status`, and
  `inbox` tools;
- App Server dynamic tools registered by the sidecar for the selected thread;
- a packaged Codex skill that documents when and how Codex should use those
  tools.

MCP is likely the most stable first tool surface because Codex already supports
configured and plugin-bundled MCP servers in both CLI and IDE contexts. Dynamic
tools may provide a tighter App Server sidecar experience but require
experimental API opt-in and should be validated before becoming the primary
path.

## Package shape

A future repository slice may use this shape:

```text
integrations/codex/
  README.md
  .codex-plugin/
    plugin.json
  skills/
    inter-agent/
      SKILL.md
  .mcp.json
  hooks/
    hooks.json
  sidecar/
    README.md
    src/
    tests/
```

The plugin portion would be optional supporting packaging. The sidecar is the
integration owner. Installing the plugin alone must not imply that automatic
inbound delivery is active.

## Setup and lifecycle expectations

A Codex integration will not be as self-contained as a host extension with a
native long-running plugin runtime. Automatic behavior requires a sidecar process
or daemon to be running and attached to Codex App Server.

The target user experience after setup is still automatic:

1. start or ensure the inter-agent server;
2. start or attach to Codex App Server;
3. start the Codex sidecar with a routing name;
4. send and receive inter-agent messages without per-message user interaction.

The exact startup model is an early spike decision. Possible options include:

- a user-started `inter-agent-codex` sidecar command;
- a managed sidecar launched by a Codex hook at `SessionStart`, if lifecycle and
  trust behavior prove acceptable;
- an external supervisor or app-server daemon flow.

The design must not rely on hidden Codex internals or a forked Codex binary.

## Security expectations

The integration must stay inside the existing inter-agent localhost, same-user
security model.

- The sidecar must authenticate with inter-agent challenge-response and must not send the raw shared secret.
- The sidecar must not store inter-agent secrets or proofs in Codex plugin state, Codex
  config, logs, transcripts, or injected model-visible context unless explicitly configured by the user.
- Codex App Server control access must be local-only and use the safest available
  transport for the target platform.
- Inbound peer messages must be injected as untrusted collaboration context, not
  as developer or system instructions.
- Any automatic `turn/steer` behavior must be opt-in and clearly documented.
- App Server WebSocket transport should be treated as experimental unless Codex
  documents it as production-supported before implementation begins.

## Required early spikes

Before implementation starts, copy only a concrete slice into `PLAN.md` and
validate these questions:

1. Can a sidecar reliably discover or start the desired Codex App Server endpoint
   without a forked Codex build?
2. Can the sidecar identify the correct active or selected thread in a way users
   understand?
3. Does `thread/inject_items` create acceptable model-visible and user-visible
   behavior in the active Codex CLI/TUI workflow?
4. Is `turn/steer` safe and useful enough to offer, and should it be disabled by
   default?
5. Should outbound operations use MCP first, dynamic tools first, or both?
6. Can plugin packaging improve install/setup without implying plugin-only
   automatic delivery?
7. What state files are needed for inbox, connection identity, thread selection,
   and reconnect behavior?
8. What manual user acceptance test proves parity with the existing integration
   expectations?

## Acceptance criteria for a future design spike

A design spike is successful when it demonstrates, against a real Codex version:

- sidecar connection to inter-agent and Codex App Server;
- explicit Codex routing name registration;
- inbound direct message delivery to a selected thread;
- outbound `send`, `broadcast`, `list`, and `status` from Codex;
- bounded inbox behavior when no thread is selected;
- reconnection behavior for bus and App Server restarts;
- no secret or proof leakage into Codex-visible state or logs;
- clear documentation that plugin-only Codex support is insufficient and that
  the sidecar owns automatic delivery.

## Sequencing

Codex support is prospective follow-on work. The immediate sequencing is
release/PyPI package readiness for the current implemented integrations,
pub/sub channel work, and OpenCode support. OpenCode is the accepted prospective
host-integration direction ahead of Codex. After the current package release
work, pub/sub channel work, and OpenCode work are addressed, a Codex App Server
sidecar spike is the appropriate next Codex step.
