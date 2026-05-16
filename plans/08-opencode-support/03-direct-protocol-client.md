# Direct Protocol Client

Extra Phase: 8 — OpenCode Support

## Purpose

Implement a direct TypeScript client for the inter-agent protocol so the OpenCode plugin can run without Python, `uv`, or subprocess CLI bridges.

## Scope

- Client-side protocol envelopes needed by OpenCode.
- Token loading and server identity verification.
- Agent listener connection and short-lived control connections.
- Error handling aligned with `ERROR_CODES.md`.
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

Before building the full client, prove direct WebSocket access from the OpenCode plugin runtime as described in `plans/08-opencode-support/00-execution-guide.md`.

Minimum proof:

1. Load a local OpenCode TUI plugin.
2. Open a WebSocket from that plugin.
3. Read the inter-agent token and server metadata from the configured data directory.
4. Send a valid `hello` envelope to a live inter-agent server.
5. Receive a `welcome` frame.
6. Receive one `msg` frame if practical.

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
   - Default port: `9473`.
   - Default data directory: `INTER_AGENT_DATA_DIR` or `~/.inter-agent`.
   - Default direct, broadcast, frame, custom, and connection limits should match the core defaults where the client validates locally.

3. Implement token loading.
   - Read the existing token from the inter-agent data directory.
   - If the token does not exist, decide whether the OpenCode extension may create it or should instruct the user to start the server first.
   - Match restrictive file permissions where the runtime allows it.
   - Never log the token.

4. Implement server identity verification.
   - Read `server.<port>.meta` and `server.<port>.pid` from the data directory.
   - Confirm host and port match the configured endpoint.
   - Confirm metadata nonce matches.
   - Confirm the server PID is live where the current platform supports it.
   - On Linux, port the `/proc/<pid>/stat` start-marker check where practical.
   - On platforms where full verification is unavailable, fail closed unless the design explicitly accepts a documented degraded mode.

5. Implement protocol envelope builders.
   - `buildAgentHello({ token, sessionId, name, label })`
   - `buildControlHello({ token, sessionId })`
   - `buildSend({ to, text, fromName })`
   - `buildBroadcast({ text, fromName })`
   - `buildList()`
   - `buildShutdown()`

6. Implement control operations.
   - Open WebSocket.
   - Verify identity before sending token.
   - Send control `hello`.
   - Wait for `welcome` or `error`.
   - Send operation.
   - For operations that can return protocol errors, wait briefly for an error frame before reporting success.
   - Normalize results for commands and LLM tools.

7. Implement the persistent listener primitive.
   - Open WebSocket.
   - Verify identity before token transmission.
   - Send agent `hello` with session ID, name, label, and capabilities.
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
   - Unit-test token and identity parsing against fixture files.
   - Unit-test error classification.
   - Add a mock WebSocket server test if practical in the OpenCode package.
   - Add a live inter-agent server test later under the integration-test plan.

## Acceptance criteria

- OpenCode shared client code can connect to a live inter-agent server without invoking Python or shelling out to inter-agent CLIs.
- Token loading and identity verification follow the core security model.
- Control operations produce stable typed results for TUI commands and server tools.
- The listener primitive can receive direct and broadcast `msg` frames.
- Permanent protocol errors stop reconnect attempts.
- Tests cover protocol envelope generation and error classification.

## Files likely to change

- `integrations/opencode/src/client.ts`
- `integrations/opencode/src/protocol.ts`
- `integrations/opencode/src/identity.ts`
- `integrations/opencode/src/errors.ts`
- `integrations/opencode/src/config.ts`
- `integrations/opencode/src/format.ts`
- `integrations/opencode/test/` or equivalent test location
- `ERROR_CODES.md` only if protocol docs are stale

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
