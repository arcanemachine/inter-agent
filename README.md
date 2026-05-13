# inter-agent

`inter-agent` is a lightweight localhost messaging bus for AI coding sessions.

It provides a framework-agnostic protocol for direct and broadcast messaging between running sessions, plus host adapters that expose that protocol in specific tooling. The Pi adapter is the primary user-facing workflow.

## Elevator pitch

Have you ever wanted your AI coding agents to talk to each other?

- **Inter-agent messaging** — Send direct messages from one agent to another by name.
- **Broadcast to all** — Notify every connected session at once.
- **Framework-agnostic** — Any agent that speaks JSON over WebSocket can join, no matter what tool it runs in.
- **Localhost only** — Nothing leaves your machine. Shared-token auth, local identity checks, and no remote exposure.
- **Minimal ceremony** — Start the server, connect a session, send messages. No databases, no cloud services, no configuration files.

## Core behavior

- WebSocket protocol over localhost.
- First-class direct (`A -> B`) and broadcast messaging.
- Stable routing names, unique-prefix target resolution, sorted session lists, and optional display-only labels for introspection.
- Extension envelope via `op: "custom"` with pass-through routing.
- Basic shared-token authentication, local identity checks, and documented protocol error codes.

## Layout

- `src/inter_agent/core/` universal protocol server/client bits
- `src/inter_agent/adapters/pi/` Pi-specific UX adapter
- `src/inter_agent/adapters/claude/` Claude Code-specific UX adapter
- `spec/` AsyncAPI contract, standalone operation schemas in `spec/schemas/`, and canonical examples in `spec/examples/`
- `tests/` conformance and validation tests
- `docs/` supporting notes

## Quickstart: Claude Code workflow

1. Start the server:
   ```bash
   uv run inter-agent-server
   ```

2. Load the plugin in a Claude Code session:
   ```bash
   claude --plugin-dir ./claude-plugin
   ```

3. Connect and start messaging:
   ```
   /inter-agent connect my-agent
   /inter-agent send other-agent "run tests"
   /inter-agent broadcast "build is green"
   /inter-agent list
   /inter-agent status
   /inter-agent disconnect
   /inter-agent shutdown
   ```

For details on command output and failure behavior, see `src/inter_agent/adapters/claude/README.md`.

## Quickstart: Pi workflow

1. Install the inter-agent server and start it:
   ```bash
   git clone https://github.com/arcanemachine/inter-agent ~/.local/share/inter-agent
   cd ~/.local/share/inter-agent
   uv sync
   uv run inter-agent-server
   ```

   The server runs in the foreground. To run it in the background, use one of these approaches:

   - **`nohup`** (simplest, survives terminal close):
     ```bash
     nohup uv run inter-agent-server > /tmp/inter-agent.log 2>&1 &
     ```

   - **`tmux`** or **`screen`** (good for debugging):
     ```bash
     tmux new-session -d -s inter-agent "uv run inter-agent-server"
     ```

   To stop the server:

   - **Graceful shutdown** (preferred if the server is reachable):
     ```bash
     uv run inter-agent-pi shutdown
     ```

   - **Kill the process** (if graceful shutdown fails):
     ```bash
     pkill -f inter-agent-server
     ```

2. Install the Pi extension:
   ```bash
   pi install https://github.com/arcanemachine/pi-inter-agent
   ```

3. Inside Pi, connect to the bus and start messaging:
   ```
   /inter-agent-connect my-agent --label "My Agent"
   /inter-agent-send other-agent "run tests"
   /inter-agent-broadcast "build is green"
   /inter-agent-list
   /inter-agent-status
   /inter-agent-disconnect
   /inter-agent-shutdown
   ```

For details on command output, status fields, and failure behavior, see `src/inter_agent/adapters/pi/README.md`.

### Core protocol commands (for debugging)

If you prefer to use the raw Python CLI directly:

- `uv run inter-agent-connect <name>`
- `uv run inter-agent-send <to> <text>`
- `uv run inter-agent-send --text "broadcast text"`
- `uv run inter-agent-list`
- `uv run inter-agent-shutdown`

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
| `INTER_AGENT_CONNECTION_MAX` | 64 | active authenticated connections |
| `INTER_AGENT_CUSTOM_TYPE_MAX` | 128 bytes | `custom.custom_type` |
| `INTER_AGENT_CUSTOM_PAYLOAD_MAX` | 1 MiB | JSON-encoded `custom.payload` |

Custom extension payloads are routed as pass-through JSON after `custom_type` and payload-size validation.

## Troubleshooting auth failures

`AUTH_FAILED` means the client token did not match the running server. Stop the server, remove the token file from `INTER_AGENT_DATA_DIR/token` or `~/.inter-agent/token`, start the server again, and reconnect clients. See `SECURITY.md` for the token rotation procedure.

## Release validation

Build and inspect local release artifacts without publishing:

- `uv build`
- `uv run python scripts/validate-release-build.py`

Publishing package artifacts and selecting package-index settings are maintainer-owned release actions.

## Versioning and changelog

The package version lives in `pyproject.toml`. Release preparation updates that version and `CHANGELOG.md` together. The changelog uses release-oriented behavior summaries rather than development session notes.

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
- `CHANGELOG.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ERROR_CODES.md`
- `AGENTS.md`
