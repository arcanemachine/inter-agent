# Direct Protocol Client

Prospective roadmap item — OpenCode Support

## Purpose

Implement a direct TypeScript client for the inter-agent protocol so the OpenCode plugin can run without Python, `uv`, or subprocess CLI bridges.

## Scope

- Client-side protocol envelopes needed by OpenCode.
- Shared-secret loading, TLS/certificate trust, and challenge-response server proof verification.
- Agent listener connection and short-lived control connections.
- Error handling aligned with `spec/error-codes.md`.
- Tests for protocol and error behavior.

## Protocol operations required

The OpenCode integration needs these operations:

- `hello` as `agent` for the persistent listener.
- `hello` as `control` for one-shot commands and tools.
- `send` with optional `from_name`.
- `broadcast` with optional `from_name`.
- `list`.
- `shutdown`.
- Listener handling for `welcome`, `msg`, `error`, and transport close.

Optional later:

- `custom` for host-specific payloads.
- `ping`/`pong` only if the current protocol or server behavior requires it.

## Required spike before full implementation

Before building the full client, prove direct WebSocket access from the OpenCode plugin runtime as described in `docs/plans/opencode-support/00-execution-guide.md`.

Minimum proof:

1. Load a local OpenCode TUI plugin.
2. Open a WebSocket from that plugin.
3. Read the inter-agent shared secret from environment/config/token-file resolution.
4. Resolve `ws://` or `wss://` using the same effective TLS defaults as core.
5. Send a valid `hello` envelope to a live inter-agent server.
6. Complete `auth_challenge` / `auth_response` without sending the raw shared secret.
7. Receive a `welcome` frame.
8. Receive one `msg` frame if practical.

If this proof fails, stop and report. Do not continue with a Python CLI bridge unless the design is explicitly updated and accepted.

## Work

1. Read the canonical protocol references before implementation.
   - `spec/asyncapi.yaml`
   - `spec/schemas/hello.json`
   - `spec/schemas/welcome.json`
   - `spec/schemas/send.json`
   - `spec/schemas/broadcast.json`
   - `spec/schemas/list.json`
   - `spec/schemas/list_ok.json`
   - `spec/schemas/shutdown.json`
   - `spec/schemas/msg.json`
   - `spec/schemas/error.json`
   - `src/inter_agent/core/shared.py`
   - `src/inter_agent/core/client.py`
   - `src/inter_agent/core/send.py`
   - `src/inter_agent/core/list.py`
   - `src/inter_agent/core/status.py`
   - `src/inter_agent/core/shutdown.py`

2. Implement shared defaults.
   - Default host: `127.0.0.1`.
   - Default port: `16837`.
   - Default data directory: `INTER_AGENT_DATA_DIR`, config `dataDir`, or the platform default state directory.
   - Default direct, broadcast, frame, custom, and connection limits should match the core defaults where the client validates locally.

3. Implement shared-secret loading.
   - Resolve `INTER_AGENT_SECRET`, config `secret`, or fallback token file with the same effective precedence as core.
   - If the fallback token does not exist, decide whether the OpenCode extension may create it or should instruct the user to start the server first.
   - Match restrictive file permissions where the runtime allows it.
   - Never log the shared secret or HMAC proofs.

4. Implement TLS and server proof handling.
   - Resolve `INTER_AGENT_TLS`, config `tls`, and loopback/non-loopback defaults.
   - Resolve `INTER_AGENT_TLS_CERT` / config `tlsCert` and trust the configured/default certificate for `wss://` connections.
   - Build `hello` with HMAC auth metadata.
   - Verify the server proof from `auth_challenge` before sending `auth_response`.
   - Do not depend on `server.<port>.meta` or `server.<port>.pid` files unless a future core server metadata feature is accepted; those files are not part of the current implemented core.

5. Implement protocol envelope builders.
   - `buildAgentHello({ sessionId, name, label })`
   - `buildControlHello({ sessionId })`
   - `buildSend({ to, text, fromName })`
   - `buildBroadcast({ text, fromName })`
   - `buildList()`
   - `buildShutdown()`

6. Implement control operations.
   - Open WebSocket.
   - Send control `hello` and complete challenge-response authentication without sending the raw shared secret.
   - Wait for `welcome` or `error`.
   - Send operation.
   - For operations that can return protocol errors, wait briefly for an error frame before reporting success.
   - Normalize results for commands and LLM tools.

7. Implement the persistent listener primitive.
   - Open WebSocket.
   - Send agent `hello` with session ID, name, label, and capabilities, then complete challenge-response authentication without sending the raw shared secret.
   - Emit structured callbacks for `welcome`, `msg`, `error`, and close.
   - Do not perform OpenCode UI work in the low-level client module.

8. Implement permanent versus transient error handling.
   - Permanent errors should stop reconnect attempts:
     - `AUTH_FAILED`
     - `BAD_LABEL`
     - `BAD_NAME`
     - `BAD_ROLE`
     - `BAD_SESSION`
     - `NAME_TAKEN`
     - `SESSION_TAKEN`
     - `TOO_MANY_CONNECTIONS`
   - Transient errors should be eligible for bounded reconnect.

9. Implement validation helpers.
   - Validate routing names using the same rule as the core server: lowercase alphanumeric start, lowercase alphanumeric or hyphen continuation, max 40 characters.
   - Validate configured port and host.
   - Validate outbound text length before sending when possible.

10. Add tests.
   - Unit-test envelope builders.
   - Unit-test shared-secret resolution and TLS config/certificate handling against fixture files.
   - Unit-test error classification.
   - Add a mock WebSocket server test if practical in the OpenCode package.
   - Add a live inter-agent server test later under the integration-test plan.

## Acceptance criteria

- OpenCode shared client code can connect to a live inter-agent server without invoking Python or shelling out to inter-agent CLIs.
- Shared-secret loading, TLS behavior, and challenge-response server proof verification follow the core security model.
- Control operations produce stable typed results for TUI commands and server tools.
- The listener primitive can receive direct and broadcast `msg` frames.
- Permanent protocol errors stop reconnect attempts.
- Tests cover protocol envelope generation and error classification.

## Files likely to change

- `integrations/opencode/src/client.ts`
- `integrations/opencode/src/protocol.ts`
- `integrations/opencode/src/identity.ts` if retained for local sender identity/state rather than server metadata
- `integrations/opencode/src/errors.ts`
- `integrations/opencode/src/config.ts`
- `integrations/opencode/src/format.ts`
- `integrations/opencode/test/` or equivalent test location
- `spec/error-codes.md` only if protocol docs are stale

## Checks

```bash
cd integrations/opencode
npm run typecheck
npm run build
npm test  # after a test script exists
```

Run the root gate before completing the phase:

```bash
./run-checks.sh
```
