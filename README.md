# inter-agent

`inter-agent` lets local AI coding sessions communicate through one authenticated message bus. Pi, Claude Code, and OpenCode can discover connected agents, send direct messages, broadcast, and use named channels.

This repository is the **ecosystem source checkout**. It records a compatible combination of the core runtime and host integrations as Git submodules. It is not a Python package, npm package, or runtime dependency.

## Choose a component

| Component | Use it for | Installation |
| --- | --- | --- |
| [inter-agent-core](https://github.com/arcanemachine/inter-agent-core) | The host-neutral Python runtime, server, protocol, TLS, routing, channels, shared state, and generic CLI. | [Core README](https://github.com/arcanemachine/inter-agent-core/blob/main/README.md) |
| [inter-agent-pi](https://github.com/arcanemachine/inter-agent-pi) | Pi commands, model tools, notifications, mailbox delivery, and the Pi helper. | [Pi README](https://github.com/arcanemachine/inter-agent-pi/blob/main/README.md) |
| [inter-agent-claude-code](https://github.com/arcanemachine/inter-agent-claude-code) | The Claude Code plugin, Monitor listener, wrappers, and Claude helper. | [Claude Code README](https://github.com/arcanemachine/inter-agent-claude-code/blob/main/README.md) |
| [inter-agent-opencode](https://github.com/arcanemachine/inter-agent-opencode) | OpenCode TUI commands, server tools, direct protocol access, and automatic inbound delivery. | [OpenCode README](https://github.com/arcanemachine/inter-agent-opencode/blob/main/README.md) |
| Complete checkout | Coordinated development, review, and cross-adapter acceptance. | Clone this repository recursively. |

Each child is independently versioned and installable. The submodules record the exact source revisions tested together.

## How it works

One `inter-agent-core` server owns authentication, routing, channels, and connection state. Pi, Claude Code, and OpenCode connect through their own host adapters and surface incoming messages through their native interfaces. They share the same endpoint, state directory, secret discovery, and TLS configuration.

The default endpoint is `127.0.0.1:16837`. Loopback connections default to plaintext WebSockets; non-loopback connections default to TLS unless explicitly disabled. Clients authenticate with an HMAC-SHA-256 challenge using a shared secret.

## First cross-adapter message

Install the [Pi](https://github.com/arcanemachine/inter-agent-pi/blob/main/README.md), [Claude Code](https://github.com/arcanemachine/inter-agent-claude-code/blob/main/README.md), or [OpenCode](https://github.com/arcanemachine/inter-agent-opencode/blob/main/README.md) component, then connect each host to the same bus:

```text
# In Pi
/inter-agent connect pi-agent

# In Claude Code
/inter-agent connect claude-agent
/inter-agent send pi-agent hello from Claude Code

# In OpenCode
# Select "Inter-agent: Connect OpenCode session" from Ctrl+P.
# Enter: opencode-agent --auto-connect
```

The receiving host shows its native notification or delivery view. For separate machines, configure a shared reachable endpoint, secret, and TLS settings; the default loopback endpoint is local to one machine.

## Complete source checkout

Clone the tested child set:

```bash
git clone --recurse-submodules https://github.com/arcanemachine/inter-agent.git
cd inter-agent
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

Use the child README for the component you are changing. Commit child changes in that repository, then update the corresponding Gitlink here.

Run coordinated validation from the checkout with:

```bash
scripts/run-checks.sh
```

The script builds and clean-installs the indexed child revisions, then exercises direct messages, broadcasts, channels, kick behavior, isolated buses, and TLS without publishing or using the user's existing bus.

## Compatibility and security

[`COMPATIBILITY.md`](COMPATIBILITY.md) records the released compatible versions and the tested submodule set.

The default trust boundary is one trusted operating-system user on one machine. Shared-secret authentication prevents unauthenticated clients from joining, and TLS protects network transport, but neither protects against hostile code running as the same user with access to local state or secrets. Do not commit or share secrets, private keys, certificates, or state. See the [`inter-agent-core` security model](https://github.com/arcanemachine/inter-agent-core/blob/main/SECURITY.md).

## Documentation and support

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — repository ownership and component boundaries
- [`COMPATIBILITY.md`](COMPATIBILITY.md) — released versions and compatibility
- [`inter-agent-core/spec/`](https://github.com/arcanemachine/inter-agent-core/tree/main/spec) — protocol definition, schemas, examples, and error codes
- [Core issues](https://github.com/arcanemachine/inter-agent-core/issues)
- [Pi issues](https://github.com/arcanemachine/inter-agent-pi/issues)
- [Claude Code issues](https://github.com/arcanemachine/inter-agent-claude-code/issues)
- [OpenCode issues](https://github.com/arcanemachine/inter-agent-opencode/issues)
- [Ecosystem issues](https://github.com/arcanemachine/inter-agent/issues)

## License

MIT. See [`LICENSE.md`](LICENSE.md).
