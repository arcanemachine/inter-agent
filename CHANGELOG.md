# Changelog

This project uses SemVer-style package versions. While the package is pre-1.0, maintainers may introduce breaking protocol or command changes in minor versions. Release preparation updates `pyproject.toml` and this changelog together. Entries describe durable user-facing behavior, not development session history.

## 0.1.0

- Provides a localhost WebSocket bus with authenticated `hello` / `welcome` handshakes.
- Supports direct, broadcast, custom, ping/pong, list, bye, and authenticated shutdown operations.
- Provides Pi adapter commands for connect, send, broadcast, list, status, and shutdown.
- Provides Claude Code adapter with Monitor-backed listener, session state, and CLI commands.
- Provides Pi extension (`integrations/pi/`) with spawn-based listener, commands, and LLM-callable tools.
- Provides Claude Code plugin (`integrations/claude-code/`) with Monitor-backed listener, reaction policy, and CLI commands.
- Server auto-starts when the Claude Code listener connects and the server is not running.
- Server shuts down automatically after 300 seconds of idle time (no connected sessions), configurable via `--idle-timeout`.
- Rejects duplicate session IDs and duplicate routing names on concurrent connections.
- Enforces resource limits for connections, text payload size, custom types, and custom payloads.
- Performs server identity verification (host, port, PID liveness, nonce, process start marker) before sending the shared token.
- Enforces canonical protocol errors, capability baseline reporting, target resolution, lifecycle metadata, and local token/identity safeguards.
- Handles permanent errors, graceful SIGINT/SIGTERM shutdown, and stale listener cleanup.
- Includes package entry points, conformance tests, release build validation, and protocol schemas/examples.
