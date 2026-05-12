# Security Model

## Baseline assumptions

1. Single user, single machine.
2. Localhost-only deployment.
3. Threat model is defensive against accidental/mild local misuse, not malicious same-user code execution.

## Security controls

1. Server binds to localhost (`127.0.0.1`).
2. Shared bearer token is required in `hello`; invalid tokens receive canonical `AUTH_FAILED` errors.
3. Token/state files use restrictive permissions (`0600`), state directory (`0700`). Server-owned lifecycle files include the token, server identity metadata, PID metadata, and reserved shutdown-control metadata.
4. Clients verify server identity before sending the shared token. Verification checks host, port, PID liveness, matching identity/PID metadata nonce, and a process start marker when the platform exposes one. Server identity metadata is written atomically, includes a startup timestamp, state schema version, instance nonce, and process start marker, and is removed by the server during normal shutdown. On platforms without a process start marker, verification falls back to PID liveness plus matching local metadata.
5. Shutdown uses the same localhost shared-token authentication as other control operations and requires a control-role connection.
6. Core validates operation shapes and rejects unauthenticated/invalid requests with documented protocol error codes.
7. Resource limits bound incoming WebSocket frames and direct/broadcast text. Text limits are measured as UTF-8 encoded bytes after JSON decoding: `INTER_AGENT_DIRECT_MAX` defaults to 2 MiB, `INTER_AGENT_BROADCAST_MAX` defaults to 512 KiB, and `INTER_AGENT_FRAME_MAX` defaults to 16 MiB.

Custom extension payloads are pass-through JSON. They are bounded by the WebSocket frame limit, not by a separate application-level custom payload cap.

## Explicit non-goals

1. Protection from hostile processes running as the same OS user.
2. Cross-machine trust, PKI lifecycle, or mTLS.
3. Multi-tenant isolation and enterprise RBAC.

## Extension areas

- Stronger identity attestation.
- Transport hardening for remote scenarios.
- Policy middleware (for example, rate limits or channel permissions).
