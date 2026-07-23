# Task 1 — Prove installed Pi/Claude interoperability over TLS

Status: ready for dispatch

## Outcome

Prove that the installed Pi and Claude Code integration paths interoperate through one authenticated loopback `wss://` server. Cover direct messages, broadcast, pub/sub, control helpers, reconnect with stable certificate material, configuration propagation, and bounded rejection of plaintext/untrusted clients. Fix only a defect first reproduced by this acceptance work. If the complete matrix passes without a product defect, finish as test/documentation-only.

This is closeout item 9. Item 8d is closed in `e47a8ad`; the next roadmap item is the separately user-gated migration checkpoint. Do not begin migration, extraction, publication, or remote work.

## Authoritative references

Read these before changing files:

1. `AGENTS.md`
2. `/workspace/.agents/languages/python.md`
3. `.agents/PLAN.md`
4. this packet
5. `docs/plans/important-closeout/02-installed-tls-acceptance.md`
6. `docs/plans/important-closeout/00-execution-guide.md`
7. `SECURITY.md`
8. the current versions of every file selected from the allowed-file list below

For Pi changes, also read `integrations/pi/AGENTS.md`. For Claude integration changes, also read `integrations/claude-code/AGENTS.md`. Do not traverse or print `node_modules`, dependency trees, user/global configuration, credentials, certificate private-key contents, or real message bodies.

## Existing behavior — do not redesign it

- Loopback hosts default to `ws://`; explicit `tls=true`/`INTER_AGENT_TLS=true`/`--tls` selects `wss://`.
- Non-loopback hosts default to TLS. Do not change either default.
- Server TLS uses both a certificate and private key. With neither configured it creates `tls-cert.pem` and `tls-key.pem` in the resolved data directory. On POSIX, the data directory is `0700` and both files are `0600`.
- Clients trust the generated certificate in their shared data directory, or the explicit `tlsCert`/`INTER_AGENT_TLS_CERT`/`--tls-cert` path. Hostname checking is intentionally disabled for this local self-signed baseline; certificate-chain validation remains enabled.
- TLS does not replace HMAC challenge-response. A client with the trusted certificate but wrong shared secret must still fail authentication.
- Endpoint precedence is CLI > environment > config > host-based default. `dataDir`, `tlsCert`, and `tlsKey` retain their current resolution rules.
- Pi project settings override Pi global settings. Pi resolves relative `projectPath`, `dataDir`, `tlsCert`, and `tlsKey` against the settings file that declares them, then passes configured values to helper subprocesses as `INTER_AGENT_*` variables.
- Claude’s installed monitor invokes `integrations/claude-code/skills/inter-agent/bin/inter-agent-claude`. The wrapper selects the runtime helper but otherwise inherits normal `INTER_AGENT_*` endpoint/TLS configuration. Plugin `secret` may set `INTER_AGENT_SECRET`; no Claude-only TLS configuration exists or should be added.
- Pi queues inbound bodies by default; this task must not weaken mailbox secrecy or lifecycle behavior. Controlled acceptance bodies may be tested locally but must not be printed in reports.
- Pi and Claude listener reconnect loops are bounded and reapply desired channel subscriptions after a transient server restart.

## Allowed files

Use only the minimum necessary subset.

### Expected test and documentation files

- `tests/integration/test_cross_adapter_tls_live.py` (preferred new matrix)
- `tests/test_tls_transport.py`
- `tests/test_config_resolution.py`
- `tests/test_pi_extension_static.py`
- `tests/test_claude_wrapper.py`
- `integrations/pi/tests/extension-mailbox.test.ts`
- `README.md`
- `SECURITY.md`
- `integrations/pi/README.md`
- `integrations/claude-code/README.md`

Do not spread the TLS matrix across the existing plaintext live modules unless the new module cannot reuse their behavior clearly. If that exception is demonstrated, the only additional test files allowed are:

