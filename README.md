# inter-agent

**TLDR:** This system allows multiple coding harness sessions to talk directly to each other, even across harnesses (e.g. Claude Code to Pi)!

`inter-agent` is a localhost message bus for AI coding-agent sessions. It lets sessions in supported coding harnesses send direct messages, share occasional announcements, and coordinate through one small WebSocket protocol.

Supported user-facing integrations:

| Integration | Entry point | Best for |
| --- | --- | --- |
| Core CLI | `src/inter_agent/core/` | Scripting, testing, and building new adapters |
| Claude Code | `integrations/claude-code/` | Claude Code slash commands, Monitor notifications, and message lookup |
| Pi | `integrations/pi/` | Pi slash commands and LLM-callable tools |

Short-term active work lives in [`PLAN.md`](PLAN.md). Accepted prospective direction lives in [`ROADMAP.md`](ROADMAP.md), and exploratory ideas live in [`IDEAS.md`](IDEAS.md). The supported integration list above includes only integrations that have been implemented.

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

## Quick start from a checkout

The preferred local setup is to clone this repository once, prepare its Python runtime with `uv`, then install the host plugins from that checkout. This keeps the runtime source easy to inspect and update while preserving the shared default bus state.

`uv` is preferred because it uses the repository lockfile and matches the project quality gate.

```bash
git clone https://github.com/arcanemachine/inter-agent.git /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
```

Install the Pi extension from the checkout:

```bash
pi install /path/to/inter-agent/integrations/pi
```

Install the Claude Code plugin from the checkout marketplace metadata:

```bash
claude plugin marketplace add /path/to/inter-agent
claude plugin install inter-agent --config project_path=/path/to/inter-agent
```

Then connect from each host with a unique routing name:

```text
/inter-agent connect pi-one
/inter-agent connect claude-one
```

Either host listener can auto-start the local server. You can also start it manually from the checkout:

```bash
cd /path/to/inter-agent
uv run inter-agent-server
```

Check the bus from the repository wrapper:

```bash
./inter-agent status
./inter-agent list
```

Pi and Claude Code sessions can use separate extension installs and still talk to each other as long as their helpers use the same endpoint and state settings. The defaults already share `127.0.0.1:16837` and the platform inter-agent state directory.

## Installation alternatives

The Python runtime provides the server and helper commands used by host extensions. Host extensions may use a prepared checkout, a managed venv, or helper commands on `PATH`; these are runtime sources only and do not change the shared default bus endpoint or state directory.

### Preferred: checkout with uv

Use `uv` when working from this repository:

```bash
git clone https://github.com/arcanemachine/inter-agent.git /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
uv run inter-agent-status
```

### Without uv: standard Python venv

`uv` is not required by the protocol or server. A standard Python virtual environment can run the core package as long as dependencies and console scripts are installed:

```bash
git clone https://github.com/arcanemachine/inter-agent.git /path/to/inter-agent
cd /path/to/inter-agent
python -m venv .venv
. .venv/bin/activate
python -m pip install .
inter-agent-status
```

On Windows, activate the venv with the platform shell's normal activation command, for example:

```powershell
.venv\Scripts\Activate.ps1
```

### From a built package

A wheel or source distribution can also be installed into any compatible Python environment:

```bash
python -m pip install inter_agent-*.whl
inter-agent-status
```

Host extension helper discovery must be able to find the installed helper commands, either through a configured checkout/runtime path or `PATH`.

## Use from Pi

Install the bundled Pi package from a prepared checkout:

```bash
pi install /path/to/inter-agent/integrations/pi
```

Alternatively, install from the repository URL:

```bash
pi install https://github.com/arcanemachine/inter-agent
```

