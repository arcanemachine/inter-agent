# Current integration reliability closeout

Status: concrete; items 5–7 are already ordered; item 5 is active

## Purpose

Preserve exact completion requirements for the three known reliability defects before mailbox, migration, or release work begins. This file does not replace the active item-5 packet.

## Item 5 — Pi disconnect reliability

The active packet is authoritative. Acceptance must prove that `/inter-agent disconnect`:

- waits for the owned listener process to exit rather than only sending SIGTERM;
- does not shut down the shared server;
- updates persisted and live state exactly once;
- emits intentional notifications without a later misleading connection-closed warning;
- releases the routing name so immediate reconnect under the same name succeeds;
- handles already-exited/no-listener cases idempotently;
- bounds waiting and escalates or reports failure without hanging Pi;
- cleans up on session shutdown.

## Item 6 — Pi pre-connect list behavior

Required behavior:

- `/inter-agent list` is a read-only short-lived authenticated diagnostic and never requires the Pi listener/current connection.
- If the configured server is reachable, pre-connect list succeeds and shows current agent sessions or an intentional empty result.
- If the server is unavailable, auth fails, TLS setup fails, or output is malformed, show the existing bounded actionable diagnostic; do not fabricate an empty list.
- Listing must not auto-connect an agent, start a listener, mutate state, or expose a new LLM tool beyond the already supported list tool.
- Add focused static/helper and live tests for reachable-empty, reachable-populated, unavailable, auth failure, malformed output, and no-listener gating absence.

End-to-end: against an already-running server, invoke Pi list before Pi connect, observe empty/populated success, then connect and confirm behavior remains consistent.

## Item 7 — Claude Code sandbox connect exit 127

Required investigation order:

1. Reproduce with the installed plugin/wrapper in the affected sandbox or the closest available isolated environment.
2. Record which runtime resolution branch is selected: explicit helper, configured `project_path`, managed venv, PATH, or setup-needed.
3. Distinguish missing helper, stale venv shebang, missing executable permission, unavailable Python/venv, plugin option propagation, PATH isolation, and sandbox process policy.
4. Fix repository-owned behavior only when evidence identifies it.
5. If the environment forbids required execution, document the verified constraint and an actionable supported setup; do not claim a code fix.

Preserve:

- wrapper resolution precedence;
- explicit approval for bootstrap;
- no declarative Monitor;
- shared endpoint/state defaults;
- short bounded diagnostics without tracebacks or secret values.

Tests must cover the reproduced failure path using isolated temporary directories and wrapper processes. Live installed-plugin acceptance is required when Claude CLI access supports it; otherwise record the exact unavailable capability.

## Combined gate

After items 5–7 are accepted:

- run Pi type/build/Prettier checks;
- run strict Claude marketplace and plugin validation;
- run focused live adapter tests;
- run `./run-checks.sh`;
- ensure `TODO.md` contains no resolved defects;
- ensure docs describe verified behavior only.

Do not activate mailbox/migration work until each defect is implemented, explicitly accepted as an environment constraint, or separately deferred by the user.