- `tests/integration/test_pi_adapter_live.py`
- `tests/integration/test_claude_adapter_live.py`
- `tests/integration/test_cross_adapter_pubsub_live.py`
- `tests/conftest.py`

### Product files allowed only after a failing regression test

Use the defect-to-owner table below. Do not modify product code speculatively.

- `src/inter_agent/core/config.py`
- `src/inter_agent/core/tls.py`
- `src/inter_agent/core/transport.py`
- `src/inter_agent/core/server.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/pi/listener.py`
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/listener.py`
- `integrations/pi/src/index.ts`
- `integrations/claude-code/skills/inter-agent/bin/inter-agent-claude`

Stop and report to `inter-agent-leader` before modifying any other file. Do not modify protocol/schema, auth semantics, message/channel semantics, limits, package metadata, plugin manifests/skills, mailbox implementation, kick/reload/compaction behavior, migration plans, repository layout, credentials, or publication assets.

## Phase 0 — Establish a clean baseline

1. Confirm `git status --short` is empty. If not, stop and report; do not overwrite another session’s work.
2. Confirm maintained installed versions used by acceptance: Pi `0.81.1` and the available Claude Code version. Record versions, not global package lists.
3. Use the repository `.venv` and lockfile. Do not install or upgrade dependencies.
4. Run the existing focused baseline before editing:

   ```bash
   uv run pytest \
     tests/test_tls_transport.py \
     tests/test_config_resolution.py \
     tests/integration/test_pi_adapter_live.py \
     tests/integration/test_claude_adapter_live.py \
     tests/integration/test_cross_adapter_pubsub_live.py -q
   npm --prefix integrations/pi test
   ```

5. If baseline fails, report the exact test names and stop. Do not conflate a pre-existing failure with TLS acceptance.

## Phase 1 — Add the automated TLS cross-adapter matrix

Prefer one new `tests/integration/test_cross_adapter_tls_live.py`. Keep its TLS server fixture file-local unless sharing demonstrably makes the existing `LiveServer` fixture clearer. Use `unused_tcp_port`, `tmp_path`/`tmp_path_factory`, `asyncio.create_task(run_server(...))`, and an isolated data directory. Use a test-only high-entropy or fixed non-production secret through `monkeypatch`; never print it.

### 1A. TLS server fixture

The fixture must:

1. Set isolated `INTER_AGENT_CONFIG`, `INTER_AGENT_DATA_DIR`, `INTER_AGENT_SECRET`, `INTER_AGENT_HOST=127.0.0.1`, `INTER_AGENT_PORT=<unused>`, and `INTER_AGENT_TLS=true`.
2. Start `run_server("127.0.0.1", port, tls=True, data_dir=data_dir)` with no explicit cert/key, causing default material generation.
3. Wait by probing the resolved TLS status, not by a fixed sleep alone.
4. Expose only host, port, data directory, certificate path, and test secret to test code. Never include the secret or private-key bytes in assertion messages.
5. Cancel and await the server task in `finally`.
6. Assert generated file locations and, on POSIX, `0700` data-directory plus `0600` certificate/key modes.

### 1B. Real adapter listeners

Start both real listener implementations against that fixture:

- Pi: `run_pi_listener(..., tls=True, data_dir=data_dir, tls_cert_path=cert_path)` with a unique `pi-tls-*` name and `io.StringIO` output.
- Claude: `ClaudeListener(..., tls=True, data_dir=data_dir, tls_cert_path=cert_path)` with a unique `claude-tls-*` name and `io.StringIO` output.

Use bounded polling for welcomes/server-visible presence. Do not mock SSL contexts, `AgentSession`, WebSocket connections, command functions, listener control sockets, or delivered adapter output. Always stop/cancel/await both listeners in `finally`.

Assert both adapter `list` and `status --json` paths resolve `tls=true`, the expected port/data directory/certificate source, and exactly the two agent names. Status/list connections are control sessions and must not appear as persistent agents.

### 1C. Direct and broadcast delivery

Through the adapter command APIs used by the real helper CLIs:

1. Send Pi → Claude using the Pi listener’s actual routing name as `from_name`; assert one Claude-formatted direct delivery with the correct sender/kind.
2. Send Claude → Pi using the Claude listener’s active identity; assert one Pi JSON direct frame with correct sender/recipient/kind.
3. Broadcast Pi → Claude and Claude → Pi; assert the other adapter receives each controlled body exactly once and the sender is not treated as a separate delivery target.
4. Assert command exit/result semantics remain adapter-specific: Pi helper JSON success and Claude helper silent success where currently documented.

Keep controlled bodies in local variables. Assertions may compare them, but test names, failure messages, logs, and the completion report must not quote them.

### 1D. Pub/sub and control paths

Use one unique channel and the listeners’ real local control sockets:

1. Subscribe both listeners through `pi_commands.subscribe(channel, pi_name)` and `claude_commands.subscribe(channel)`.
2. Call both adapters’ `channels` helpers. Each must report one entry containing both subscriber names and no control-session names.
3. Publish Claude → Pi; assert exactly one Pi channel delivery with channel/sender metadata and no echo in Claude output.
4. Publish Pi → Claude; assert exactly one Claude channel delivery with channel/sender metadata and no echo in Pi output.
5. Unsubscribe Pi and prove only Claude remains; unsubscribe Claude and prove the channel disappears.
6. Exercise the normal TLS `status`, `list`, `channels`, subscribe/unsubscribe, publish, direct-send, and broadcast helper paths. Do not substitute direct protocol frames for those helper paths.

### 1E. Restart and subscription recovery

In one test:

1. Subscribe both listeners to a unique channel.
2. Record a hash of the generated certificate locally; never print certificate/key contents.
3. Cancel and await only the TLS server task. Keep both listeners running.
4. Restart `run_server` on the same host/port with the same data directory, secret, and `tls=True`.
5. Poll until both exact names are present once and both are resubscribed. Do not accept a suffixed name or duplicate registration.
6. Assert the certificate hash is unchanged.
7. Publish once in each direction and send one direct message in each direction; assert exact-once post-reconnect delivery.
8. Assert no unbounded traceback/error output and no leaked secret/private-key text.

### 1F. Negative transport/auth cases

Add focused tests with bounded diagnostics:

1. **Plaintext against TLS:** connect/probe the TLS port with `tls=False`/`ws://`; require unavailable/connection failure or a WebSocket exception. It must not authenticate or list agents.
2. **Untrusted certificate:** create a second unrelated generated certificate in a separate data directory using project TLS helpers. Probe the real TLS server with `tls=True` and that unrelated certificate. Require failure, no agent registration, no traceback in adapter-facing diagnostics, and no certificate-validation bypass.
3. **Missing configured certificate:** retain or strengthen the existing `TLS configuration failed:` assertion; it must name the missing path/action without a traceback.
4. **Wrong secret over trusted TLS:** use the real trusted certificate with a different test secret. Require canonical authentication failure, proving TLS and HMAC are both enforced.

