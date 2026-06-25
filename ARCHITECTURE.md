# Architecture

`inter-agent` is a localhost WebSocket message bus for AI coding sessions.

## Layers

1. **Core protocol (`src/inter_agent/core/`)**
   - Handshake/auth (`hello` / `welcome`)
   - Presence and identity (`session_id`, routing `name`, display-only `label`)
   - Routing (`send`, `broadcast`, `custom` pass-through)
   - Health and lifecycle (`ping` / `pong`, `bye`, authenticated `shutdown`)
   - Session management (control-only `kick` to force-disconnect a registered session by name or session_id)
   - Introspection (`list` capability)
   - Importable command APIs for server start, connect, send, broadcast, list, and status checks.

2. **Adapters (`src/inter_agent/adapters/`)**
   - Host-specific command UX and integration.
   - Call importable core command APIs rather than spawning core scripts by file path.
   - May expose only a subset of core-supported operations.
   - Pi adapter (`pi/`) provides TypeScript extension integration.
   - Claude Code adapter (`claude/`) provides Monitor-backed listener and CLI commands, and suppresses identical repeated sends within a short window so agent-loop re-fires do not duplicate deliveries.
   - Integration assets for each host live under `integrations/<host>/`.

3. **Spec (`spec/`)**
   - AsyncAPI contract in `spec/asyncapi.yaml`.
   - Standalone JSON Schemas for protocol operations in `spec/schemas/`.
   - Example payloads for canonical behavior in `spec/examples/`.
   - Canonical protocol error codes in `spec/error-codes.md`.

## Messaging model

- Session identity: active `session_id` values are unique. A duplicate active `session_id` is rejected; the ID may be reused after the previous connection closes.
- Direct message: sender targets one agent by routing name. Resolution checks exact names first, then unique routing-name prefixes. Ambiguous prefixes are rejected.
- Label: optional human-readable display metadata returned by introspection; labels are never routing keys.
- List introspection returns agent sessions sorted by routing name and excludes control sessions.
- Broadcast: sender targets all other connected agents.
- Custom: extension envelope (`op: custom`, `custom_type`, `payload`), routed by core without type-specific interpretation after type and payload-size checks.
- Error: canonical `error` envelopes use documented codes from `spec/error-codes.md`; clients should key behavior on `code`, not `message`.
- Resource boundaries: direct and broadcast text limits use UTF-8 encoded byte length after JSON decoding; active connections, custom types, and JSON-encoded custom payloads also have configurable limits.

## Server lifecycle

- The server can be started manually (`uv run inter-agent-server`) or auto-started by adapters when a client connects and the server is not running.
- Manual starts run until explicit shutdown by default. Passing `--idle-timeout <seconds>` opts in to automatic shutdown after that idle period; `--idle-timeout 0` also leaves the timeout disabled.
- Adapters that auto-start the server, including Pi `/inter-agent-connect` and Claude Code `listen`, pass an explicit 300-second idle timeout, verify the server is reachable before proceeding, and retry for up to 15 seconds after launching the server process.

## Configuration and lifecycle state

- The default endpoint is `127.0.0.1:16837`.
- Endpoint resolution uses explicit CLI options first, then `INTER_AGENT_HOST` / `INTER_AGENT_PORT`, then the inter-agent JSON config file, then built-in defaults.
- The config file is `INTER_AGENT_CONFIG` when set, otherwise `${XDG_CONFIG_HOME:-~/.config}/inter-agent/config.json` on Linux and `~/Library/Application Support/inter-agent/config.json` on macOS.
- Server state lives under `INTER_AGENT_DATA_DIR`, then the config file `dataDir`, then `${XDG_STATE_HOME:-~/.local/state}/inter-agent` on Linux or `~/Library/Application Support/inter-agent` on macOS.
- The token file, server identity metadata, PID metadata, and reserved shutdown-control metadata are per-user local files with restrictive permissions.
- Server identity metadata is written atomically and includes host, port, PID, state schema version, startup timestamp, instance nonce, and a platform process start marker when available.
- Startup refuses to replace live metadata for the same port and removes stale metadata for dead server processes when safe.
- Authenticated shutdown stops accepting new connections, closes active sessions, and removes server lifecycle metadata during normal shutdown.
- Status checks report available, unavailable, identity-check-failed, auth-failed, and protocol-mismatch states for host tooling, along with the resolved configuration, discovered live server metadata, and endpoint hints.
- When client/control commands target an unavailable configured endpoint and exactly one live server is discovered in lifecycle metadata, they use the discovered endpoint. Server startup always binds the resolved configured endpoint and does not use discovery fallback.

## Capability exchange

- `hello.capabilities` is a required JSON object where clients may declare known or extension capability keys.
- Unknown client capability keys are tolerated and may be ignored; client declarations do not enable unimplemented features.
- `welcome.capabilities` advertises server-supported baseline capabilities: `core.version` is `0.1`, `channels` is `false`, and `rate_limit` is `false`.
- Future channel routing and policy negotiation ideas remain in `IDEAS.md` until promoted into the plan.

## Evolution touchpoints

- Middleware/router hook points reserved for future channel/pub-sub and rate-limit policies.
