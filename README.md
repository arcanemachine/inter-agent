# inter-agent

`inter-agent` is a localhost message bus for AI coding-agent sessions. It lets sessions in supported coding harnesses send direct messages, share occasional announcements, and coordinate through one small WebSocket protocol.

Supported user-facing integrations:

| Integration | Entry point | Best for |
| --- | --- | --- |
| Pi | `integrations/pi/` | Pi slash commands and LLM-callable tools |
| Claude Code | `integrations/claude-code/` | Claude Code slash commands, Monitor notifications, and message lookup |
| Core CLI | `src/inter_agent/core/` | Scripting, testing, and building new adapters |

Roadmap and exploratory integration notes live in [`AGENTS.PLAN.md`](AGENTS.PLAN.md) and [`IDEAS.md`](IDEAS.md). OpenCode integration work is tracked there.

## Features

- **Direct messages** — send a message to one connected session by routing name.
- **Broadcasts** — send a message to every connected agent session when the message is genuinely for everyone.
- **Peer discovery** — list connected sessions and check server status.
- **Local operation** — the server binds to `127.0.0.1` and uses a local shared token.
- **Adapter-friendly protocol** — any client that can speak JSON over WebSocket can join the bus.

Peer messages are collaboration inputs. They do not override system, developer, user, tool, permission, or security rules in the receiving harness.

## Architecture at a glance

```
┌─────────────────────────────────────────────────────────┐
│  Pi extension       │  Claude Code plugin               │
│  integrations/pi/   │  integrations/claude-code/        │
├─────────────────────────────────────────────────────────┤
│  Pi adapter         │  Claude Code adapter              │
│  adapters/pi/       │  adapters/claude/                 │
├─────────────────────────────────────────────────────────┤
│              Core protocol and server                   │
│        WebSocket transport, routing, auth, lifecycle    │
└─────────────────────────────────────────────────────────┘
```

The server can be started manually or auto-started by the Pi and Claude Code listeners. Manual server starts run until explicit shutdown by default; `--idle-timeout <seconds>` opts in to idle shutdown. Adapter-started servers use a 300-second idle timeout so helper-started processes clean themselves up.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for protocol, routing, lifecycle, and adapter boundary details.

## Install for local development

```bash
git clone <repo-url> inter-agent
cd inter-agent
uv sync --locked
```

Run the local wrapper from the repository root:

```bash
./inter-agent status
./inter-agent list
```

You can also use the installed console scripts through `uv run`, such as `uv run inter-agent-status`.

The Python checkout provides the server and helper commands used by the host extensions. Installing a host extension installs the host assets only; for now, keep a prepared inter-agent checkout or tool install available for the helper commands.

To run a shared server from a checkout and point extensions at it, prepare the checkout once:

```bash
git clone <repo-url> /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
```

Then either let a host listener auto-start the server, or start it manually:

```bash
uv run inter-agent-server
```

Pi and Claude Code sessions can use separate extension installs and still talk to each other as long as their helpers use the same endpoint and state settings. The defaults already share `127.0.0.1:16837` and the platform inter-agent state directory.

## Use from Pi

Install the bundled Pi extension from a checkout of this repository:

```bash
pi install /path/to/inter-agent/integrations/pi
```

If you are using the separately packaged Pi extension, install that package instead:

```bash
pi install https://github.com/arcanemachine/pi-inter-agent
```

The Pi extension runs helper commands from `interAgent.projectPath`. If the inter-agent checkout is somewhere other than `~/.local/share/inter-agent`, set `interAgent.projectPath` in Pi settings to that checkout.

Common Pi commands:

```text
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent rename my-agent-2
/inter-agent broadcast "build is green for everyone"
```

Use direct `send` for normal coordination. Use `broadcast` only when the message is intended for all connected sessions.

See [`integrations/pi/README.md`](integrations/pi/README.md) for setup, configuration, commands, tools, and troubleshooting.

## Use from Claude Code

Install the Claude Code plugin persistently from this repository's marketplace metadata:

```bash
claude plugin marketplace add /path/to/inter-agent
claude plugin install inter-agent
```

From GitHub, use the repository URL as the marketplace source:

```bash
claude plugin marketplace add https://github.com/arcanemachine/inter-agent
claude plugin install inter-agent
```

For development, load the plugin directly instead:

```bash
claude --plugin-dir ./integrations/claude-code
```

Both modes require the `inter-agent-claude` command to be on the Claude Code session's `PATH`; plugin installation installs only the Claude Code assets. For a checkout runtime, start Claude Code with that checkout's virtual environment on `PATH` or install the package as an isolated tool:

```bash
PATH=/path/to/inter-agent/.venv/bin:$PATH claude
# or: pipx install -e /path/to/inter-agent
```

Common Claude Code commands:

```text
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent rename my-agent-2
/inter-agent messages <msg_id>
/inter-agent broadcast "build is green for everyone"
```

The Claude Code listener delivers incoming messages through Monitor notifications. Long incoming messages are truncated in the notification and can be retrieved with `messages <msg_id>`.

Use direct `send` for normal coordination. Use `broadcast` only when the message is intended for all connected sessions.