Do not weaken `ssl` verification, set an unverified context, add `--insecure`, catch failures as success, rely on machine-global trust, or use an external host.

## Phase 2 — Prove host configuration propagation

### 2A. Pi extension behavior

Add behavior coverage in `integrations/pi/tests/extension-mailbox.test.ts` using its existing fake-spawn/settings harness. Configure project-local relative values for:

- `dataDir`
- `tlsCert`
- `tlsKey`
- `tls: true`

Start the listener and inspect only the captured child options. Assert:

1. paths resolve relative to the project settings file;
2. child environment includes exactly the resolved `INTER_AGENT_DATA_DIR`, `INTER_AGENT_TLS`, `INTER_AGENT_TLS_CERT`, and `INTER_AGENT_TLS_KEY` values;
3. the secret remains environment-only and absent from command arguments/notices/diagnostics;
4. TLS paths and secret are absent from listener command arguments unless the existing Python helper interface deliberately requires non-secret TLS flags—do not introduce duplicate propagation;
5. project settings still override global settings.

Use `tests/test_pi_extension_static.py` only for the public configuration boundary if needed; behavior coverage is authoritative and source-string assertions must not replace it.

### 2B. Claude installed wrapper behavior

Add `tests/test_claude_wrapper.py` coverage with a fake selected helper that emits only a fixed boolean/presence summary, never raw values. Invoke the bundled wrapper with isolated `HOME`, normal `INTER_AGENT_DATA_DIR`, `INTER_AGENT_TLS`, `INTER_AGENT_TLS_CERT`, and `INTER_AGENT_TLS_KEY`, plus plugin `project_path` and test `secret`. Assert:

