# Architecture

`inter-agent` is a localhost WebSocket message bus for AI coding sessions.

## Layers

1. **Core protocol (`src/inter_agent/core/`)**
   - Handshake/auth (`hello` / `welcome`)
   - Presence and identity (`session_id`, routing `name`, display-only `label`)
   - Routing (`send`, `broadcast`, `custom` pass-through)
   - Health and lifecycle (`ping` / `pong`, `bye`, authenticated `shutdown`)
   - Introspection (`list` capability)
   - Importable command APIs for server start, connect, send, broadcast, list, and status checks.

2. **Adapters (`src/inter_agent/adapters/`)**
   - Host-specific command UX and integration.
   - Call importable core command APIs rather than spawning core scripts by file path.
   - May expose only a subset of core-supported operations.

3. **Spec (`spec/`)**
   - AsyncAPI contract in `spec/asyncapi.yaml`.
   - Standalone JSON Schemas for protocol operations in `spec/schemas/`.
   - Example payloads for canonical behavior in `spec/examples/`.

## Messaging model

- Direct message: sender targets one agent by routing name. Resolution checks exact names first, then unique routing-name prefixes. Ambiguous prefixes are rejected.
- Label: optional human-readable display metadata returned by introspection; labels are never routing keys.
- Broadcast: sender targets all other connected agents.
- Custom: extension envelope (`op: custom`, `custom_type`, `payload`), routed by core without type-specific interpretation.
- Error: canonical `error` envelopes use documented codes from `ERROR_CODES.md`; clients should key behavior on `code`, not `message`.
- Resource boundaries: direct and broadcast text limits use UTF-8 encoded byte length after JSON decoding; custom payloads are bounded by the incoming WebSocket frame limit.

## Lifecycle state

- Server state lives under `INTER_AGENT_DATA_DIR` or `~/.inter-agent` by default.
- The token file, server identity metadata, PID metadata, and reserved shutdown-control metadata are per-user local files with restrictive permissions.
- Server identity metadata is written atomically and includes host, port, PID, state schema version, and startup timestamp.
- Startup refuses to replace live metadata for the same port and removes stale metadata for dead server processes when safe.
- Authenticated shutdown stops accepting new connections, closes active sessions, and removes server lifecycle metadata during normal shutdown.

## Capability exchange

- `hello.capabilities` is a required JSON object where clients may declare known or extension capability keys.
- Unknown client capability keys are tolerated and may be ignored; client declarations do not enable unimplemented features.
- `welcome.capabilities` advertises server-supported baseline capabilities: `core.version` is `0.1`, `channels` is `false`, and `rate_limit` is `false`.
- Future channel routing and policy negotiation ideas remain in `IDEAS.md` until promoted into the plan.

## Evolution touchpoints

- Middleware/router hook points reserved for future channel/pub-sub and rate-limit policies.