The Pi extension resolves helper commands from an override, a configured checkout, a Pi-managed venv, or `PATH`. If you use a checkout runtime, set `interAgent.projectPath` in Pi settings to that checkout and prepare the Python environment there. `uv sync --locked` is preferred; a standard `.venv` with `python -m pip install .` can also provide the helper commands. If no runtime is found, Pi shows a short setup-needed message; see [`integrations/pi/README.md#runtime-setup`](integrations/pi/README.md#runtime-setup).

Common Pi commands:

```text
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent rename my-agent-2
/inter-agent broadcast "build is green for everyone"
```

> TIP: You can also just tell Pi to talk to other agents directly, or send broadcasts.

Use direct `send` for normal coordination. Use `broadcast` only when the message is intended for all connected sessions.

See [`integrations/pi/README.md`](integrations/pi/README.md) for setup, configuration, commands, tools, and troubleshooting.

## Use from Claude Code

Install the Claude Code plugin persistently from a prepared checkout:

```bash
claude plugin marketplace add /path/to/inter-agent
claude plugin install inter-agent --config project_path=/path/to/inter-agent
```

Alternatively, use the repository URL as the marketplace source:

```bash
claude plugin marketplace add https://github.com/arcanemachine/inter-agent
claude plugin install inter-agent
```

For development, load the plugin directly instead:

```bash
claude --plugin-dir ./integrations/claude-code
```

The plugin includes a small runtime wrapper. It can use a configured local checkout, a Claude-managed venv, or `inter-agent-claude` on `PATH`.

For a local checkout runtime, prepare the checkout first. `uv` is preferred:

```bash
cd /path/to/inter-agent
uv sync --locked
claude plugin install inter-agent --config project_path=/path/to/inter-agent
```

Without `uv`, install the package into a standard venv in the checkout before pointing Claude Code at it:

```bash
cd /path/to/inter-agent
python -m venv .venv
. .venv/bin/activate
python -m pip install .
claude plugin install inter-agent --config project_path=/path/to/inter-agent
```

For a managed runtime, run `/inter-agent bootstrap` in Claude Code. The skill asks for approval before creating `~/.claude/data/inter-agent/venv` and installing the Python runtime. The managed venv is only a runtime source; it does not change the shared default bus endpoint or state directory.

Common Claude Code commands:

```text
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent rename my-agent-2
/inter-agent messages <msg_id>
/inter-agent broadcast "build is green for everyone"
```

> TIP: You can also just tell Claude to talk to other agents directly, or send broadcasts.

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

Config file discovery uses `INTER_AGENT_CONFIG` when set. Otherwise it uses the platform config location: `${XDG_CONFIG_HOME:-~/.config}/inter-agent/config.json` on Linux, `~/Library/Application Support/inter-agent/config.json` on macOS, and `%APPDATA%\\inter-agent\\config.json` on Windows when available.

State files, including the shared token and server lifecycle metadata, use `INTER_AGENT_DATA_DIR`, then `dataDir` from config, then the platform state location: `${XDG_STATE_HOME:-~/.local/state}/inter-agent` on Linux, `~/Library/Application Support/inter-agent` on macOS, and `%LOCALAPPDATA%\\inter-agent` on Windows when available, otherwise `%APPDATA%\\inter-agent`.

If the configured endpoint is unavailable and exactly one live server is found in the configured data directory, client commands use that discovered server. If multiple live servers are found, status output lists them so the endpoint can be set explicitly.

## Cross-harness interoperability

Runtime source and bus state are separate. Claude Code can use a configured checkout, a Claude-managed venv, or `PATH` helpers while Pi uses a configured checkout, a Pi-managed venv, or `PATH` helpers. Those sessions still share the same bus when the endpoint and state settings match.

For normal local use, leave `host`, `port`, and `dataDir` unset in both integrations. Claude Code and Pi then use the shared default bus at `127.0.0.1:16837` with the platform inter-agent state directory. If you intentionally want separate buses, set a different `port` and/or `dataDir` for one integration.

A quick interoperability check is to connect one Claude Code session and one Pi session, run `/inter-agent list` in either host, then send a direct message in each direction.

## Build a host adapter

New host adapters should treat the Python core as the protocol and lifecycle layer, not as Pi- or Claude-specific behavior. Start with the typed core helpers documented in [`ARCHITECTURE.md#adapter-author-contract`](ARCHITECTURE.md#adapter-author-contract) for endpoint resolution, listener connections, send/broadcast/list/status, shutdown, and operator commands.

Adapters may provide host-native commands, notifications, managed runtime lookup, output formatting, and continuation caches. Do not redefine protocol semantics, bypass auth or identity checks, depend on private server internals, or default to host-specific bus state that prevents cross-harness communication.

## Troubleshooting

### Pi reports that inter-agent setup is needed

Pi extension setup problems appear as a short notification pointing to the Pi runtime setup docs, for example:

```text
[inter-agent] setup needed. See integrations/pi/README.md#runtime-setup
```

If you configured `interAgent.projectPath`, Pi fails fast when helpers are missing from that checkout. Recreate the checkout venv and test the helper directly:

```bash
cd /path/to/inter-agent
uv sync --locked
.venv/bin/inter-agent-pi status --json
```

If you did not configure a checkout, use the managed Pi runtime instructions in [`integrations/pi/README.md#runtime-setup`](integrations/pi/README.md#runtime-setup).

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
├── integrations/opencode/          # Prospective OpenCode design notes; not an implementation
├── spec/                           # AsyncAPI contract, schemas, examples, and error codes
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
| [`spec/error-codes.md`](spec/error-codes.md) | Protocol developers | Canonical protocol error codes |
| [`AGENTS.md`](AGENTS.md) | Coding agents | Repository workflow and conventions |
| [`PLAN.md`](PLAN.md) | Contributors | Current short-term active work |
| [`ROADMAP.md`](ROADMAP.md) | Contributors | Accepted medium- and long-term direction, including prospective integrations |
| [`IDEAS.md`](IDEAS.md) | Contributors | Exploratory or unaccepted follow-up ideas |

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

### Versioning and release notes

The Python package version in `pyproject.toml` is the core release version. Related Pi package metadata, Claude Code plugin metadata, and the root Claude marketplace metadata use the same version for releases that ship from this repository. During unreleased pre-release development, the version may remain unchanged while changes accumulate locally.

Release notes and the maintainer update checklist live in [`CHANGELOG.md`](CHANGELOG.md). Changelog entries should describe stable behavior changes, not session history.

Build and validate release artifacts:

```bash
uv build
uv run python scripts/validate-release-build.py
```

## License

MIT
