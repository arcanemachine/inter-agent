# inter-agent

A lightweight messaging bus that allows AI coding harness sessions to talk to each other.

This tool can allow your Claude Code or Pi sessions to talk to each other, or even allow communication between different harnesses (e.g. Pi <-> Claude Code).

This tool provides a platform that can be extended to work with other coding harnesses. OpenCode is the next planned host-native extension target. A Codex extension is not planned because Codex's no-fork extension system does not expose the background message delivery and control surface needed for an inter-agent extension; any future Codex work should be treated as an App Server sidecar, not a Codex extension.

## What it does

Inter-agent lets AI coding agents running in different tools on the same machine send messages to each other:

- **Direct messages** — send a message to one agent by name
- **Broadcast** — send a message to every connected agent at once
- **Localhost only by default** — nothing leaves your machine without your permission

Any agent that can speak JSON over WebSocket can join, no matter what tool it runs in.

## How it works

The project has three layers:

1. **Core protocol** (`src/inter_agent/core/`) — a WebSocket message bus that runs on your local machine. It handles connection management, routing, authentication, and lifecycle.

2. **Adapters** (`src/inter_agent/adapters/`) — command-line interfaces that wrap the core protocol for each host tool. Adapters provide commands like `connect`, `send`, `broadcast`, and `list`; use direct `send` for normal agent-to-agent communication and reserve `broadcast` for messages everyone explicitly needs.

3. **Extensions** (`integrations/`) — host-specific plugin assets (skills, monitors, manifest files) that let you use inter-agent from within the host tool itself.

```
┌─────────────────────────────────────────────────────────┐
│  Pi extension      │  Claude Code plugin                │
│  (integrations/pi/)│  (integrations/claude-code/)       │
├─────────────────────────────────────────────────────────┤
│  Pi adapter        │  Claude Code adapter               │
│  (adapters/pi/)    │  (adapters/claude/)                │
├─────────────────────────────────────────────────────────┤
│              Core protocol (core/)                      │
│         WebSocket bus, routing, auth                    │
└─────────────────────────────────────────────────────────┘
```

The server can be started manually with `uv run inter-agent-server`, or it will auto-start when the Pi or Claude Code listener connects and the server is not already running. Manual server starts run until explicit shutdown by default; pass `--idle-timeout <seconds>` to opt in to automatic shutdown after an idle period. Adapter auto-started servers use an explicit 300-second idle timeout so helper-started processes clean themselves up.

## Optional: start the server manually

```bash
cd /path/to/inter-agent
uv run inter-agent-server
```

## Setup your extension

Pick the extension for the tool you use:

### Pi

Install the Pi extension:

```bash
pi install https://github.com/arcanemachine/pi-inter-agent
```

In Pi:

```
/inter-agent-connect my-agent
/inter-agent-send other-agent "run tests"
/inter-agent-broadcast "build is green for everyone"
```

See [`integrations/pi/README.md`](integrations/pi/README.md) for full setup, configuration, commands, and troubleshooting.

### Claude Code

Load the plugin in a Claude Code session. The listener auto-starts the server if it is not running:

```bash
claude --plugin-dir ./integrations/claude-code
```

In Claude Code:

```
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent broadcast "build is green for everyone"
```

See [`src/inter_agent/adapters/claude/README.md`](src/inter_agent/adapters/claude/README.md) for full setup and commands.

### Using the core protocol directly

If you are building a new adapter or extension, you can use the core protocol commands directly:

```bash
# Start the server
uv run inter-agent-server

# Connect a session
uv run inter-agent-connect my-agent

# Send a message
uv run inter-agent-send other-agent "hello"

# Broadcast
uv run inter-agent-send --text "hello all"

# List connected sessions
uv run inter-agent-list

# Shut down the server
uv run inter-agent-shutdown
```

## Troubleshooting

### Pi: command not found during connect or status

Pi extension setup problems often appear as a harness notification like:

```text
[inter-agent] connect failed: inter-agent status command was not found. Check that inter-agent is installed and configured, then try again.
```

or:

```text
[inter-agent] status failed: inter-agent status command was not found. Check that inter-agent is installed and configured, then try again.
```

The Pi extension runs helper scripts from the inter-agent virtual environment under `interAgent.projectPath`. If that path is wrong, the virtual environment has not been created, or the virtual environment was created in a different filesystem path, Pi may report the helper as missing.

Check the configured project path, then recreate the helper scripts:

```bash
cd /path/to/inter-agent
uv sync --locked
.venv/bin/inter-agent-pi status --json
```

If `interAgent.projectPath` is not configured, Pi uses `~/.local/share/inter-agent`. If you cloned inter-agent somewhere else, set `interAgent.projectPath` in `.pi/settings.json` or `~/.pi/agent/settings.json`.

## Project layout

```
inter-agent/
├── src/inter_agent/core/           # Universal protocol server and client
├── src/inter_agent/adapters/pi/    # Pi adapter commands
├── src/inter_agent/adapters/claude/# Claude Code adapter commands
├── integrations/pi/                # Pi extension (TypeScript)
├── integrations/claude-code/       # Claude Code plugin (skills, monitors)
├── spec/                           # AsyncAPI contract and JSON schemas
├── tests/                          # Conformance and integration tests
└── docs/                           # Security notes and threat model
```

## Documentation

| Document                                                                                 | Audience            | Contents                             |
| ---------------------------------------------------------------------------------------- | ------------------- | ------------------------------------ |
| `README.md`                                                                              | New users           | Overview, setup, project layout      |
| [`integrations/pi/README.md`](integrations/pi/README.md)                                 | Pi users            | Pi extension setup, commands, tools  |
| [`src/inter_agent/adapters/claude/README.md`](src/inter_agent/adapters/claude/README.md) | Claude Code users   | Claude Code adapter commands         |
| [`ARCHITECTURE.md`](ARCHITECTURE.md)                                                     | Contributors        | Layers, messaging model, lifecycle   |
| [`AGENTS.md`](AGENTS.md)                                                                 | Contributors        | Development workflow and conventions |
| [`SECURITY.md`](SECURITY.md)                                                             | Contributors        | Security model and token rotation    |
| [`ERROR_CODES.md`](ERROR_CODES.md)                                                       | Protocol developers | Canonical error codes                |

## Development

Run the full quality gate:

```bash
./run-checks.sh
```

Individual checks:

```bash
uv run pytest
uv run ruff check .
uv run black --check .
uv run mypy src tests
```

The package version lives in `pyproject.toml`. Release notes live in `CHANGELOG.md`.

Build and validate release artifacts:

```bash
uv build
uv run python scripts/validate-release-build.py
```

## License

MIT
