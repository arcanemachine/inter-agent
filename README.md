# inter-agent

`inter-agent` lets AI coding-agent sessions talk to each other on the same machine.

Connect each session once, then the agents can send messages, ask each other questions, coordinate work, and report results through their host integration. The main use case is coordination between multiple sessions in the same harness, such as two Claude Code sessions or two Pi sessions working in parallel. Because every host uses the same small protocol, different harnesses can also talk to each other when useful.

## Why use it?

- **Let agents coordinate directly** — connect them once, then they can message each other while they work.
- **Coordinate parallel work** — ask another session to inspect code, run checks, review a change, or take a related task.
- **Use routing names** — connect each session as a name like `frontend`, `reviewer`, or `pi-one`, then send direct messages to that name.
- **Share occasional announcements** — broadcast only when every connected session needs the message.
- **Keep it local and scriptable** — the bus is a small localhost WebSocket server with CLI helpers and host integrations.

Peer messages are collaboration inputs. They do not override system, developer, user, tool, permission, or security rules in the receiving harness.

## Supported integrations

| Integration | Entry point | Best for |
| --- | --- | --- |
| Claude Code | `integrations/claude-code/` | Claude Code slash commands, Monitor notifications, and message lookup |
| Pi | `integrations/pi/` | Pi slash commands and LLM-callable tools |
| Core CLI | `src/inter_agent/core/` | Scripting, testing, and building new adapters |

## How it works

```text
AI session ─┐
AI session ─┼─ host integration ─ inter-agent server ─ host integration ─ AI session
AI session ─┘              localhost WebSocket bus
```

1. Start or auto-start one local inter-agent server.
2. Each agent session connects with a unique routing name.
3. Agents use their host integration to send direct messages, broadcasts, list peers, and check status.
4. Connections authenticate with shared-secret HMAC challenge-response.

For normal same-user local use, no secret setup is needed. The server and clients use a generated fallback secret from the shared inter-agent state directory. For separate harnesses, containers, or isolated filesystems, export the same secret everywhere.

## Quick start from a checkout

Clone once, prepare the Python runtime, install the host integration you want, then connect from two or more sessions. Those sessions can be in the same harness, such as two Pi sessions, two Claude Code sessions, or a mix.

```bash
git clone https://github.com/arcanemachine/inter-agent.git /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
```

### Pi

Install the Pi extension:

```bash
pi install /path/to/inter-agent/integrations/pi
```

