# inter-agent

Permissive, universal-friendly agent-to-agent messaging bus with a Python core and Pi adapter.

## MVP goals

- Core protocol over localhost WebSocket.
- First-class direct (`A -> B`) and broadcast messaging.
- Extension path via `op: "custom"` envelopes.
- Unknown custom message types pass through the core bus.
- Security baseline: localhost bind, shared token, file-permission hygiene, basic server identity check.

## Non-goals (MVP)

- Full pub-sub/channels.
- Active rate limiting.
- Durable replay queue.
- Enterprise auth/TLS hardening.

## Layout

- `core/` universal protocol server/client bits
- `adapters/pi/` Pi-specific UX adapter
- `spec/` AsyncAPI + schemas + examples
- `tests/` conformance and validation tests
- `docs/` supporting notes

## Development checks

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy core adapters tests`

## Additional docs

- `ARCHITECTURE.md`
- `SECURITY.md`
- `AGENTS.md` (agent workflow)
