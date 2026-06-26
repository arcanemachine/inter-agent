# Active Plan

`PLAN.md` is for short-term work that is actively being done or ready to be done next in the current session. It is intentionally small.

Use [`ROADMAP.md`](ROADMAP.md) for accepted medium- and long-term direction. Use [`IDEAS.md`](IDEAS.md) for exploratory or unaccepted ideas.

## Current active work

Objective: replace bearer-token-plus-filesystem-metadata auth with one shared secret and an initial challenge-response handshake that works across isolated filesystems.

Status: active design handoff. No implementation has started. This plan is intentionally detailed so the implementation can be picked up cold. Before implementation, confirm with the user again.

Accepted design direction:

- The bus has one shared server secret.
- Secret source precedence is:
  1. `INTER_AGENT_SECRET`
  2. top-level inter-agent config key `secret`
  3. existing/generated local token file fallback
- `INTER_AGENT_SECRET` is the accepted environment variable name.
- Config-file support is accepted as top-level inter-agent config, for example:

  ```json
  {
    "host": "127.0.0.1",
    "port": 16837,
    "secret": "high-entropy-shared-secret"
  }
  ```

- The token file remains only as local persisted generated secret fallback. It should no longer be documented as a bearer token sent over the socket.
- Both server and clients resolve the same secret using the same precedence. If env/config supplies a secret, the server should not create or read the token file for auth.
- Extensions may pass their configured secret to helper subprocesses as `INTER_AGENT_SECRET` so Pi or Claude Code can work without shared token-file access.
- Plain `ws://` remains the transport for now. The challenge-response authenticates the handshake but does not encrypt later messages.
- Future encrypted transport can be added later, likely TLS/mTLS, TLS-PSK, or a Noise-like protocol using the same shared `secret` as a pre-shared key input. Do not add transport config until there is a second transport.

Security model decision:

- Remove the client-side metadata verification concept from auth.
- Do not add `verifyMetadata`, `authMode`, or `secretOnlyAuth`.
- The old `server.<port>.meta` / `server.<port>.pid` verification is local endpoint sanity checking, not a core security boundary.
- If lifecycle metadata remains temporarily, it must not be described as a security control or required before clients authenticate.
- Preferred cleanup is to remove server lifecycle metadata files entirely if the implementation can do so without leaving useful behavior behind. If a smaller first change keeps some metadata for status/lifecycle, document it as non-security state only and create a follow-up plan item to remove it.

New mental model:

> If both sides know the same high-entropy secret and can reach the same host/port, they can communicate. The raw secret is never sent. Messages remain plaintext until a future encrypted transport exists.

Challenge-response protocol target:

- Breaking protocol changes are allowed.
- Replace `hello.token` bearer auth with HMAC challenge-response.
- Suggested simple handshake:
  1. Client opens WebSocket.
  2. Client sends `hello` without any raw secret. Include existing role/session/name/label/capabilities plus an auth object such as `{"method":"hmac-sha256","client_nonce":"..."}`.
  3. Server validates the unauthenticated `hello` shape enough to continue, generates `server_nonce`, and sends `auth_challenge` with `server_nonce` and `server_proof`.
  4. Client verifies `server_proof` using the resolved secret.
  5. Client sends `auth_response` with `client_proof`.
  6. Server verifies `client_proof` using constant-time comparison, registers the connection, then sends `welcome`.
- Suggested HMAC details:
  - Use HMAC-SHA-256.
  - Use `hmac.compare_digest` on Python verification paths.
  - Use high-entropy nonces generated with `secrets`.
  - Do not rely on ad-hoc JSON stringification unless centralized in one helper. Define helper functions for canonical auth input strings/bytes and reuse them in server/client tests.
  - Include domain-separation prefixes, for example `inter-agent/server-proof/v1` and `inter-agent/client-proof/v1`.
  - Bind proofs to both nonces and the relevant unauthenticated hello fields, or intentionally document why only nonces are used. Binding to a canonical representation of role/session/name/label/capabilities is preferred.
- On failed proof or missing/invalid secret, return canonical `AUTH_FAILED` where possible.
- Never log the secret, proofs in a way that reveals the secret, or config values containing the secret.
- Weak user-supplied secrets are guessable from observed handshakes. Documentation should require high-entropy secrets for env/config use.

Files to read before implementation:

