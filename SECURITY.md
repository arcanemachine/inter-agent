# Security Model (MVP)

## Baseline assumptions

1. Single user, single machine.
2. Localhost-only deployment.
3. Threat model is defensive against accidental/mild local misuse, not malicious same-user code execution.

## Controls in MVP

1. Server binds to localhost (`127.0.0.1`).
2. Shared bearer token is required in `hello`.
3. Token/state files use restrictive permissions (`0600`), state directory (`0700`).
4. Clients perform basic server identity verification before sending token (`pid/meta/host/port`).
5. Core validates operation shapes and rejects unauthenticated/invalid requests.

## Explicit non-goals (MVP)

1. Protection from hostile processes running as the same OS user.
2. Cross-machine trust, PKI lifecycle, or mTLS.
3. Multi-tenant isolation and enterprise RBAC.

## Future hardening path

- Optional stronger identity attestation.
- Optional transport hardening for remote scenarios.
- Optional policy middleware (rate limits, channel permissions).
