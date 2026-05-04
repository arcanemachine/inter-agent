# Security Baseline (MVP)

1. Bind server to `127.0.0.1`.
2. Use a shared bearer token file with mode `0600`.
3. Keep state directory mode `0700`.
4. Verify basic server identity (pid/meta/host/port) before sending token.
5. Reject unauthenticated operations.
