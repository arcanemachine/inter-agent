# inter-agent

`inter-agent` lets local AI coding sessions communicate through one authenticated message bus. A Pi session, a Claude Code session, or another client can discover connected agents, send direct messages, broadcast, and exchange messages through named channels.

This repository is the **ecosystem source checkout**. It pins a tested combination of the core runtime and host integrations, then verifies that they build, install, and work together. It is not itself a Python package, npm package, or runtime dependency.

## Projects

| Project | What it provides |
| --- | --- |
| [`core/`](core/) | The host-neutral Python runtime: WebSocket server, protocol, authentication, TLS, routing, channels, lifecycle controls, shared configuration, and generic command-line clients. |
| [`extensions/pi/`](extensions/pi/) | The Pi extension: `/inter-agent` commands, agent-callable tools, inbound notifications, mailbox UI, and a Python helper built on the core runtime. |
| [`extensions/claude-code/`](extensions/claude-code/) | The Claude Code plugin: skill-driven commands, Monitor-based inbound delivery, bundled wrappers, and a Python helper built on the core runtime. |

Each project is independently versioned and installable. This repository records the exact source revisions tested together as Git submodules.

## What it does

The ecosystem supports:

- named agent sessions;
- direct agent-to-agent messages;
- broadcasts to connected agents;
- named channel subscription and publishing;
- session, server, and channel inspection;
- administrative kick and shutdown operations;
- shared endpoint and state discovery across host integrations; and
- plaintext loopback or configured TLS transport.

The core protocol is host-neutral. Pi and Claude Code adapt their own command, tool, and notification interfaces to the core's public APIs rather than implementing separate message buses.

## How it works

```text
Pi session                                                Claude Code session
    │                                                               │
    ▼                                                               ▼
Pi extension ───────┐                              ┌──── Claude Code plugin
                    │                              │
                    ▼                              ▼
              Pi helper ───► inter-agent core ◄─── Claude helper
                                  │
                                  ▼
                         local WebSocket bus
```

One core server owns authentication, routing, channels, and connection state. Host listeners connect as named agents and surface incoming messages through their native UI. Command clients use the same endpoint, secret, and TLS configuration as those listeners.

The default endpoint is `127.0.0.1:16837`. Clients authenticate with an HMAC-SHA-256 challenge using a shared secret. Loopback connections default to plaintext WebSockets; non-loopback connections default to TLS unless TLS is explicitly disabled.

## Install and use

Install the component for the host you use:

- **Pi:** follow [`extensions/pi/README.md`](extensions/pi/README.md).
- **Claude Code:** follow [`extensions/claude-code/README.md`](extensions/claude-code/README.md).
- **Core server or generic CLI:** follow [`core/README.md`](core/README.md).

You do not need this superproject after the required components are installed. It is primarily for developing, reviewing, and testing a coordinated source set.

## Work on the ecosystem

### Prerequisites

The coordinated checks currently target:

- Git with submodule support;
- Python 3.12.8;
- `uv` 0.10.4; and
- Node.js 24.16.0 with npm for the Pi extension.

Clone the complete source set:

```bash
git clone --recurse-submodules https://github.com/arcanemachine/inter-agent.git
cd inter-agent
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

Prepare each child's development dependencies:

```bash
(cd core && uv sync --locked)
(cd extensions/pi && uv sync --locked && npm ci)
(cd extensions/claude-code && uv sync --locked)
```

Then run the coordinated gate from a clean checkout:

```bash
scripts/run-checks.sh
```

The gate is offline-first. Initial dependency setup must populate the local `uv` and npm caches; the gate fails rather than fetching an unavailable dependency from a registry.

### What the gate verifies

The root gate:

1. verifies the canonical submodule URLs and exact pinned revisions;
2. validates the superproject's public source and artifact boundaries;
3. creates an isolated recursive checkout;
4. runs every child project's package-local checks;
5. builds and installs the candidate artifacts in a clean environment;
6. exercises Pi and Claude Code interoperability for direct messages, broadcasts, channels, kick behavior, isolated buses, and TLS; and
7. confirms that the checkout remains clean.

Temporary state is removed after a successful run. Failed acceptance state is retained under `/tmp` and its path is printed for diagnosis.

## Source revisions and releases

The submodule Gitlinks identify the exact candidate source set tested by this repository. [`COMPATIBILITY.md`](COMPATIBILITY.md) records the compatible semantic versions, but it does not claim that a candidate has been published or tagged.

When a child revision changes, update its Gitlink and run both the child's package gate and the root coordinated gate. Update `COMPATIBILITY.md` when the supported version set changes.

## Security model

The default design assumes one trusted operating-system user on one machine. Shared-secret authentication prevents unauthenticated clients from joining the bus, and TLS can protect network transport, but neither protects against hostile code running as the same user with access to the bus state or secret.

Do not commit or share bus secrets, private keys, certificates, or local state. See [`core/SECURITY.md`](core/SECURITY.md) for the complete security model.

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — repository ownership and component boundaries
- [`COMPATIBILITY.md`](COMPATIBILITY.md) — coordinated candidate versions
- [`core/spec/`](core/spec/) — AsyncAPI protocol definition, schemas, examples, and error codes
- Child READMEs — component-specific installation, commands, and development instructions

## License

MIT. See [`LICENSE.md`](LICENSE.md).
