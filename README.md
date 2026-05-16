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

2. **Adapters** (`src/inter_agent/adapters/`) — command-line interfaces that wrap the core protocol for each host tool. Adapters provide commands like `connect`, `send`, `broadcast`, and `list`.

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

The server can be started manually with `uv run inter-agent-server`, or it will auto-start when the Claude Code listener connects and the server is not already running (the Pi extension requires the server to be started manually). After 300 seconds with no connected sessions, the server shuts down automatically. Use `--idle-timeout <seconds>` to change the idle timeout, or `--idle-timeout 0` to disable it.

## Setup the server

```bash
cd src/inter_agent
uv run inter-agent-server
```

## Setup your extension

Pick the extension for the tool you use:

### Pi

Start the server (required — the Pi extension does not auto-start it):

```bash
cd /path/to/inter-agent
uv run inter-agent-server
```

Then install the Pi extension:

```bash
pi install https://github.com/arcanemachine/pi-inter-agent
```

In Pi:

```
/inter-agent-connect my-agent
/inter-agent-send other-agent "run tests"
/inter-agent-broadcast "build is green"
```

See [`integrations/pi/README.md`](integrations/pi/README.md) for full setup, configuration, and commands.

### Claude Code

Load the plugin in a Claude Code session. The listener auto-starts the server if it is not running:

```bash
claude --plugin-dir ./integrations/claude-code
```

In Claude Code:

```
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent broadcast "build is green"
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

The package version lives in `pyproject.toml`.

Build and validate release artifacts:

```bash
uv build
uv run python scripts/validate-release-build.py
```

## License

MIT
