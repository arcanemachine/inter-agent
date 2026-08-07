# Compatibility

This source checkout coordinates the split-generation candidate set below. It does not claim that any component has been published to a registry or released as a tag.

| Component | Candidate version | Compatibility |
| --- | --- | --- |
| `inter-agent-core` | `0.2.0` | Provides the `inter_agent` runtime and protocol capability `core.version` `0.1`. |
| `inter-agent-pi` | npm extension `0.2.1`; Python helper `0.2.0` | Requires `inter-agent-core==0.2.0`; its npm extension and Python helper use the core public APIs. |
| `inter-agent-claude-code` | `0.2.0` | Requires `inter-agent-core==0.2.0`; its plugin and Python helper use the core public APIs. |

The protocol's AsyncAPI document is version `0.1.0`. Git submodules record the exact tested candidate revisions without copying those revisions into this document.

Each component versions independently after this split generation. Any later Gitlink update must pass the component's package gate and ecosystem acceptance, and this record must be updated if the supported semantic version set changes.
