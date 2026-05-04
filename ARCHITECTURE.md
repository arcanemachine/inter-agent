# Architecture

`inter-agent` is a localhost WebSocket message bus for AI coding sessions.

## Layers

1. **Core protocol (`core/`)**
   - Handshake/auth (`hello` / `welcome`)
   - Presence and identity (`session_id`, `name`)
   - Routing (`send`, `broadcast`, `custom` pass-through)
   - Health (`ping` / `pong`, `bye`)
   - Introspection (`list` capability)

2. **Adapters (`adapters/`)**
   - Host-specific command UX and integration.
   - May expose only a subset of core-supported operations.

3. **Spec (`spec/`)**
   - AsyncAPI contract and JSON Schemas.
   - Example payloads for canonical behavior.

## Messaging model

- Direct message: sender targets one agent by name.
- Broadcast: sender targets all other connected agents.
- Custom: extension envelope (`op: custom`, `custom_type`, `payload`), routed by core without type-specific interpretation.

## Evolution touchpoints

- `capabilities` field in handshake for future negotiation.
- Middleware/router hook points reserved for future channel/pub-sub and rate-limit policies.
