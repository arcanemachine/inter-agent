# Task 1 — Pi startup inter-agent identity flag

Status: active

## Goal

Allow a user to assign and connect a Pi worker's inter-agent routing name at process startup with:

```bash
pi --inter-agent <name>
```

The flag must reuse the existing Pi extension connection path and leave Pi usable when connection setup fails.

## Context

The user promoted this narrow capability ahead of queued mailbox work. Pi's supported extension API provides string-valued CLI flags through `pi.registerFlag()`. Registered flag values are available from `pi.getFlag()` at `session_start`, not during the extension factory. The current Pi extension already owns server discovery/auto-start, listener launch, name validation feedback, connection state, reconnect, auth/TLS configuration, notifications, and shutdown.

This is closeout priority insertion 7a. Item 8, Pi queued mailbox, remains next after this packet is accepted.

## Allowed files to modify

- `integrations/pi/src/index.ts`
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`

## Additional files allowed to read

- `integrations/pi/AGENTS.md`
- `integrations/pi/package.json`
- `integrations/pi/tsconfig.json`
- `tests/integration/test_pi_adapter_live.py`
- `docs/plans/important-closeout/01-pi-queued-mailbox.md`

Do not read or modify other files without reporting why this packet is insufficient. Do not expose shared secrets or private environment values in output, tests, documentation, or the completion report.

## Non-goals

- No protocol, core, Python adapter/helper, server, auth, TLS, endpoint-default, listener-reconnect, pub/sub, or packaging redesign.
- No queued mailbox or delivery-mode implementation; that remains item 8.
- No new settings key, environment variable, persisted startup preference, label syntax, or slash-command behavior.
- No automatic send, broadcast, publish, subscribe, read, reply, or model turn.
- No change to Pi session display names or Pi's built-in `/name` behavior.
- No external publication, credentials, remote changes, or repository migration.
- No unrelated formatting or documentation churn.

## Requirements

1. Register exactly one string-valued Pi extension flag named `inter-agent`, producing the installed syntax `pi --inter-agent <name>`.
2. Read the flag through `pi.getFlag("inter-agent")` only after Pi exposes CLI values at `session_start`.
3. Treat a present, non-empty flag as the explicit desired inter-agent routing name for that Pi process/session runtime. Do not interpret it as a label, Pi display name, message, or configuration path.
4. On every `session_start` reason in the same Pi process (`startup`, `reload`, `new`, `resume`, or `fork`), prefer the explicit flag name over transcript-restored inter-agent connection state. This keeps the worker identity effective after Pi replaces or reloads the extension session.
5. Reuse the existing connect path for argument handling, server discovery/auto-start, helper resolution, listener replacement, auth/TLS propagation, connection state, status, and notifications. Do not introduce a second launch path or duplicate listener.
6. Preserve existing behavior when the flag is absent. Existing transcript-restored reconnect remains unchanged in that case.
7. A malformed, blank, rejected, duplicate, unavailable-runtime, auth, or server-start failure must produce the existing bounded actionable feedback and leave Pi running. Do not throw from `session_start`, abort Pi, expose a traceback, or trigger a model turn.
8. A successful listener welcome remains the authority for connected state. Do not claim readiness before the existing listener path receives it.
9. Existing `/inter-agent connect`, `rename`, and `disconnect` behavior remains available after startup. An in-session command may change the current connection; the process flag is reapplied only on a later `session_start` lifecycle event.
10. Do not rewrite Pi settings or add durable state beyond the current connection-state behavior already owned by the extension.
11. Document the exact installed syntax, automatic connection behavior, precedence over restored state, reapplication on session replacement/reload, nonfatal failure behavior, and unchanged behavior when omitted.
12. Add focused regression coverage before or with the implementation. At minimum cover exact flag registration/type, deferred `session_start` lookup, flag precedence over restored state, reuse of the existing connect path, and unchanged no-flag reconnect behavior. Static assertions may cover API/surface boundaries; real installed-path UAT must prove behavior.
13. Keep all changes inside the allowed-file boundary.

## Acceptance criteria

- `pi --inter-agent worker-a` is accepted when the installed extension is loaded and starts the existing listener as `worker-a`.
- The connected worker appears on the real bus under that routing name and uses the existing configured endpoint/auth/TLS behavior.
- The explicit flag wins over a different restored connection name at session start.
- Reload or session replacement reconnects using the flag name without leaving duplicate listeners.
- A failed connection is bounded and nonfatal; Pi remains usable.
- Omitting the flag preserves current startup/reconnect behavior.
- Existing slash commands remain usable and no autonomous messaging/model turn is introduced.
- Focused checks, installed Pi acceptance, and the full repository gate pass.
- `git diff --check` is clean and only allowed files are modified.

## Checks

Run at minimum:

```bash
uv run pytest tests/test_pi_extension_static.py -q
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check src/index.ts README.md
./run-checks.sh
git diff --check
```

Also record the installed Pi version used for acceptance and confirm its extension API accepts the registered string flag.

## End-to-end acceptance test

Use an installed Pi package when available; otherwise report the limitation and use Pi's supported explicit extension loading as the closest substitute.

1. Start an isolated real inter-agent server without printing its secret or private configuration.
2. Launch Pi with a unique routing name using `pi --inter-agent <unique-name>` and keep the process/session open.
3. Confirm the flag is accepted, the normal bounded connecting/connected UI appears, and the unique name appears in a real bus `list`/identity observation.
4. Confirm only one listener/session exists for that Pi worker.
5. Exercise `/reload` or one session-replacement flow and confirm the same flag name reconnects after the old listener exits, without overlap or a duplicate session.
6. Use an in-session inter-agent rename or disconnect command and confirm the existing command still works.
7. Exercise one bounded failure (for example a duplicate valid name or unavailable isolated endpoint) and confirm Pi remains open and usable with no traceback or autonomous model turn.
8. Launch Pi without `--inter-agent` and confirm it does not create a new connection unless existing restored-state semantics call for one.
9. Exit cleanly and confirm the listener/session is removed.

Record observed commands and results without exposing secret values. Written steps alone are not acceptance evidence.

## Completion report

Report changed files, exact flag semantics, precedence/lifecycle behavior, focused checks, full gate, installed Pi version/path, real bus observations, reload/session-replacement result, bounded-failure result, environment limitations, secret-safety confirmation, and allowed-file confirmation. Do not commit.
