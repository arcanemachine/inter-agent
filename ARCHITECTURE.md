# Ecosystem architecture

The ecosystem repository coordinates source revisions; it does not ship runtime code.

## Ownership

- [`core/`](core/) owns the protocol, authentication, TLS, routing, lifecycle, limits, and shared endpoint/state resolution.
- [`extensions/pi/`](extensions/pi/) owns Pi commands, tools, listener lifecycle, mailbox presentation, and the Pi helper.
- [`extensions/claude-code/`](extensions/claude-code/) owns the Claude Code plugin, skill, Monitor lifecycle, wrappers, and Claude helper.
- This root owns Git submodule coordination and the ecosystem compatibility record.

The extension helpers use the core's public APIs. They do not copy or fork core protocol behavior. The core does not include host plugins or adapters. The superproject is not required at runtime after a component is installed.

## Source coordination

Gitlinks identify the exact coordinated source set. `COMPATIBILITY.md` records the compatible semantic versions; the Gitlinks, not README prose, identify source revisions. Update the compatibility record when the supported version set changes.

For protocol, security, and host details, read the owning child documentation rather than this overview.