Tell Pi where the checkout runtime is. Add this to `.pi/settings.json` for the current workspace or `~/.pi/agent/settings.json` globally:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent"
  }
}
```

Then connect inside each Pi session with a unique name:

```text
/inter-agent connect pi-one
/inter-agent connect pi-two
```

### Claude Code

Install the Claude Code plugin and point it at the same checkout:

```bash
claude plugin marketplace add /path/to/inter-agent
claude plugin install inter-agent --config project_path=/path/to/inter-agent
```

Then connect inside each Claude Code session with a unique name:

```text
/inter-agent connect claude-one
/inter-agent connect claude-two
```

Either listener can auto-start the local server. You can also start it manually:

```bash
cd /path/to/inter-agent
uv run inter-agent-server
```

Check the bus from the repository wrapper:

```bash
./inter-agent status
./inter-agent list
```

## Setup modes

### Default local setup

Use this when the server and harnesses share the same user account and inter-agent state directory. No port or secret configuration is needed:

```text
endpoint: 127.0.0.1:16837
secret: generated fallback token
```

### Shared secret and custom port

Use this for separate harnesses, containers, isolated filesystems, or multiple independent buses. Export the same values anywhere that starts the server or runs clients/helpers:

```bash
export INTER_AGENT_HOST=127.0.0.1
export INTER_AGENT_PORT=16838
export INTER_AGENT_SECRET='<high-entropy-shared-secret>'
```

Then start the server and harnesses normally. Pi, Claude Code, and the core CLI all read these environment variables. If a harness is launched by another parent process, make sure that process has the environment too.

For containers, `127.0.0.1` means “inside this container”; use a reachable host or container address when needed.

For two independent buses, use different ports and usually different secrets.

More setup detail, including config files, managed runtimes, and troubleshooting, lives in [`docs/SETUP.md`](docs/SETUP.md).

## Daily use

The normal flow is:

1. Connect each agent session with a unique name.
2. Tell the agents what you want coordinated.
3. Let them send messages to each other through inter-agent.

For example, after connecting `builder` and `reviewer`, you can tell one agent: “Ask reviewer to inspect the test changes.” The agent can use inter-agent to send the message, and replies arrive in the active session as host notifications.

Common slash commands in Pi and Claude Code are still available when you want manual control:

```text
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent list
/inter-agent status
/inter-agent rename my-agent-2
/inter-agent broadcast "build is green for everyone"
/inter-agent disconnect
```

Use direct `send` for normal coordination. Use `broadcast` only when the message is intended for all connected sessions.

Core CLI equivalents are available through the repository wrapper:

```bash
./inter-agent start
./inter-agent status
./inter-agent list
./inter-agent pi send other-agent "hello"
./inter-agent claude send other-agent "hello"
./inter-agent stop
```

## Troubleshooting quick hits

- **Setup needed** — the host integration cannot find the Python runtime. Prepare the checkout with `uv sync --locked` and configure the host to use that checkout.
- **`AUTH_FAILED`** — the client and server are using different secrets. Set the same `INTER_AGENT_SECRET` everywhere, restart the server, then reconnect clients.
- **Wrong port or unavailable server** — check `INTER_AGENT_HOST` and `INTER_AGENT_PORT` for the server and every harness.
- **Name taken** — routing names must be unique. Choose another name or run `./inter-agent list`.

See [`docs/SETUP.md`](docs/SETUP.md) for the detailed setup guide.

## Security in brief

`inter-agent` is designed for one user on one machine. The server binds to localhost by default and authenticates connections with shared-secret HMAC-SHA-256. The raw secret is not sent over the socket.

Messages are still plaintext over `ws://`. Localhost limits accidental exposure, but it does not protect against hostile same-user code or provide encrypted remote transport.

See [`SECURITY.md`](SECURITY.md) for the full security model and secret rotation procedure.

## Project docs

| Document | Contents |
| --- | --- |
| [`docs/SETUP.md`](docs/SETUP.md) | Detailed setup, config, custom ports, shared secrets, containers, troubleshooting |
| [`integrations/pi/README.md`](integrations/pi/README.md) | Pi extension setup, commands, tools |
| [`integrations/claude-code/README.md`](integrations/claude-code/README.md) | Claude Code plugin setup and commands |
| [`src/inter_agent/adapters/claude/README.md`](src/inter_agent/adapters/claude/README.md) | Claude Code adapter CLI details |
| [`src/inter_agent/adapters/pi/README.md`](src/inter_agent/adapters/pi/README.md) | Pi adapter CLI details |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Layers, protocol model, routing, lifecycle, adapter boundaries |
| [`SECURITY.md`](SECURITY.md) | Security model, controls, secret rotation |
| [`spec/`](spec/) | Protocol contract, schemas, examples, and error codes |
| [`spec/error-codes.md`](spec/error-codes.md) | Canonical protocol error codes |
| [`PLAN.md`](PLAN.md) | Current short-term active work |
| [`ROADMAP.md`](ROADMAP.md) | Accepted medium- and long-term direction |
| [`docs/IDEAS.md`](docs/IDEAS.md) | Exploratory or unaccepted ideas |
| [`AGENTS.md`](AGENTS.md) | Coding-agent workflow for this repository |

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
└── docs/                           # Setup, design notes, and supporting references
```

New host adapters should treat the Python core as the protocol and lifecycle layer. See [`ARCHITECTURE.md#adapter-author-contract`](ARCHITECTURE.md#adapter-author-contract).

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

Build and validate release artifacts:

```bash
uv build
uv run python scripts/validate-release-build.py
```

The Python package version in `pyproject.toml` is the core release version. Related Pi package metadata, Claude Code plugin metadata, and root Claude marketplace metadata use the same version for releases that ship from this repository. Release notes and the maintainer update checklist live in [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT
