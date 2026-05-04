# Threat Model (MVP)

## In scope

- Single user, single machine.
- Localhost-only server.
- Shared bearer token auth.
- Basic server identity metadata verification by clients.

## Out of scope

- Protection against malicious code already running as the same OS user.
- Cross-machine trust and PKI.
- Multi-tenant permission isolation.
