# Changelog

This project uses SemVer-style package versions. While the package is pre-1.0, maintainers may introduce breaking protocol or command changes in minor versions. Release preparation updates `pyproject.toml` and this changelog together. Entries describe durable user-facing behavior, not development session history.

## 0.1.0

- Provides a localhost WebSocket bus with authenticated `hello` / `welcome` handshakes.
- Supports direct, broadcast, custom, ping/pong, list, bye, and authenticated shutdown operations.
- Provides Pi adapter commands for connect, send, broadcast, list, status, and shutdown.
- Enforces canonical protocol errors, capability baseline reporting, target resolution, lifecycle metadata, resource limits, and local token/identity safeguards.
- Includes package entry points, conformance tests, release build validation, and protocol schemas/examples.
