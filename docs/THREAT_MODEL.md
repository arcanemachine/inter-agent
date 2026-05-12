# Threat Model

## In scope

- Single user, single machine.
- Localhost-only server.
- Shared bearer token authentication over localhost WebSockets.
- Local server identity metadata verification by clients before sending the token.
- Defensive controls against accidental or mild local misuse: restrictive state-file permissions, resource limits, duplicate-session rejection, and authenticated shutdown.

## Out of scope

- Protection against malicious code already running as the same OS user.
- Cross-machine trust, PKI, TLS termination, or mTLS.
- Multi-tenant permission isolation or enterprise RBAC.
- Protection from a local process that can read or modify the user's `INTER_AGENT_DATA_DIR` contents.
