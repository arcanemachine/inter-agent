# inter-agent

`inter-agent` is a lightweight localhost messaging bus for AI coding sessions.

It provides a framework-agnostic protocol for direct and broadcast messaging between running sessions, plus host adapters that expose that protocol in specific tooling.

## Core behavior

- WebSocket protocol over localhost.
- First-class direct (`A -> B`) and broadcast messaging.
- Extension envelope via `op: "custom"` with pass-through routing.
- Basic shared-token authentication and local identity checks.

## Layout

- `src/inter_agent/core/` universal protocol server/client bits
- `src/inter_agent/adapters/pi/` Pi-specific UX adapter
- `spec/` AsyncAPI + schemas + examples
- `tests/` conformance and validation tests
- `docs/` supporting notes

## Quickstart

1. Create environment and install dependencies:
   - `uv sync`

2. Start server:
   - `./start.sh server`

3. Connect two sessions (in separate terminals):
   - `./start.sh connect agent-a`
   - `./start.sh connect agent-b`

4. Send and broadcast:
   - `./start.sh send agent-b "run tests"`
   - `./start.sh broadcast "build is green"`

5. List sessions / status:
   - `./start.sh list`
   - `./start.sh status`

## Development checks

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`

## Additional docs

- `ARCHITECTURE.md`
- `SECURITY.md`
- `AGENTS.md`