1. the selected helper receives all TLS/data variables unchanged;
2. plugin `secret` maps to `INTER_AGENT_SECRET` without entering argv/stdout/stderr;
3. the wrapper adds no Claude-specific TLS defaults and does not strip core config/environment;
4. helper arguments remain unchanged.

Do not add TLS fields to the Claude plugin manifest: installed Claude uses the shared core environment/config path.

### 2C. Core precedence

Retain the existing CLI > environment > config > default contract. Add to `tests/test_config_resolution.py` only if the acceptance matrix exposes an uncovered precedence defect. At minimum, ensure the focused suite still covers loopback plaintext default, explicit loopback TLS, non-loopback TLS default, config TLS paths, environment overrides, and CLI overrides.

## Defect-to-owner recipe

A product edit requires a failing behavior test first. Apply only the matching row:

| Observed failure | Owning files allowed | Required regression |
|---|---|---|
| Endpoint/TLS/data/cert/key precedence is wrong | `src/inter_agent/core/config.py` | `tests/test_config_resolution.py` |
| Generated material, permissions, server context, or client trust is wrong | `src/inter_agent/core/tls.py`, and only if necessary `transport.py`/`server.py` | `tests/test_tls_transport.py` plus matrix case |
| Pi extension drops or mis-resolves configured values | `integrations/pi/src/index.ts` | TypeScript fake-spawn behavior test |
| Pi Python helper drops resolved TLS into listener/control operations | Pi `commands.py` and/or `listener.py` | cross-adapter TLS behavior test |
| Claude wrapper strips environment or exposes secret | bundled `inter-agent-claude` wrapper | `tests/test_claude_wrapper.py` |
| Claude Python helper drops resolved TLS into listener/control operations | Claude `commands.py` and/or `listener.py` | cross-adapter TLS behavior test |

If a failure points to protocol/schema, auth redesign, certificate policy, package installation, host APIs, or any file outside the table, stop and report. Do not improvise a broader fix.

## Phase 3 — Documentation

Update evergreen docs only after the behavior passes. Prefer no wording change if current docs already state the verified behavior accurately. Any change must preserve these facts:

- Pi and Claude inherit core endpoint, TLS, certificate, state, and HMAC configuration.
- Generated certificates work when server and clients share the same reachable data directory; otherwise configure the client’s trusted certificate explicitly.
- Enabling TLS still requires the same shared-secret authentication.
- Loopback plaintext and non-loopback TLS defaults do not change.
- The baseline is local single-user transport encryption, not mTLS, federation, public PKI automation, remote hardening, or multi-user security.

Do not add prospective packaging, migration, or release claims.

## Phase 4 — Automated checks

Run in this order and report exact totals:

