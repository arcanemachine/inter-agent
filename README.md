# inter-agent

`inter-agent` is the source-checkout superproject for the local inter-agent message bus ecosystem. It coordinates a tested set of independent repositories; it is not a Python package, an npm package, or a runtime dependency.

- [`core/`](core/) is the host-neutral server, protocol, authentication, TLS, routing, and shared endpoint/state runtime.
- [`extensions/pi/`](extensions/pi/) is the Pi extension and its Python helper.
- [`extensions/claude-code/`](extensions/claude-code/) is the Claude Code plugin and its Python helper.

Each component is independently versioned and installable. This repository's Git submodules record the exact candidate source set tested together. Candidate source is not a registry release.

## Source checkout

Clone every component together:

```bash
git clone --recurse-submodules https://github.com/arcanemachine/inter-agent.git
cd inter-agent
```

If you already made an ordinary clone:

```bash
git submodule update --init --recursive
```

Run the coordinated source-checkout checks after following each child's documented development setup:

```bash
scripts/run-checks.sh
```

The root check is offline-first and does not publish, tag, push, install globally, or change a user bus. It expects initialized submodules and uses isolated state for interoperability checks.

## Installing components

Use the component that matches your host:

- [core installation and commands](core/README.md)
- [Pi installation and commands](extensions/pi/README.md)
- [Claude Code plugin installation and commands](extensions/claude-code/README.md)

For independent checkout, issue tracker, changelog, and security-report links, use the canonical repositories: [core](https://github.com/arcanemachine/inter-agent-core), [Pi](https://github.com/arcanemachine/inter-agent-pi), and [Claude Code](https://github.com/arcanemachine/inter-agent-claude-code).

## Interoperability and security

Independently installed hosts use the core's shared endpoint and state rules, so Pi and Claude Code can use one local bus. The default design is one user on one machine. A shared-secret challenge authenticates clients; TLS protects configured transport but does not make hostile same-user code safe. Do not commit or share bus secrets, certificates, keys, or local state.

See [ARCHITECTURE.md](ARCHITECTURE.md) for ownership boundaries and [COMPATIBILITY.md](COMPATIBILITY.md) for the tested candidate set.

## License

MIT. See [LICENSE.md](LICENSE.md).
