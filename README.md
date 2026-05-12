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
- `spec/` AsyncAPI contract, standalone operation schemas in `spec/schemas/`, and canonical examples in `spec/examples/`
- `tests/` conformance and validation tests
- `docs/` supporting notes

## Quickstart

1. Create environment and install dependencies:
   - `uv sync`

2. Start server:
   - `uv run inter-agent-server`

3. Connect two sessions (in separate terminals):
   - `uv run inter-agent-pi connect agent-a`
   - `uv run inter-agent-pi connect agent-b`

4. Send and broadcast:
   - `uv run inter-agent-pi send agent-b "run tests"`
   - `uv run inter-agent-pi broadcast "build is green"`

5. List sessions / status:
   - `uv run inter-agent-pi list`
   - `uv run inter-agent-pi status`

Core command entry points are also available for direct protocol use:

- `uv run inter-agent-connect <name>`
- `uv run inter-agent-send <to> <text>`
- `uv run inter-agent-send --text "broadcast text"`
- `uv run inter-agent-list`

`start.sh` remains available as a local development/demo helper that delegates to the package entry points.

## Development checks

Run the full local quality gate:

- `./run-checks.sh`

The gate runs `uv sync --locked` before the required checks. For targeted debugging, run individual checks directly:

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`

## Additional docs

- `ARCHITECTURE.md`
- `SECURITY.md`
- `AGENTS.md`