```bash
uv run pytest \
  tests/test_tls_transport.py \
  tests/test_config_resolution.py \
  tests/test_claude_wrapper.py \
  tests/test_pi_extension_static.py \
  tests/integration/test_cross_adapter_tls_live.py \
  tests/integration/test_pi_adapter_live.py \
  tests/integration/test_claude_adapter_live.py \
  tests/integration/test_cross_adapter_pubsub_live.py -q

npm --prefix integrations/pi test
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi exec -- prettier --check \
  src/index.ts src/mailbox.ts tests/**/*.ts README.md package.json tsconfig.json tsconfig.test.json
npm --prefix integrations/pi run build

uv run pytest \
  tests/test_claude_plugin_static.py \
  tests/test_claude_skill_static.py \
  tests/test_claude_wrapper.py -q
./run-checks.sh
git diff --check
```

If `tests/integration/test_cross_adapter_tls_live.py` is legitimately not created because an existing matrix is extended, substitute the exact selected module and explain why. Do not omit the full gate.

## Phase 5 — Installed-path acceptance recipe

This is mandatory and is separate from pytest. Use the installed maintained Pi `0.81.1`, the repository `.venv` helpers, Claude’s bundled monitor wrapper, one isolated TLS server, and unique ephemeral names/channel/bodies. Never use the user’s active bus, default port, global Pi package state, global inter-agent state, or real secrets.

### 5A. Isolation and cleanup trap

1. Create `/tmp/inter-agent-tls-uat.XXXXXX` with subdirectories for server state, Pi agent config, Pi project, and captured process output.
2. Allocate an unused loopback port by binding to port zero and closing the socket immediately before server start.
3. Generate an ephemeral high-entropy secret in memory. It may be passed through isolated process environments or the temporary Pi settings file, but never shell command arguments, terminal output, logs, the report, or repository files.
4. Create unique `pi-tls-*`, `claude-tls-*`, and channel names.
5. Install a trap before starting processes. It must stop children, wait for them, check tmux clients before killing any UAT tmux session, remove the isolated Pi package/config, and delete the entire temporary root.

### 5B. Start the real TLS server

Start the repository `.venv/bin/inter-agent-server` with environment-only data directory/secret/host/port and `--tls`. Capture output to a mode-`0600` temporary log. Poll `.venv/bin/inter-agent-status --json` with matching environment until available. Assert generated material and POSIX modes without printing the files.

### 5C. Install and start Pi without duplicate extensions

1. Set `PI_CODING_AGENT_DIR` to the isolated Pi agent-config directory while retaining the normal `HOME`; do not load globally installed packages.
2. Run `PI_CODING_AGENT_DIR=<isolated> pi install <repository-root>`.
3. Write isolated Pi project `.pi/settings.json` with `interAgent.projectPath=<repository-root>`, host, port, server `dataDir`, ephemeral secret, `tls=true`, and explicit generated `tlsCert`/`tlsKey`. Set `deliveryMode` to `immediate` only for this controlled UAT so local assertions can observe delivery; do not change repository defaults.
4. Start actual Pi from that project in an unattached uniquely named tmux session with `PI_CODING_AGENT_DIR=<isolated> pi --approve --no-session --inter-agent <pi-name>`.
5. Poll the TLS list helper until the Pi name appears exactly once. If Pi exits, capture only bounded sanitized diagnostics; never dump the full pane/settings/environment.

### 5D. Start Claude through the installed monitor path

Invoke `integrations/claude-code/skills/inter-agent/bin/inter-agent-claude listen --name <claude-name>` as a persistent child with:

- `CLAUDE_PLUGIN_OPTION_PROJECT_PATH=<repository-root>`
- matching environment-only host/port/data directory/secret/TLS/cert/key

This is the installed plugin’s bundled monitor path and must resolve the checkout `.venv/bin/inter-agent-claude`. Do not bypass the wrapper by launching the Python listener directly. Poll list until both exact names appear once.

### 5E. Exercise installed traffic

Drive Pi slash commands through tmux and Claude commands through the same bundled wrapper/environment. Use local assertions against captured outputs; do not print controlled bodies.

