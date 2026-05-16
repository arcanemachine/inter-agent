# Live Tests and Fixtures

Extra Phase: 8 — OpenCode Support

## Purpose

Prove the OpenCode integration works against a live inter-agent bus while keeping the automated quality gate practical and not dependent on an interactive OpenCode session.

## Scope

- TypeScript unit tests for protocol and formatting helpers.
- Live-server tests for direct protocol behavior.
- Structural tests for plugin metadata and exports.
- Manual OpenCode user acceptance tests.
- Root quality-gate integration once checks are stable.

## Automated test strategy

1. **Unit tests inside `integrations/opencode/`**
   - Protocol envelope builders.
   - Error classification.
   - Name validation.
   - Formatting and truncation.
   - Inbox bounding and continuation records.
   - Config defaults and overrides.
   - Identity metadata parsing with fixture files.

2. **Mock WebSocket tests**
   - Control handshake succeeds.
   - Control handshake receives protocol error.
   - `send` receives an error frame for unknown target.
   - Listener receives `welcome` and `msg` frames.
   - Permanent errors stop reconnect.
   - Transient close triggers reconnect.

3. **Live inter-agent server tests**
   - Start the Python server on an unused port with temporary `INTER_AGENT_DATA_DIR`.
   - Connect the TypeScript listener as one agent.
   - Send direct message from another control connection.
   - Send broadcast message.
   - Verify list/status behavior.
   - Verify shutdown behavior in an isolated test.

4. **Structural package tests**
   - `package.json` exports include `./tui` and `./server`.
   - Built files exist after `npm run build`.
   - Entry modules do not default-export both targets from one file.
   - README examples reference current command names.

5. **OpenCode-host tests**
   - Automated tests should not require a real interactive OpenCode TUI in the required gate.
   - If a host-level smoke test is practical, keep it optional and documented separately.
   - Prefer a manual UAT checklist for interactive behavior.

## Manual UAT checklist

Run these before marking OpenCode support complete:

1. Install the OpenCode plugin from the local `integrations/opencode/` path.
2. Start an inter-agent server with a temporary or test data directory.
3. Open an OpenCode TUI session with the plugin enabled.
4. Run `/inter-agent-connect opencode-a --label "OpenCode A"`.
5. Start a Pi or another OpenCode session as `peer-a`.
6. From OpenCode, send a direct message to `peer-a`.
7. From `peer-a`, send a direct message to `opencode-a`.
8. Confirm OpenCode shows an attention notification and toast.
9. Confirm long message truncation and inbox continuation.
10. Broadcast from OpenCode and confirm peers receive it.
11. Broadcast from a peer and confirm OpenCode receives it.
12. Run `/inter-agent-list` and confirm both sessions appear.
13. Run `/inter-agent-status` and confirm server and listener state are accurate.
14. Restart the inter-agent server and confirm OpenCode reconnect behavior.
15. Trigger a permanent error, such as duplicate name, and confirm retries stop.
16. Disconnect and confirm listener cleanup.
17. Reload or restart OpenCode and confirm persisted state behaves as designed.
18. Ask the OpenCode agent to use `inter_agent_send` and confirm tool execution.
19. Ask the OpenCode agent to use `inter_agent_list` and confirm structured output.
20. Confirm peer messages do not bypass OpenCode permissions or policy.

## Work

1. Choose the test runner for `integrations/opencode/`.
   - Prefer the existing OpenCode ecosystem where practical.
   - Keep dependency footprint small.

2. Add unit tests for pure helper modules.
3. Add mock WebSocket tests.
4. Add live-server tests that can run from the OpenCode package or root test harness.
5. Add structural package tests.
6. Add a documented manual UAT file or README section.
7. Wire stable OpenCode checks into `./run-checks.sh` only after they pass consistently in the container.
8. Keep interactive OpenCode validation outside the mandatory gate unless it can run headlessly and reliably.

## Acceptance criteria

- Unit tests cover protocol, errors, formatting, config, and inbox behavior.
- Live tests prove TypeScript direct protocol compatibility with the Python inter-agent server.
- Required tests do not need an interactive OpenCode session.
- Manual UAT covers commands, tools, listener delivery, reconnects, truncation, and policy.
- `./run-checks.sh` includes OpenCode package checks once stable.

## Files likely to change

- `integrations/opencode/package.json`
- `integrations/opencode/src/`
- `integrations/opencode/test/`
- `integrations/opencode/README.md`
- `run-checks.sh`
- `tests/` if Python-side live fixtures are reused

## Checks

```bash
cd integrations/opencode
npm run typecheck
npm run build
npm test
```

Root checks before completion:

```bash
./run-checks.sh
```
