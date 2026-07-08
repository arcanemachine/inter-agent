# Security Model

## Baseline assumptions

- `inter-agent` is for one user on one machine.
- The server binds to localhost. The default endpoint is `127.0.0.1:16837`.
- Localhost limits accidental network exposure; it does not make the transport encrypted or protect against hostile same-user code.
- Remote access, multi-user operation, and enterprise authorization require a separate accepted threat model before implementation.

## Core controls

- **Transport encryption**

  The server and clients speak WebSocket over `ws://` or `wss://`. Loopback hosts (`127.0.0.1`, `localhost`, `::1`) default to plaintext `ws://` unless TLS is explicitly enabled. Non-loopback hosts default to TLS `wss://` unless TLS is explicitly disabled.

  TLS is configured through `INTER_AGENT_TLS`/`tls` (enable/disable), `INTER_AGENT_TLS_CERT`/`tlsCert` (certificate), and `INTER_AGENT_TLS_KEY`/`tlsKey` (private key). CLI flags `--tls`, `--no-tls`, `--tls-cert`, and `--tls-key` override config and environment. If TLS is enabled without configured certificate/key material, the server generates `tls-cert.pem` and `tls-key.pem` in the inter-agent data directory with restrictive POSIX permissions; clients trust that generated certificate or the configured `INTER_AGENT_TLS_CERT`/`tlsCert`.

  TLS encrypts the WebSocket transport. It does not make remote or multi-user operation safe, and it does not replace shared-secret challenge-response authentication.

- **Shared-secret challenge-response authentication**

  Every connection starts with `hello`, then completes an HMAC-SHA-256 challenge-response using the resolved shared secret. The raw secret is never sent over the socket. Invalid or missing proofs receive the canonical `AUTH_FAILED` protocol error where possible. This handshake runs inside the WebSocket connection and is unchanged by TLS.

  The shared secret resolves in this order:

  1. `INTER_AGENT_SECRET`
  2. top-level inter-agent config key `secret`
  3. existing/generated local token file fallback

  `INTER_AGENT_SECRET` and config `secret` should be high-entropy values. Weak user-supplied secrets are guessable from observed handshakes.

- **Fallback state directory**

  The fallback generated secret file uses this data directory resolution order:

  - `INTER_AGENT_DATA_DIR`
  - `dataDir` from the inter-agent config file
  - platform default state directory

  Platform defaults are:

  - Linux: `${XDG_STATE_HOME:-~/.local/state}/inter-agent`
  - macOS: `~/Library/Application Support/inter-agent`
  - Windows: `%LOCALAPPDATA%\inter-agent` when available, otherwise `%APPDATA%\inter-agent` when available

  If `INTER_AGENT_SECRET` or config `secret` is set, core does not read or create the fallback token file for auth.

- **Config file location**

  The config file is `INTER_AGENT_CONFIG` when set. Otherwise it uses the platform config location:

  - Linux: `${XDG_CONFIG_HOME:-~/.config}/inter-agent/config.json`
  - macOS: `~/Library/Application Support/inter-agent/config.json`
  - Windows: `%APPDATA%\inter-agent\config.json` when available

- **Filesystem permissions**

  On POSIX-compatible filesystems, the data directory is mode `0700` and the fallback token file is mode `0600`.

  Existing fallback token files with broader POSIX permissions are tightened to `0600` when loaded.

  On platforms without POSIX mode semantics, file permission controls are best-effort and the localhost single-user assumptions still apply.

- **Server lifecycle**

  Server startup binds the configured host/port. Duplicate live servers are detected by bind failure.

  Authenticated shutdown and kick use the same challenge-response authentication as other operations and require a control-role connection.

- **Protocol validation**

  Core validates operation shapes and rejects unauthenticated or invalid requests with documented protocol error codes from `spec/error-codes.md`.

  Clients and adapters should key behavior on error `code`, not human-readable `message`.

- **Resource limits**

  The server bounds incoming frames, active connections, message text, and custom extension payloads.

  Defaults are:

  - `INTER_AGENT_FRAME_MAX`: 16 MiB
  - `INTER_AGENT_CONNECTION_MAX`: 64 active authenticated connections
  - `INTER_AGENT_DIRECT_MAX`: 2 MiB of UTF-8 text
  - `INTER_AGENT_BROADCAST_MAX`: 512 KiB of UTF-8 text
  - `INTER_AGENT_CUSTOM_TYPE_MAX`: 128 bytes
  - `INTER_AGENT_CUSTOM_PAYLOAD_MAX`: 1 MiB of JSON-encoded UTF-8 payload

  Direct and broadcast limits are measured after JSON decoding.

- **Idle shutdown**

  Manual server starts run until explicit shutdown by default.

  `--idle-timeout <seconds>` opts into automatic shutdown after an idle period. Adapter-started servers use an explicit 300-second idle timeout so helper-started processes clean themselves up.

- **Custom payloads**

  Custom extension payloads remain pass-through JSON after `custom_type` and payload-size validation. Core does not interpret custom payload semantics.

## Host integrations and direct clients

Host integrations may be Python-backed adapters or non-Python direct protocol clients.

Python-backed adapters should use importable core APIs for endpoint resolution, shared-secret resolution, and protocol operations.

Direct clients in another runtime have the same obligations:

- resolve the shared endpoint and secret consistently;
- never log or persist secrets or proofs in host-owned state unless explicitly configured by the user;
- preserve payload limits and routing semantics;
- treat peer messages as collaboration inputs, not authoritative instructions.

Host extension config may pass a configured secret to helper subprocesses as `INTER_AGENT_SECRET`. This supports isolated filesystems such as containers without requiring a shared data directory.

## Secret rotation

For `INTER_AGENT_SECRET` or config `secret`:

1. Update the secret value for the server and every client/adapter.
2. Restart the server.
3. Reconnect clients and adapters. Connections using the old secret fail with `AUTH_FAILED`.

For fallback generated token-file use:

1. Stop the local server with `./inter-agent stop` or `uv run inter-agent-shutdown` when it is reachable. If it is not reachable, terminate the server process.
2. Remove the token file from the active data directory.
3. Start the server again with `uv run inter-agent-server`. A new fallback secret is created with restrictive permissions where the platform supports them.
4. Reconnect clients and adapters.

## Explicit non-goals

- Protection from hostile same-user processes.
- Message confidentiality over WebSocket when TLS is disabled.
- Cross-machine trust, PKI lifecycle, mTLS, or remote transport hardening beyond transport encryption.
- Multi-tenant isolation, enterprise RBAC, or policy administration.

TLS provides transport encryption only; it does not make remote or multi-user operation fully safe.

## Extension areas

- Transport hardening for remote scenarios.
- Policy middleware such as rate limits or channel permissions.
- Future encrypted transports that use the shared secret as pre-shared key input.
