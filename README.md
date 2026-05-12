# inter-agent

`inter-agent` is a lightweight localhost messaging bus for AI coding sessions.

It provides a framework-agnostic protocol for direct and broadcast messaging between running sessions, plus host adapters that expose that protocol in specific tooling. The Pi adapter is the primary user-facing workflow.

## Core behavior

- WebSocket protocol over localhost.
- First-class direct (`A -> B`) and broadcast messaging.
- Stable routing names, unique-prefix target resolution, sorted session lists, and optional display-only labels for introspection.
- Extension envelope via `op: "custom"` with pass-through routing.
- Basic shared-token authentication, local identity checks, and documented protocol error codes.

## Layout

- `src/inter_agent/core/` universal protocol server/client bits
- `src/inter_agent/adapters/pi/` Pi-specific UX adapter
- `spec/` AsyncAPI contract, standalone operation schemas in `spec/schemas/`, and canonical examples in `spec/examples/`
- `tests/` conformance and validation tests
- `docs/` supporting notes

## Quickstart: Pi workflow

1. Create the environment and install dependencies:
   - `uv sync`

2. Start the localhost bus server:
   - `uv run inter-agent-server`

3. Connect Pi sessions in separate terminals:
   - `uv run inter-agent-pi connect agent-a --label "Agent A"`
   - `uv run inter-agent-pi connect agent-b --label "Agent B"`

4. Send messages through the Pi adapter:
   - `uv run inter-agent-pi send agent-b "run tests"`
   - `uv run inter-agent-pi broadcast "build is green"`

5. Inspect or stop the bus:
   - `uv run inter-agent-pi list`
   - `uv run inter-agent-pi status`
   - `uv run inter-agent-pi shutdown`

Pi-specific command output, status fields, shutdown behavior, and failure behavior are documented in `src/inter_agent/adapters/pi/README.md`.

## Core protocol commands

Core command entry points are available for direct protocol use and adapter/debug workflows. Pi users should prefer `inter-agent-pi` for host-facing commands.

- `uv run inter-agent-connect <name>`
- `uv run inter-agent-send <to> <text>`
- `uv run inter-agent-send --text "broadcast text"`
- `uv run inter-agent-list`
- `uv run inter-agent-shutdown`

## Development helper

`start.sh` is a local development/demo helper that delegates to the package entry points. It is not required for the installed command workflow. For a bounded smoke check, run `./start.sh status --json`.

## Resource limits

Text limits are measured as UTF-8 encoded bytes after JSON decoding. Text exactly at the configured byte limit is accepted; text one byte over the limit is rejected with `TEXT_TOO_LARGE`.

| Environment variable | Default | Applies to |
| --- | ---: | --- |
| `INTER_AGENT_DIRECT_MAX` | 2 MiB | `send.text` |
| `INTER_AGENT_BROADCAST_MAX` | 512 KiB | `broadcast.text` |
| `INTER_AGENT_FRAME_MAX` | 16 MiB | incoming WebSocket message frames |

Custom extension payloads are routed as pass-through JSON and are bounded by the WebSocket frame limit.

## Development checks

Run the full local quality gate:

- `./run-checks.sh`

The gate runs `uv sync --locked` before the required checks. For targeted debugging, run individual checks directly:

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`

## Additional docs

- `src/inter_agent/adapters/pi/README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ERROR_CODES.md`
- `AGENTS.md`
