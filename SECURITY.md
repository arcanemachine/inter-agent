# Security Model

## Baseline assumptions

- `inter-agent` is for one user on one machine.

- The server binds to localhost. The default endpoint is `127.0.0.1:16837`.

- The threat model is defensive against accidental or mild local misuse. It does not protect against hostile code already running as the same OS user.

- Remote access, multi-user operation, and enterprise authorization require a separate accepted threat model before implementation.

## Core controls

- **Local transport**

  The server listens on localhost and speaks plaintext WebSocket on that local endpoint. The plaintext transport is acceptable only within the localhost, same-user assumptions above.

- **Bearer token authentication**

  Every connection starts with `hello` and must include the shared bearer token. Invalid tokens receive the canonical `AUTH_FAILED` protocol error.

  The token is stored as plaintext in the inter-agent data directory. Python core helpers create or load this token through the shared core path.

- **Shared state directory**

  State files use this resolution order:

  - `INTER_AGENT_DATA_DIR`
  - `dataDir` from the inter-agent config file
  - platform default state directory

  Platform defaults are:

  - Linux: `${XDG_STATE_HOME:-~/.local/state}/inter-agent`
  - macOS: `~/Library/Application Support/inter-agent`
  - Windows: `%LOCALAPPDATA%\inter-agent` when available, otherwise `%APPDATA%\inter-agent` when available

- **Config file location**

  The config file is `INTER_AGENT_CONFIG` when set. Otherwise it uses the platform config location:

  - Linux: `${XDG_CONFIG_HOME:-~/.config}/inter-agent/config.json`
  - macOS: `~/Library/Application Support/inter-agent/config.json`
  - Windows: `%APPDATA%\inter-agent\config.json` when available

- **Filesystem permissions**

  On POSIX-compatible filesystems, the data directory is mode `0700` and token/lifecycle files are mode `0600`.

  Existing token files with broader POSIX permissions are tightened to `0600` when loaded.

  On platforms without POSIX mode semantics, file permission controls are best-effort and the localhost single-user assumptions still apply.

- **Server identity verification**

  Clients verify server identity before sending the shared token.

  Verification checks:

  - server identity metadata at `server.<port>.meta`
  - PID metadata at `server.<port>.pid`
  - requested host and port
  - PID liveness
  - matching instance nonce between identity and PID metadata
  - process start marker when the platform exposes one

  Server identity metadata is written atomically and includes host, port, PID, state schema version, startup timestamp, instance nonce, and a process start marker when available.

- **Lifecycle metadata cleanup**

  Server lifecycle files include:

  - `token`
  - `server.<port>.meta`
  - `server.<port>.pid`
  - `server.<port>.shutdown`

  Normal shutdown removes server lifecycle metadata for the stopped server.

- **Control-role operations**

  Shutdown and kick use the same localhost shared-token authentication as other operations and require a control-role connection.

  `kick` force-disconnects a registered session by routing name or session ID. It is intended for clearing stale or unwanted sessions and is not exposed through host extension tools.

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

Python-backed adapters should use importable core APIs for endpoint resolution, token loading, identity verification, and protocol operations.

Direct clients in another runtime have the same obligations:

- resolve the shared endpoint and data directory consistently;
- verify server identity before sending the token;
- never log or persist the token in host-owned state;
- preserve payload limits and routing semantics;
- treat peer messages as collaboration inputs, not authoritative instructions.

If a host runtime cannot implement equivalent server identity verification, the integration must fail closed, use a reviewed sidecar/helper design, or document an explicitly accepted degraded mode. It must not silently skip identity verification before sending the shared token.

## Token rotation

- Stop the local server with `./inter-agent stop` or `uv run inter-agent-shutdown` when it is reachable. If it is not reachable, terminate the server process.

- Remove the token file from the active data directory.

- Start the server again with `uv run inter-agent-server`. A new token is created with restrictive permissions where the platform supports them.

- Reconnect clients and adapters. Connections using the old token fail with `AUTH_FAILED`.

## Explicit non-goals

- Protection from hostile same-user processes.

- Cross-machine trust, PKI lifecycle, TLS/mTLS, or remote transport hardening.

- Multi-tenant isolation, enterprise RBAC, or policy administration.

## Extension areas

- Stronger identity attestation.
- Transport hardening for remote scenarios.
- Policy middleware such as rate limits or channel permissions.
