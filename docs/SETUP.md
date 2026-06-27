# Setup and configuration

This guide covers setup choices beyond the short path in the root README.

## Concepts

`inter-agent` has two parts:

1. A Python runtime that provides the local WebSocket server and helper commands.
2. Host integrations, such as the Pi extension and Claude Code plugin, that call those helpers.

After each session is connected, agents can send messages to each other through their host integration; users do not need to manually relay every message.

Runtime source is separate from bus configuration. A checkout runtime, managed venv, or `PATH` install can all join the same bus when they use the same endpoint and secret.

## Recommended checkout runtime

Use a checkout when you want explicit local control or are developing this project:

```bash
git clone https://github.com/arcanemachine/inter-agent.git /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
uv run inter-agent-status
```

`uv` is preferred because it uses the repository lockfile and matches the project quality gate.

### Without uv

A standard Python virtual environment also works:

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

A wheel or source distribution can be installed into any compatible Python environment:

```bash
python -m pip install inter_agent-*.whl
inter-agent-status
```

Host integrations must be able to find the installed helper commands, either through a configured checkout/runtime path or `PATH`.

## Pi setup

Install the bundled Pi package from a prepared checkout:

```bash
pi install /path/to/inter-agent/integrations/pi
```

Then set the checkout path in `.pi/settings.json` for the current workspace or `~/.pi/agent/settings.json` globally:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent"
  }
}
```

Alternatively, install from the repository URL:

```bash
pi install https://github.com/arcanemachine/inter-agent
```

The Pi extension resolves helpers in this order:

1. `INTER_AGENT_PI_HELPER`, as an exact path to `inter-agent-pi`.
2. `interAgent.projectPath` from Pi settings, using `<projectPath>/.venv/bin`.
3. Legacy checkout fallback at `~/.local/share/inter-agent`, only when helper scripts already exist there.
4. Pi-managed runtime at `~/.pi/agent/inter-agent/venv`.
5. `inter-agent-pi`, `inter-agent-connect`, and `inter-agent-server` on `PATH`.

If no runtime is found, Pi reports setup needed and points to `integrations/pi/README.md#runtime-setup` from the repository root.

For a Pi-managed runtime without a checkout:

```bash
python3 -m venv ~/.pi/agent/inter-agent/venv
~/.pi/agent/inter-agent/venv/bin/python -m pip install --upgrade \
  https://github.com/arcanemachine/inter-agent/archive/refs/heads/main.zip
~/.pi/agent/inter-agent/venv/bin/inter-agent-pi status --json
```

If Pi was already running and still reports setup needed, run `/reload` or restart Pi. The GitHub `main` archive is a pre-release install source until stable package releases are available.

See [`integrations/pi/README.md`](../integrations/pi/README.md) for Pi commands, tools, and troubleshooting.

## Claude Code setup

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

For development, load the plugin directly from a checkout:

```bash
claude --plugin-dir ./integrations/claude-code
```

The plugin calls its bundled wrapper, which resolves the runtime helper in this order:

1. `INTER_AGENT_CLAUDE_HELPER`, as an exact executable path override.
2. Claude plugin `project_path` config, using `<project_path>/.venv/bin/inter-agent-claude`.
3. Claude-managed venv helper at `~/.claude/data/inter-agent/venv/bin/inter-agent-claude`.
4. `inter-agent-claude` on `PATH`.

For a managed runtime, run `/inter-agent bootstrap` from Claude Code. The skill asks for approval before creating `~/.claude/data/inter-agent/venv` and installing the Python runtime. The managed venv is only a runtime source; it still uses the shared default bus endpoint and secret discovery.

See [`integrations/claude-code/README.md`](../integrations/claude-code/README.md) for Claude Code commands, receive behavior, and troubleshooting.

## Server lifecycle

Either Pi or Claude Code listeners can auto-start the local server. Auto-started servers use a 300-second idle timeout and shut down after that period with no connected sessions.

Manual server starts run until explicit shutdown unless you pass an idle timeout:

```bash
cd /path/to/inter-agent
uv run inter-agent-server
uv run inter-agent-server --idle-timeout 300
```

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

