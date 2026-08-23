# Compatibility

This public source checkout coordinates tested child source versions and records the exact Git revisions tested together. It does not publish a package or runtime of its own; this source-only compatibility record makes no publication, tag, or release claim.

| Component | Tested source version | Compatibility |
| --- | --- | --- |
| `inter-agent-core` | `0.3.0` | Provides the `inter_agent` runtime and protocol capability `core.version` `0.1`. |
| `inter-agent-pi` | npm extension `0.3.2`; Python helper `0.3.1` | Requires `inter-agent-core==0.3.0`; control uses released public Pi lifecycle/submission APIs present in Pi `0.81.1`, with runtime semantics additionally verified against Pi `0.84.2`. |
| `inter-agent-claude-code` | plugin `0.2.1`; Python helper `0.3.0` | Requires `inter-agent-core==0.3.0`; the plugin metadata remains `0.2.1` while the helper uses the Core `0.3.0` source and the current Pi compatibility set. |
| `inter-agent-opencode` | standalone OpenCode extension | Provides separate TUI and server plugin targets, direct TypeScript/Bun protocol access, loopback plaintext or WSS, and automatic inbound delivery. |

The protocol's AsyncAPI document is version `0.1.0`. Git submodules record the exact tested child revisions without copying those revisions into this document.

Each component versions independently. Run the child checks and ecosystem acceptance when updating a Gitlink, and update this record when the supported version set changes.