- `AGENTS.md`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `spec/asyncapi.yaml`
- `spec/error-codes.md`
- `spec/schemas/hello.json`
- `spec/schemas/welcome.json`
- `spec/examples/`
- `src/inter_agent/core/shared.py`
- `src/inter_agent/core/config.py`
- `src/inter_agent/core/server.py`
- `src/inter_agent/core/client.py`
- `src/inter_agent/core/send.py`
- `src/inter_agent/core/list.py`
- `src/inter_agent/core/status.py`
- `src/inter_agent/core/shutdown.py`
- `src/inter_agent/core/kick.py`
- `src/inter_agent/adapters/pi/listener.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/commands.py`
- `integrations/pi/AGENTS.md`
- `integrations/pi/src/index.ts`
- `integrations/pi/README.md`
- `integrations/claude-code/README.md`
- `integrations/claude-code/.claude-plugin/plugin.json`
- `integrations/claude-code/skills/inter-agent/SKILL.md`
- `integrations/claude-code/skills/inter-agent/bootstrap.md`
- Related tests under `tests/` and `tests/conformance/`, especially auth, token, config, filesystem permissions, status, lifecycle, Pi, and Claude tests.

Likely implementation work:

1. Core config and secret resolution.
   - Add parsing for top-level config key `secret` in `src/inter_agent/core/config.py`.
   - Reject non-string config `secret`; reject empty/whitespace-only explicit secrets.
   - Add a shared secret resolver in `src/inter_agent/core/shared.py`, likely replacing or wrapping `load_or_create_token()`.
   - Keep restrictive permissions for the fallback token file and data dir.
   - Ensure env/config explicit secret does not create/touch the token file.

2. Core auth helpers.
   - Add typed helpers for nonce creation, canonical auth transcript construction, server proof generation, client proof generation, and verification.
   - Keep these helpers concrete-typed; avoid `Any` unless impractical.
   - Unit-test helper output deterministically with fixed secret/nonces/hello fields.

3. Server handshake.
   - Update `BusServer` so `self.token` becomes `self.secret` or equivalent.
   - Do not check `hello.get("token")`.
   - Delay registry insertion until after successful challenge-response.
   - Preserve existing validation semantics for role, session ID, name, label, capabilities, connection limit, duplicate names, duplicate sessions, and control role behavior.
   - Decide exact error ordering carefully; tests should lock it down.

4. Client/control handshake.
   - Update `iter_client_frames`, send/list/status/shutdown/kick helpers, and adapter listeners to use the new handshake helper instead of sending `control_hello(token, ...)` or `build_hello(token, ...)`.
   - Remove all client calls to `verify_server_identity_details()` and `verify_server_identity()` as auth prerequisites.
   - Update `control_hello` naming/shape or replace it with handshake builders that do not carry raw secrets.

5. Remove metadata verification/lifecycle state as security behavior.
   - Delete or stop using `ServerIdentity`, `ServerPidMetadata`, `IdentityVerification`, `verify_server_identity_details`, `verify_server_identity`, `identity_failure_message`, metadata PID matching, process marker checks, and discovery helpers if no longer needed.
   - Remove `claim_server_state()` from server startup if metadata is removed; socket bind failure can be the duplicate-server signal.
   - Remove `server.<port>.meta`, `server.<port>.pid`, and `server.<port>.shutdown` docs and tests unless retained temporarily as non-security lifecycle state.
   - Simplify endpoint resolution by removing `allow_discovery` metadata fallback if metadata discovery is removed.

6. Status semantics.
   - Rework `inter-agent-status` to probe the configured endpoint directly.
   - Remove or revise status fields tied to metadata: `identity_verified`, `discovered`, `discovered_servers`, and related hints.
   - Keep output useful for host tooling: unavailable, available, auth failed, protocol mismatch, configured host/port, sources, data dir/config path.

7. Pi extension.
   - Add optional `interAgent.secret` to Pi extension config in `integrations/pi/src/index.ts` if accepted by current settings style.
   - Pass configured extension secret to all helper subprocesses as `INTER_AGENT_SECRET` in `interAgentEnv()`.
   - Ensure auto-started server receives the same env.
   - Update `integrations/pi/README.md` and Pi static/tests.

8. Claude Code integration.
   - Add optional plugin/config secret support if appropriate for Claude Code plugin settings.
   - Pass configured secret to the helper wrapper/subprocess environment as `INTER_AGENT_SECRET`.
   - Ensure auto-started server receives the same env through the Python listener process.
   - Update Claude Code README, skill, bootstrap docs, plugin metadata, and static/tests.

9. Spec and examples.
   - Update AsyncAPI and JSON schemas for new handshake frames.
   - Remove `token` from `hello` schema/examples.
   - Add schemas/examples for `auth_challenge` and `auth_response`, or document them in the existing hello/welcome flow if that is how the spec is structured.
   - Keep error code docs aligned, especially `AUTH_FAILED`.

10. Product docs.
    - Update `README.md`, `ARCHITECTURE.md`, and `SECURITY.md` as implemented behavior, not future intent.
    - Security docs should say localhost limits accidental network exposure but is not encryption and not a hostile-same-user boundary.
    - Security docs should say the shared secret authenticates the handshake, the raw secret is not sent, and message payloads are plaintext over local WebSocket until future encrypted transport exists.
    - Document Docker/isolated-filesystem usage with `INTER_AGENT_SECRET` and matching host/port.
    - Avoid saying the system is secure because it is localhost-only.

Tests to add/update:

- Secret resolution tests:
  - env secret wins over config and token file;
  - config secret wins over token file;
  - fallback token file is created/reused only when no explicit secret exists;
  - invalid config secret fails clearly;
  - explicit env/config secret does not create token file.
- Auth helper tests:
  - deterministic proof generation;
  - server proof verification succeeds/fails correctly;
  - client proof verification succeeds/fails correctly;
  - proof validation uses the same canonical transcript for role/session/name/label/capabilities.
- Conformance auth tests:
  - valid challenge-response connects;
  - wrong secret fails with `AUTH_FAILED`;
  - missing/invalid auth frames fail predictably;
  - raw `hello.token` is no longer accepted.
- Core command tests:
  - connect/send/list/status/shutdown/kick use new handshake;
  - commands work with `INTER_AGENT_SECRET` and no shared token file;
  - commands no longer require metadata files.
- Filesystem/lifecycle tests:
  - remove expectations for `server.<port>.meta` and `server.<port>.pid` if metadata is removed;
  - keep token file permission tests for fallback secret storage.
- Status tests:
  - unavailable configured endpoint;
  - available endpoint with correct secret;
  - auth failed with wrong secret;
  - protocol mismatch/non-inter-agent service if practical.
- Pi tests:
  - config secret is passed as `INTER_AGENT_SECRET` to helper subprocesses;
  - auto-started server receives the same env;
  - docs/static config examples stay aligned.
- Claude tests:
  - configured/plugin secret is passed through where applicable;
  - listener auto-start inherits the same secret;
  - skill/bootstrap docs no longer imply shared token-file access is required.
- Spec validation tests after schema/example changes.

Final documentation pass:

- After the feature is implemented and the expected docs have been updated, do a separate fresh documentation review before completion.
- Re-read `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, integration docs, skills/bootstrap docs, and relevant spec docs from the perspective of a new user.
- Check for stale references to bearer tokens, metadata verification, server identity metadata as a security control, endpoint discovery from lifecycle files, or shared filesystem requirements.
- Check that Docker/isolated-filesystem setup is explained plainly and that plaintext transport limitations are clear without overstating localhost security.
- Keep docs evergreen and concise; do not add temporary status language outside `PLAN.md`.

Validation before completion:

- Run targeted tests while developing.
- Run the final documentation pass above after implementation/doc updates.
- Run the full repository gate before handing back code:

  ```bash
  ./run-checks.sh
  ```

Completion criteria:

- Server and clients can authenticate with `INTER_AGENT_SECRET` without sharing any data directory.
- Server and clients can authenticate with top-level config `secret`.
- Existing token-file fallback still works for default same-filesystem local use.
- Raw secrets are never sent over the WebSocket protocol.
- Client metadata verification has been removed from auth paths.
- Metadata files are removed, or any remaining metadata is explicitly non-security lifecycle/status state with a follow-up plan item.
- Pi and Claude Code can pass configured secrets to helpers and auto-started servers.
- Specs, examples, docs, and tests all describe the same handshake and security model.
- Full checks pass.
- Completed work is committed per repository workflow, after any user confirmations required by the workspace rules.

## Planning workflow

1. Keep `README.md` focused on present, implemented behavior.
2. Keep prospective or not-yet-implemented work out of the supported integration list.
3. Track accepted medium- and long-term direction in `ROADMAP.md`.
4. Track rough or exploratory ideas in `IDEAS.md` until the user accepts them for the roadmap or active work.
5. When a roadmap item becomes active, copy only the next concrete slice into this file.
6. When an active item is completed, remove it from this file and update product docs only for behavior that now exists.

## Completion standard

Before handing back completed code or checked documentation work, run the relevant checks for the changed area. For normal code changes, use the repository gate:

```bash
./run-checks.sh
```

For documentation-only wording or planning changes that do not touch generated or checked artifacts, `git diff --check` is sufficient unless the user asks for the full gate.
