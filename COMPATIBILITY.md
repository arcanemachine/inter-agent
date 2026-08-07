# Compatibility

This public source checkout coordinates released child versions and records the exact Git revisions tested together. It does not publish a package or runtime of its own.

| Component | Released version | Compatibility |
| --- | --- | --- |
| `inter-agent-core` | `0.2.0` | Provides the `inter_agent` runtime and protocol capability `core.version` `0.1`. |
| `inter-agent-pi` | npm extension `0.2.1`; Python helper `0.2.0` | Requires `inter-agent-core==0.2.0`; the extension and helper use the core public APIs. |
| `inter-agent-claude-code` | plugin `0.2.1`; Python helper `0.2.0` | Requires `inter-agent-core==0.2.0`; the plugin and helper use the core public APIs. |

The protocol's AsyncAPI document is version `0.1.0`. Git submodules record the exact tested child revisions without copying those revisions into this document.

Each component versions independently. Run the child checks and ecosystem acceptance when updating a Gitlink, and update this record when the supported version set changes.
