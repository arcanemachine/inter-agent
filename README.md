# inter-agent

`inter-agent` lets AI coding-agent sessions talk to each other.

Connect each session once, then agents can send messages, ask each other questions, coordinate work, and report results through their host integration. The main use case is multiple sessions in the same harness, such as two Claude Code sessions or two Pi sessions. Different harnesses can also talk to each other because they use the same local bus.

## What it does

Agents can talk to each other:

- **Directly** — send a message to one connected agent by name.
- **By broadcast** — send a message to every connected agent when everyone needs it.
- **Through channels** — subscribe to named channels and publish messages to every subscriber except the publisher. Channels are an in-memory, single-server feature with no durability, ACLs, or history.

## Quick start

Clone once and prepare the Python runtime:

```bash
git clone https://github.com/arcanemachine/inter-agent.git /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
```

Install whichever host integration you want to use.

### Pi

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

Open two Pi sessions and connect each with a unique name:

```text
/inter-agent connect builder
/inter-agent connect reviewer
```

### Claude Code

```bash
claude plugin marketplace add /path/to/inter-agent
claude plugin install inter-agent --config project_path=/path/to/inter-agent
```

Open two Claude Code sessions and connect each with a unique name:

```text
/inter-agent connect builder
/inter-agent connect reviewer
```

Either integration can auto-start the local server. You can check the bus from the checkout:

```bash
./inter-agent status
./inter-agent list
```

Now tell an agent what to coordinate, for example:

```text
Ask reviewer to inspect the test changes.
```

The agent can send that message through inter-agent, and replies arrive in the host session as notifications.

## Common commands

Pi and Claude Code expose the same basic slash commands:

```text
/inter-agent connect my-agent
/inter-agent send other-agent "run tests"
/inter-agent list
/inter-agent status
/inter-agent rename my-agent-2
/inter-agent broadcast "build is green for everyone"
/inter-agent subscribe updates
/inter-agent unsubscribe updates
/inter-agent disconnect
```

Both integrations expose user-controlled channel membership as user-invoked slash commands. Nothing is subscribed automatically, and neither integration exposes subscribe or unsubscribe as LLM-callable tools. The Python Pi and Claude adapters also provide `subscribe`, `unsubscribe`, `publish`, and `channels` CLI commands; the installed Claude Code `/inter-agent` skill exposes `subscribe` and `unsubscribe` only, not `publish` or `channels`.

Use direct `send` for normal coordination. Use `broadcast` only when all connected sessions need the message.

## How it works

- One local inter-agent server routes messages between connected sessions.
- Each session connects with a unique routing name.
- Connections authenticate with a shared secret. Default local setup creates one automatically; isolated harnesses or containers can export the same secret explicitly.
- The WebSocket transport speaks `ws://` or `wss://`. Loopback hosts, including `127.0.0.1` and `localhost`, default to plaintext `ws://` unless TLS is explicitly enabled. Non-loopback hosts default to TLS/`wss://` unless TLS is explicitly disabled.

Peer messages are collaboration inputs. They do not override system, developer, user, tool, permission, or security rules in the receiving harness.

Core CLI helpers are also available:

```bash
./inter-agent start
./inter-agent status
./inter-agent list
./inter-agent channels
./inter-agent publish my-channel "hello subscribers"
./inter-agent pi send other-agent "hello"
./inter-agent claude send other-agent "hello"
./inter-agent stop
```

## Custom port, shared secret, or TLS

Default local setup needs no configuration:

```text
endpoint: 127.0.0.1:16837
secret: generated fallback token
TLS: off for loopback, on for non-loopback hosts
```

For separate harnesses, containers, isolated filesystems, or multiple independent buses, export the same values anywhere that starts the server or clients:

```bash
export INTER_AGENT_HOST=0.0.0.0
export INTER_AGENT_PORT=16838
export INTER_AGENT_SECRET='<high-entropy-shared-secret>'
```

Then start the server and harnesses normally. Pi, Claude Code, and the core CLI read these environment variables.

If a harness is launched by another parent process, make sure that process has the environment too. In containers, `127.0.0.1` means “inside this container”; use a reachable host (e.g. a LAN IP) or container address when needed.

### TLS

Core server and client commands support TLS for WebSocket transport encryption.

- Loopback/local hosts (`127.0.0.1`, `localhost`, `::1`) default to plaintext `ws://` unless TLS is explicitly enabled.
- Non-loopback hosts default to TLS `wss://` unless TLS is explicitly disabled.
- Explicitly enable or disable TLS with the `INTER_AGENT_TLS=true|false` environment variable, the `tls` config key, or command flags `--tls` / `--no-tls`.
- Provide a certificate and key with `INTER_AGENT_TLS_CERT` / `INTER_AGENT_TLS_KEY`, the `tlsCert` / `tlsKey` config keys, or `--tls-cert` / `--tls-key` flags.
- If TLS is enabled without configured certificate/key material, the server generates `tls-cert.pem` and `tls-key.pem` in the inter-agent data directory with restrictive permissions. Clients trust the generated/default certificate from the same data directory, or the certificate configured via `INTER_AGENT_TLS_CERT` / `tlsCert`.

TLS applies to transport encryption only. It does not make remote or multi-user operation fully safe, and it does not replace the shared-secret challenge-response authentication that still runs inside the WebSocket connection.

## Troubleshooting

- **Setup needed** — the host integration cannot find the Python runtime. Run `uv sync --locked` in the checkout and configure the host to use that checkout.
- **`AUTH_FAILED`** — the client and server are using different secrets. Set the same `INTER_AGENT_SECRET` everywhere, restart the server, then reconnect clients.
- **TLS certificate not found** — when TLS is enabled, start the server first so it can generate the default certificate, or configure `INTER_AGENT_TLS_CERT` / `tlsCert` with a reachable certificate path.
- **Wrong port or unavailable server** — check `INTER_AGENT_HOST` and `INTER_AGENT_PORT` for the server and every harness.
- **Name taken** — routing names must be unique. Choose another name or run `./inter-agent list`.

## More docs

- [`integrations/pi/README.md`](integrations/pi/README.md) — Pi setup, commands, tools, and configuration.
- [`integrations/claude-code/README.md`](integrations/claude-code/README.md) — Claude Code setup, commands, receive behavior, and configuration.
- [`SECURITY.md`](SECURITY.md) — security model, shared-secret auth, and secret rotation.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — protocol, routing, lifecycle, and adapter boundaries.
- [`spec/`](spec/) — protocol schemas, examples, and error codes.

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

Release notes and the maintainer update checklist live in [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT
