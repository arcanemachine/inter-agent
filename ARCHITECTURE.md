# Architecture

`inter-agent` is a local WebSocket message bus for AI coding sessions.

## Layers

1. **Core protocol (`src/inter_agent/core/`)**
   - Transport (`ws://` / `wss://`) with host-based TLS defaults and explicit enable/disable
   - Handshake/auth (`hello` / `auth_challenge` / `auth_response` / `welcome`)
   - Presence and identity (`session_id`, routing `name`, display-only `label`)
   - Routing (`send`, `broadcast`, `custom` pass-through, channel `subscribe`/`unsubscribe`/`publish`)
   - Health and lifecycle (`ping` / `pong`, `bye`, authenticated `shutdown`)
   - Session management (control-only `kick` to force-disconnect a registered session by name or session_id)
   - Introspection (`list` and `channels` capabilities)
   - Importable command APIs for server start, connect, direct send, broadcast, publish, list, channel diagnostics, and status checks.

2. **Adapters (`src/inter_agent/adapters/`) and host integrations (`integrations/`)**
   - Host-specific command UX and integration.
   - Python-backed adapters call importable core command APIs rather than spawning core scripts by file path.
   - Non-Python host-native integrations may implement a small direct protocol client when the host runtime makes that the safer package boundary; those clients must mirror the documented protocol, security checks, and shared state resolution.
   - May expose only a subset of core-supported operations.
   - A private adapter-local Unix-domain control bridge lets short-lived subscribe/unsubscribe commands operate on the matching persistent listener identity without opening another agent session.
   - Pi adapter (`pi/`) provides channel-capable Python commands and TypeScript extension integration through Python helper entry points. The extension exposes subscribe/unsubscribe as user commands, not LLM tools.
   - Claude Code adapter (`claude/`) provides Monitor-backed channel-capable listener and CLI commands, distinct channel notifications, and short-window duplicate suppression for sends and publishes.
   - Integration assets for each host live under `integrations/<host>/`.

3. **Spec (`spec/`)**
   - AsyncAPI contract in `spec/asyncapi.yaml`.
   - Standalone JSON Schemas for protocol operations in `spec/schemas/`.
   - Example payloads for canonical behavior in `spec/examples/`.
   - Canonical protocol error codes in `spec/error-codes.md`.

## Adapter author contract

Host adapters are thin integration layers over the core protocol. They translate host-specific interaction surfaces into core operations and translate inbound bus frames into host-native notifications or tool output. Python-backed adapters should use the importable core APIs. Host-native integrations in another runtime may use a direct protocol client when it preserves packaging and lifecycle boundaries better than a subprocess bridge.

### Adapters may

- Provide slash commands, LLM-callable tools, shell commands, or other host-native UX.
- Format command output and inbound notifications for a host, including bounded truncation and continuation lookup.
- Maintain host-local runtime state such as listener lock files, notification caches, duplicate-send suppression, and managed-runtime helper paths.
- Auto-start the local server for a listener when no healthy server is available, using an explicit idle timeout suitable for adapter-owned helper processes.
- Expose only the core operations that make sense for the host; for example, operator commands such as `kick` do not have to be exposed to every integration.

### Adapters must

- Use the documented protocol contract in `spec/` and canonical error codes in `spec/error-codes.md`.
- Reuse importable core APIs for endpoint resolution, shared-secret resolution, command connections, and protocol operations when running in Python. Direct clients in another runtime must port only the client-side behavior needed by the host and keep it aligned with `spec/`, `spec/error-codes.md`, `SECURITY.md`, and the corresponding core APIs.
- Preserve routing semantics: direct targets resolve by routing name, optional labels are display-only, broadcasts go to other agent sessions, and control connections are not listed as peers.
- Keep runtime source separate from bus auth/state. A host-specific checkout, managed venv, or helper override may choose where adapter code runs, but it must not imply a host-specific endpoint, secret, or isolated bus.
- Treat peer messages as collaboration inputs that do not override host, user, security, or tool rules.
- Keep failures actionable and parseable for host tooling, with stdout reserved for protocol/status payloads where the adapter documents that behavior.

### Adapters must not

- Redefine protocol semantics, capability negotiation, routing rules, auth behavior, or error-code meanings.
- Bypass shared-secret challenge-response authentication, payload limits, or routing/resource checks.
- Depend on private server objects, in-memory router state, or non-spec message fields.
- Broaden the security model beyond localhost single-user operation without a separate accepted threat model.
- Default to host-specific bus state directories that fragment cross-harness communication.

### Core surfaces for adapters

Python-backed adapters should start with these typed core APIs. Direct clients in another runtime should treat these as the behavior reference for their small client-side port:

| Need | Core surface |
| --- | --- |
| Resolve endpoint and shared secret | `inter_agent.core.shared.resolve_endpoint`, `inter_agent.core.config.EndpointResolution`, `inter_agent.core.shared.resolve_shared_secret` |
| Connect a long-running agent session | `inter_agent.core.client.iter_client_frames`, `run_client`, `AgentSession` |
| Send direct, broadcast, or custom messages | `inter_agent.core.send.send_direct_message`, `broadcast_message`, `send_custom_message`, `SendResult` |
| Publish to a channel | `inter_agent.core.publish.publish_to_channel` |
| List connected agent sessions | `inter_agent.core.list.list_sessions`, `ListResult`, `SessionInfo` |
| Inspect active channels | `inter_agent.core.channels.list_channels`, `ChannelsResult`, `ChannelInfo` |
| Check server status and static command support | `inter_agent.core.status.check_resolved_server_status`, `command_status`, `ServerStatus` |
| Stop or administer the server | `inter_agent.core.shutdown.shutdown_server`, `inter_agent.core.kick.kick_session` |