1. Pi direct-send to Claude; assert one Claude monitor delivery.
2. Claude direct-send to Pi; assert one Pi immediate delivery.
3. Broadcast from each side; assert exactly one delivery at the other side.
4. Subscribe both to the UAT channel; assert `channels --json` reports both names.
5. Publish in each direction; assert exactly one delivery to the other adapter and no self-echo.
6. Run both adapters’ status/list/channels paths over TLS and assert successful bounded output.

### 5F. Restart and negative controls

1. Stop only the server, preserve its data directory/cert/key, and restart on the same port.
2. Poll until both listeners reconnect under the exact same names and subscriptions reappear. Assert each appears once.
3. Send direct and channel traffic both ways after restart; assert exact-once delivery.
4. Run a plaintext status/list probe against the TLS port. Require failure/unavailable, no registration, no traceback, and no secret leakage.
5. Generate an unrelated certificate in a separate temporary directory and run trusted-TLS probes through both adapter helper paths using that wrong certificate. Require bounded failure, no registration, no traceback, and no secret/private-key leakage.
6. Run a trusted-certificate probe with a wrong secret and require authentication failure, proving TLS did not replace HMAC.

### 5G. Final cleanup proof

Disconnect/terminate both listeners, stop the server, and assert their names disappear. Run the trap. Confirm no UAT process, tmux session, temp root, isolated Pi package state, or generated `integrations/pi/dist`/`dist-tests` remains.

If this container cannot drive actual Pi or the Claude bundled wrapper, report the exact failing stage and environment limitation after the automated matrix passes. Do not replace installed acceptance with a mock and do not claim it passed.

## Security and evidence rules

- Never print or return the shared secret, auth proof, private key, certificate contents, process environment, or UAT bodies.
- Do not place the secret in argv. Temporary isolated config/environment is allowed and must be deleted.
- Logs must be mode `0600`, bounded, and deleted. Report stage/result summaries only.
- Failure assertions must not interpolate secrets or full environments.
- Do not weaken certificate validation or add an insecure escape hatch.
- Do not contact external hosts, use machine trust stores, or modify global Pi/Claude/inter-agent configuration.
- Do not kill any tmux session with attached clients.

## Completion criteria

All are required:

1. Generated TLS material and permissions pass.
2. Pi and Claude listeners authenticate and remain exactly once on one `wss://` server.
3. Direct, broadcast, channel membership/diagnostics, and bidirectional publish work exactly once.
4. Status/list/control helpers use the same TLS endpoint.
5. Both listeners reconnect with the same names and subscriptions after same-state server restart.
6. Plaintext, unrelated-certificate, and wrong-secret clients fail safely and register nothing.
7. Pi settings and Claude wrapper propagation are behavior-tested without secret-in-argv/output.
8. Current plaintext tests and all reliability/mailbox/kick/reload behavior remain green.
9. Focused tests, Pi checks, Claude validation, installed-path UAT, full repository gate, diff check, and cleanup pass.
10. Only allowed files changed; no credentials, generated outputs, UAT artifacts, or unrelated cleanup remain.

## Completion report — exact structure

Send only to `inter-agent-leader` and do not commit. Use these headings:

1. **Baseline** — versions and focused pre-edit results.
2. **Matrix implementation** — test architecture and exact files changed.
3. **TLS results** — generated material, direct/broadcast, pub/sub/control, reconnect, and negative cases.
4. **Configuration propagation** — Pi and Claude evidence.
5. **Defects and fixes** — each red test, owning layer, fix; or explicitly “no product defect found.”
6. **Installed acceptance** — each stage/result or precise limitation; no bodies/secrets.
7. **Verification** — exact commands and totals.
8. **Security** — certificate validation, HMAC, secret/argv/log evidence.
9. **Cleanup** — processes, tmux, temp state, generated build artifacts.
10. **Scope** — changed-file list and allowed-file confirmation.
11. **Limitations** — only genuine remaining limitations.

Questions, blockers, status, and completion reports go exclusively to `inter-agent-leader`. Do not message other agents, change plans, broaden scope, or commit.
