# Threat Model

## In scope

- Single user, single machine.
- Localhost-only server by default; optional non-loopback binding with transport encryption.
- Shared bearer token authentication over WebSockets.
- Optional TLS transport encryption for `wss://` connections.
- Server proof verification by clients before sending authentication responses.
- Defensive controls against accidental or mild local misuse: restrictive state-file permissions, resource limits, duplicate-session rejection, and authenticated shutdown.

## Out of scope

- Protection against malicious code already running as the same OS user.
- Cross-machine trust, PKI lifecycle, mTLS, or remote transport hardening beyond transport encryption.
- Multi-tenant permission isolation or enterprise RBAC.
- Protection from a local process that can read or modify the user's inter-agent state directory contents.
- Treating TLS as sufficient for safe remote or multi-user operation.