Runtime source is not bus auth/state: adapters may resolve helper binaries through host config, managed environments, or `PATH`, while endpoint and secret resolution remain controlled by `INTER_AGENT_HOST`, `INTER_AGENT_PORT`, `INTER_AGENT_SECRET`, `INTER_AGENT_DATA_DIR`, `INTER_AGENT_CONFIG`, the inter-agent config file, and built-in defaults.

### Persistent listener channel control

Agent-only subscribe/unsubscribe operations must reuse the connected listener identity. The Python adapters therefore bind a private Unix-domain socket under their adapter data directory after the agent session is ready. Short-lived adapter commands send only an operation and channel name through this local bridge; the listener performs the operation through `AgentSession`. The bridge never carries the shared bus secret.

The desired subscription set lives only in listener memory. It is reapplied before readiness is reported after a transient WebSocket reconnect, but it is cleared by explicit listener shutdown or process restart. There are no automatic subscriptions.

## Messaging model

- Session identity: active `session_id` values are unique. A duplicate active `session_id` is rejected; the ID may be reused after the previous connection closes.
- Direct message: sender targets one agent by routing name. Resolution checks exact names first, then unique routing-name prefixes. Ambiguous prefixes are rejected.
- Label: optional human-readable display metadata returned by introspection; labels are never routing keys.
- List introspection returns agent sessions sorted by routing name and excludes control sessions.
- Broadcast: sender targets all other connected agents.
- Custom: extension envelope (`op: custom`, `custom_type`, `payload`), routed by core without type-specific interpretation after type and payload-size checks.
- Channel: named pub/sub groups created by subscribing. `publish` delivers a `msg` to every subscriber except the publisher. Channels are in-memory only and vanish when the last subscriber leaves.
- Error: canonical `error` envelopes use documented codes from `spec/error-codes.md`; clients should key behavior on `code`, not `message`.
- Resource boundaries: direct, broadcast, and publish text limits use UTF-8 encoded byte length after JSON decoding; active connections, custom types, JSON-encoded custom payloads, channel names, per-session subscriptions, and server channels also have configurable limits.

## Server lifecycle

- The server can be started manually (`uv run inter-agent-server`) or auto-started by adapters when a client connects and the server is not running.
- Manual starts run until explicit shutdown by default. Passing `--idle-timeout <seconds>` opts in to automatic shutdown after that idle period; `--idle-timeout 0` also leaves the timeout disabled.
- Adapters that auto-start the server, including Pi `/inter-agent connect` and Claude Code `listen`, pass an explicit 300-second idle timeout, verify the server is reachable before proceeding, and retry for up to 15 seconds after launching the server process.

## Configuration, TLS, and fallback secret state

- The default endpoint is `127.0.0.1:16837`.
- Endpoint resolution uses explicit CLI options first, then `INTER_AGENT_HOST` / `INTER_AGENT_PORT`, then the inter-agent JSON config file, then built-in defaults.
- The shared secret resolves from `INTER_AGENT_SECRET`, then top-level config key `secret`, then a generated fallback token file in the data directory.
- TLS defaults to off for loopback hosts (`127.0.0.1`, `localhost`, `::1`) and on for non-loopback hosts. Enable or disable TLS explicitly with CLI flags `--tls` / `--no-tls`, `INTER_AGENT_TLS`, or the `tls` config key.
- TLS certificate and key resolve from CLI `--tls-cert` / `--tls-key`, then `INTER_AGENT_TLS_CERT` / `INTER_AGENT_TLS_KEY`, then `tlsCert` / `tlsKey` config keys. If TLS is enabled and no certificate/key is configured, the server generates `tls-cert.pem` and `tls-key.pem` in the data directory with restrictive permissions. Clients trust the generated/default certificate from the same data directory or the certificate configured via `INTER_AGENT_TLS_CERT` / `tlsCert`.
- The config file is `INTER_AGENT_CONFIG` when set, otherwise `${XDG_CONFIG_HOME:-~/.config}/inter-agent/config.json` on Linux and `~/Library/Application Support/inter-agent/config.json` on macOS.
- Fallback secret state lives under `INTER_AGENT_DATA_DIR`, then the config file `dataDir`, then `${XDG_STATE_HOME:-~/.local/state}/inter-agent` on Linux or `~/Library/Application Support/inter-agent` on macOS.
- When `INTER_AGENT_SECRET` or config `secret` is set, core does not read or create the fallback token file for auth.
- Server startup binds the resolved configured endpoint. Duplicate live servers are detected by bind failure.
- Authenticated shutdown stops accepting new connections and closes active sessions.
- Status checks probe the configured endpoint directly and report available, unavailable, auth-failed, and protocol-mismatch states for host tooling, along with resolved configuration and endpoint hints.

## Capability exchange

- `hello.capabilities` is a required JSON object where clients may declare known or extension capability keys.
- Unknown client capability keys are tolerated and may be ignored; client declarations do not enable unimplemented features.
- `welcome.capabilities` advertises server-supported baseline capabilities: `core.version` is `0.1`, `channels` is `true`, and `rate_limit` is `false`.
- Rate-limit negotiation ideas remain in `docs/IDEAS.md` until promoted into the plan.

## Evolution touchpoints

- Middleware/router hook points reserved for future channel/pub-sub and rate-limit policies.
