# Security Baseline

1. Bind the server to `127.0.0.1` by default.
2. Require the shared bearer token in every `hello` handshake.
3. Store the plaintext local token with mode `0600` under `INTER_AGENT_DATA_DIR` or `~/.inter-agent`.
4. Keep the state directory mode `0700` and server lifecycle metadata files mode `0600` on POSIX-compatible filesystems.
5. Verify server identity before clients send the token: host, port, PID liveness, matching identity/PID metadata nonce, and process start marker when available.
6. Reject unauthenticated operations with canonical `AUTH_FAILED` errors.
7. Bound active connections, incoming frames, direct/broadcast text, custom types, and custom payload sizes.
8. Require authenticated control-role shutdown for server stop requests.