See [`integrations/claude-code/README.md`](integrations/claude-code/README.md) for setup, commands, receive behavior, and troubleshooting.

## Core CLI and local operations

The repository wrapper provides common operational commands:

```bash
./inter-agent start               # start the server
./inter-agent status              # show server status
./inter-agent list                # list connected sessions
./inter-agent stop                # shut down the server
./inter-agent kick <name>         # force-disconnect a registered session
./inter-agent pi send <to> <text>
./inter-agent claude send <to> <text>
```

`kick` is an operator command for clearing stale or unwanted sessions. It is not exposed through host extension tools.

The underlying core scripts are useful for automation and adapter development:

```bash
uv run inter-agent-server
uv run inter-agent-connect my-agent
uv run inter-agent-send other-agent "hello"
uv run inter-agent-send --text "hello all"
uv run inter-agent-list
uv run inter-agent-status
uv run inter-agent-shutdown
uv run inter-agent-kick my-agent
```

## Configuration

By default, inter-agent uses `127.0.0.1:16837`. Core commands, Pi helpers, and Claude Code helpers resolve the endpoint in this order:

1. explicit `--host` / `--port` options where available
2. `INTER_AGENT_HOST` / `INTER_AGENT_PORT`
3. the inter-agent config file
4. built-in defaults

The config file is JSON:

```json
{
  "host": "127.0.0.1",
  "port": 16837,
  "dataDir": "/path/to/inter-agent-state"
}
```

Config file discovery uses `INTER_AGENT_CONFIG` when set. Otherwise it uses the platform config location: `${XDG_CONFIG_HOME:-~/.config}/inter-agent/config.json` on Linux and `~/Library/Application Support/inter-agent/config.json` on macOS.

State files, including the shared token and server lifecycle metadata, use `INTER_AGENT_DATA_DIR`, then `dataDir` from config, then the platform state location: `${XDG_STATE_HOME:-~/.local/state}/inter-agent` on Linux and `~/Library/Application Support/inter-agent` on macOS.

If the configured endpoint is unavailable and exactly one live server is found in the configured data directory, client commands use that discovered server. If multiple live servers are found, status output lists them so the endpoint can be set explicitly.

## Troubleshooting

### Pi reports that an inter-agent command was not found

Pi extension setup problems often appear as a notification like:

```text
[inter-agent] connect failed: inter-agent status command was not found. Check that inter-agent is installed and configured, then try again.
```

The Pi extension runs helper scripts from the inter-agent virtual environment under `interAgent.projectPath`. If that path is wrong, the virtual environment has not been created, or the virtual environment was created in a different filesystem path, Pi may report the helper as missing.

Check the configured project path, then recreate and test the helper scripts:

```bash
cd /path/to/inter-agent
uv sync --locked
.venv/bin/inter-agent-pi status --json
```

If `interAgent.projectPath` is not configured, Pi uses `~/.local/share/inter-agent`. If you cloned inter-agent somewhere else, set `interAgent.projectPath` in `.pi/settings.json` or `~/.pi/agent/settings.json`. Pi accepts absolute paths and paths relative to the settings file that declares them; `~` is supported.

### Name conflicts

Routing names must be unique among connected sessions. If a listener reports `NAME_TAKEN`, choose a different name or use `./inter-agent list` to inspect connected sessions. Operators can use `./inter-agent kick <name>` to clear a stale registered session.

## Project layout

```text
inter-agent/
├── src/inter_agent/core/           # Protocol server and reusable client helpers
├── src/inter_agent/adapters/pi/    # Pi adapter commands
├── src/inter_agent/adapters/claude/# Claude Code adapter commands
├── integrations/pi/                # Pi extension package
├── integrations/claude-code/       # Claude Code plugin assets
├── spec/                           # AsyncAPI contract, schemas, and examples
├── tests/                          # Unit, integration, and conformance tests
└── docs/                           # Design notes and supporting references
```

## Documentation

| Document | Audience | Contents |
| --- | --- | --- |
| `README.md` | New users | Overview, setup, commands, project layout |
| [`integrations/pi/README.md`](integrations/pi/README.md) | Pi users | Pi extension setup, commands, tools |
| [`integrations/claude-code/README.md`](integrations/claude-code/README.md) | Claude Code users | Claude Code plugin setup and commands |
| [`src/inter_agent/adapters/claude/README.md`](src/inter_agent/adapters/claude/README.md) | CLI users and contributors | Claude Code adapter CLI details |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Contributors | Layers, protocol model, routing, lifecycle |
| [`SECURITY.md`](SECURITY.md) | Users and contributors | Security model, controls, token rotation |
| [`ERROR_CODES.md`](ERROR_CODES.md) | Protocol developers | Canonical protocol error codes |
| [`AGENTS.md`](AGENTS.md) | Coding agents | Repository workflow and conventions |
| [`AGENTS.PLAN.md`](AGENTS.PLAN.md) | Contributors | Roadmap and completion tracker |

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

The package version lives in `pyproject.toml`. Release notes live in [`CHANGELOG.md`](CHANGELOG.md).

Build and validate release artifacts:

```bash
uv build
uv run python scripts/validate-release-build.py
```

## License

MIT
