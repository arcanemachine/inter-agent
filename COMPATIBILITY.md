# Compatibility

This public source checkout coordinates tested child source versions and records the exact Git revisions tested together. It does not publish a package or runtime of its own; this source-only compatibility record makes no publication, tag, or release claim.

| Component | Tested source version | Compatibility |
| --- | --- | --- |
| `inter-agent-core` | `0.3.0` | Provides the `inter_agent` runtime and protocol capability `core.version` `0.1`. |
| `inter-agent-pi` | npm extension `0.3.2`; Python helper `0.3.1` | Requires `inter-agent-core==0.3.0`; control uses released public Pi lifecycle/submission APIs present in Pi `0.81.1`, with runtime semantics additionally verified against Pi `0.84.2`. |
| `pi-session-manager` | `0.1.1` (`44461a7`) | Optional hosting composition verified with `inter-agent-pi` commit `01b5bf2`, Pi `0.84.2`, and tmux `3.5a`; it remains independent of routing, readiness, allowlists, and semantic control. |
| `inter-agent-claude-code` | plugin `0.2.1`; Python helper `0.3.0` | Requires `inter-agent-core==0.3.0`; the plugin metadata remains `0.2.1` while the helper uses the Core `0.3.0` source and the current Pi compatibility set. |
| `inter-agent-opencode` | package `0.2.1` | Provides separate TUI and server plugin targets, direct TypeScript/Bun protocol access, loopback plaintext or WSS, Home-screen connection, compact automatic delivery, and durable inbox tools. |

The protocol's AsyncAPI document is version `0.1.0`. Git submodules record the exact tested child revisions without copying those revisions into this document.

Each component versions independently. Run the child checks and ecosystem acceptance when updating a Gitlink, and update this record when the supported version set changes.

The verified optional composition uses a dedicated Session Manager tmux server
for ordinary visible Pi workers. Readiness and lifecycle semantics remain in
inter-agent Pi; the canonical setup and ownership guide is the
[`inter-agent-pi` Session Manager guide](https://github.com/arcanemachine/inter-agent-pi/blob/main/SESSION_MANAGER.md).
The official isolated ecosystem gate remains environment-limited when its
cached build dependencies are unavailable; the composition result does not
change that limitation.