## Endpoint and secret setup

By default, inter-agent uses `127.0.0.1:16837`.

Endpoint resolution order:

1. explicit `--host` / `--port` options where available
2. `INTER_AGENT_HOST` / `INTER_AGENT_PORT`
3. the inter-agent config file
4. built-in defaults

Shared-secret resolution order:

1. `INTER_AGENT_SECRET`
2. top-level config key `secret`
3. generated fallback token file in the inter-agent data directory

### Default same-user setup

If the server and clients share the same local inter-agent state directory, leave the secret unset. The generated fallback token works automatically.

### Shared secret for separate harnesses or containers

When harnesses cannot share the fallback state directory, set the same high-entropy secret everywhere before starting the server or clients:

```bash
export INTER_AGENT_SECRET='<high-entropy-shared-secret>'
```

If the default endpoint is not reachable from every harness, set host and port too:

```bash
export INTER_AGENT_HOST=127.0.0.1
export INTER_AGENT_PORT=16838
export INTER_AGENT_SECRET='<high-entropy-shared-secret>'
```

Every server and client on that bus must use the same endpoint and secret. For containers, remember that `127.0.0.1` means “inside this container”; use a reachable host or container address when needed.

Pi can also receive these values through `interAgent.host`, `interAgent.port`, and `interAgent.secret` in Pi settings. Claude Code installed plugins can set plugin config `secret`, which the wrapper passes to helpers as `INTER_AGENT_SECRET`; use parent-process environment variables for custom host/port.

### Multiple independent buses

Use different ports and usually different secrets:

```bash
# bus A
export INTER_AGENT_PORT=16837
export INTER_AGENT_SECRET='<secret-a>'

# bus B
export INTER_AGENT_PORT=16838
export INTER_AGENT_SECRET='<secret-b>'
```

Launch each server and harness from the environment for the bus it should join.

## Config file

The config file is JSON:

```json
{
  "host": "127.0.0.1",
  "port": 16837,
  "dataDir": "/path/to/inter-agent-state",
  "secret": "high-entropy-shared-secret"
}
```

Config file discovery uses `INTER_AGENT_CONFIG` when set. Otherwise it uses the platform config location:

- Linux: `${XDG_CONFIG_HOME:-~/.config}/inter-agent/config.json`
- macOS: `~/Library/Application Support/inter-agent/config.json`
- Windows: `%APPDATA%\\inter-agent\\config.json` when available

State files, including the fallback generated secret, use `INTER_AGENT_DATA_DIR`, then `dataDir` from config, then the platform state location:

- Linux: `${XDG_STATE_HOME:-~/.local/state}/inter-agent`
- macOS: `~/Library/Application Support/inter-agent`
- Windows: `%LOCALAPPDATA%\\inter-agent` when available, otherwise `%APPDATA%\\inter-agent`

## Troubleshooting

### Setup needed

If Pi or Claude Code says setup is needed, the host integration could not find the Python runtime helper. Prepare a checkout with `uv sync --locked`, configure the host to use that checkout, or use the host-specific managed runtime instructions.

### Auth failed

`AUTH_FAILED` means the client and server are not using the same secret. Check `INTER_AGENT_SECRET`, config `secret`, plugin/Pi settings, and whether the server was started before the environment changed. Restart the server and reconnect clients after changing a secret.

### Wrong port or unavailable server

Client commands probe the configured endpoint directly. If the endpoint is unavailable, set `INTER_AGENT_HOST` and `INTER_AGENT_PORT` or update the config file to match the server. In containers, make sure the chosen host is reachable from the client container.

### Name conflicts

Routing names must be unique among connected sessions. Choose a different name or run `./inter-agent list` to inspect connected sessions. Operators can use `./inter-agent kick <name>` to clear a stale registered session.

## Security summary

The shared secret is used for HMAC-SHA-256 challenge-response during connection startup. The raw secret is not sent over the WebSocket. Message payloads are still plaintext over `ws://`.

See [`SECURITY.md`](../SECURITY.md) for the full local single-user security model, controls, and secret rotation steps.
