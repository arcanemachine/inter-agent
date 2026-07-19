# Task 1 — Pi pre-connect list behavior

Status: active

## Goal

Make `/inter-agent list` an intentional read-only diagnostic before Pi connects: use a short-lived authenticated connection to the configured server, show current sessions or an intentional empty result when reachable, and preserve bounded actionable failures without starting or mutating the Pi listener.

## Context

`TODO.md` records that `/inter-agent list` errors before Pi connects. The durable requirements are accepted in `docs/plans/important-closeout/03-reliability-closeout.md` (item 6). The current extension source appears not to gate `handleList` on `listenerReady` or `currentConnection`, and the helper can list against a reachable server without a Pi listener; reproduce the installed Pi behavior before deciding whether the defect is in command handling, response validation, diagnostics, tests, documentation, or a stale TODO. Do not claim the issue is resolved from source inspection alone.

## Allowed files to modify

- `integrations/pi/src/index.ts`
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`
- `tests/test_pi_adapter_cli.py`
- `tests/integration/test_pi_adapter_live.py`
- `TODO.md`

## Additional files allowed to read

- `integrations/pi/AGENTS.md`
- `integrations/pi/package.json`
- `integrations/pi/tsconfig.json`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/core/list.py`
- `src/inter_agent/core/status.py`
- `tests/test_core_command_api.py`
- `tests/test_pi_listener.py`
- `docs/plans/important-closeout/03-reliability-closeout.md`

Do not read or modify other files without reporting why this packet is insufficient. If reproduction identifies a required Python helper/core behavior change, stop and report the exact evidence rather than broadening scope.

## Non-goals

- No listener lifecycle, connect, disconnect, rename, send, broadcast, publish, channels, subscription, protocol, server, auth, or TLS-policy redesign.
- No server auto-start or Pi auto-connect from list.
- No listener creation, replacement, shutdown, or connection-state mutation.
- No fabricated empty success when the server, authentication, TLS setup, command execution, or response is invalid.
- No removal or renaming of the existing `inter_agent_list` LLM-callable tool, and no new tools.
- No unrelated formatting or documentation churn.

## Requirements

1. Reproduce `/inter-agent list` through the installed Pi extension before Pi connects, against the configured server state relevant to the failure.
2. Keep list independent of `listenerReady`, `listenerProcess`, and `currentConnection`; it must use the existing short-lived authenticated list helper.
3. Against a reachable server with no agent sessions, report an intentional successful empty result.
4. Against a reachable server with sessions, report those sessions consistently before and after Pi connects.
5. Preserve bounded actionable failure diagnostics when the server is unavailable, authentication fails, TLS setup fails, command execution fails, or output is malformed. Never turn these failures into an empty success.
6. Validate the list response shape before rendering. A success response must be the expected `list_ok` object with a sessions array; malformed success output must produce the existing invalid-response diagnostic.
7. Listing must not start, stop, replace, or reconnect the Pi listener; update persisted/live connection state; or invoke server startup/shutdown.
8. Preserve the existing `inter_agent_list` tool boundary and behavior. Do not add another list tool or expose unrelated commands as tools.
9. Add or update focused tests before implementation. Cover command and tool paths, absence of listener gating/state mutation, reachable-empty, reachable-populated, unavailable, authentication failure, malformed output, and bounded diagnostics. Use live helper/server coverage where the behavior requires it; static source assertions alone are insufficient.
10. Update the Pi README to state the verified pre-connect behavior and failure semantics.
11. Remove only the completed pre-connect-list entry from `TODO.md` after implementation and acceptance evidence; leave unrelated TODO entries unchanged.
12. If reproduction shows current runtime behavior already meets every requirement, avoid production-code churn: add missing regression/live coverage, align documentation, and remove the stale TODO only after the end-to-end acceptance passes.

## Acceptance criteria

- `/inter-agent list` succeeds before Pi connects when the configured server is reachable.
- Empty and populated results are intentional and correctly rendered.
- Unavailable/auth/TLS/command/malformed failures remain distinguishable from an empty bus and produce bounded actionable diagnostics.
- List causes no listener or connection-state transition and does not auto-start a server.
- Behavior remains consistent after Pi connects.
- Focused tests, Pi type/build/format checks, live acceptance, and the full repository gate pass.
- `git diff --check` is clean and only allowed files are modified.

## Checks

Run at minimum:

```bash
uv run pytest tests/test_pi_extension_static.py tests/test_pi_adapter_cli.py tests/integration/test_pi_adapter_live.py -q
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check src/index.ts README.md package.json
./run-checks.sh
git diff --check
```

## End-to-end acceptance test

Using the locally installed Pi extension and an isolated configured server:

1. Start the server without connecting the Pi listener.
2. Invoke `/inter-agent list` through Pi and observe an intentional empty success.
3. Connect a separate uniquely named agent session, invoke Pi list again before Pi connects, and observe that session.
4. Confirm the Pi listener was not started and Pi connection state was not changed by either list operation.
5. Connect Pi, invoke list again, and confirm consistent populated behavior.
6. Exercise server-unavailable and authentication-failure configurations and confirm each reports a bounded failure rather than an empty success.
7. Feed malformed helper success output through the Pi command path and confirm the invalid-response diagnostic.

If interactive Pi cannot run in the environment, use a bounded process-level harness that loads the built extension, invokes the registered `list` command before its listener starts, and observes the real helper/server boundary. Record the exact limitation; direct helper success or static assertions alone are not sufficient acceptance.

## Completion report

Record the reproduction, root cause (or evidence that the TODO was stale), exact changed files, empty/populated behavior, failure-path results, proof that listener/state did not change, checks, UAT method/results, environment limitations, TODO cleanup, and allowed-file confirmation. Do not commit.
