# Changelog

This file records release-oriented changes for `inter-agent` packages and host integrations.

## Versioning policy

The Python package version in `pyproject.toml` is the source of truth for core release artifacts. During unreleased pre-release development, the version may remain unchanged while changes accumulate locally. Before publishing a release artifact for users, choose the release version and update all package and marketplace metadata that ships that release:

- `pyproject.toml` for the Python package;
- root `package.json` and `integrations/pi/package.json` for Pi package metadata;
- `.claude-plugin/marketplace.json` and `integrations/claude-code/.claude-plugin/plugin.json` for Claude Code marketplace and plugin metadata;
- this changelog with stable, release-oriented notes.

The protocol capability `core.version` is a protocol compatibility value, not the package release version.

## 0.1.0

- Initial package version for the inter-agent localhost message bus, core protocol helpers, and supported host integrations.
- Provides the localhost WebSocket server, bearer-token authentication, identity verification, routing, status, list, shutdown, and kick operations.
- Ships Pi and Claude Code integrations with host-specific command UX, listener lifecycle handling, and bounded incoming-message notifications.
- Supports Claude Code marketplace installation, Claude managed-runtime bootstrap, Pi root and nested package installs, and separate runtime sources that share the default bus state.
- Manual server starts are persistent by default, while Pi and Claude Code auto-started servers use an explicit 300-second idle timeout.
