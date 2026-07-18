# Task 1 — Pi disconnect reliability

Status: active

## Goal

Make `/inter-agent disconnect` reliably stop the Pi listener process before reporting success, clear Pi connection state consistently, and allow the same routing name to reconnect immediately without intermittently remaining on the bus.

## Context

`TODO.md` records that Pi disconnect works only sometimes. The extension currently sends `SIGTERM`, immediately drops its `ChildProcess` reference and marks state disconnected, then reports success without observing process exit. Startup/rename also call the synchronous stop path and may start a replacement while the prior listener still owns its routing name/control socket. The child exit handler cannot distinguish expected stops from unexpected closure once the global reference is cleared.

## Allowed files to modify

- `integrations/pi/src/index.ts`
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`
- `TODO.md`
- `ROADMAP.md`

## Additional files allowed to read

- `integrations/pi/AGENTS.md`
- `integrations/pi/package.json`
- `integrations/pi/tsconfig.json`
- `src/inter_agent/adapters/pi/listener.py`
- `tests/integration/test_pi_adapter_live.py`
- `tests/test_pi_listener.py`

Do not read or modify other files without recording why this packet is insufficient.

## Non-goals

- No server shutdown from disconnect.
- No Python listener, protocol, auth, TLS, pub/sub, send, broadcast, list, or status behavior changes.
- No Pi pre-connect list fix; that is item 6.
- No reconnect policy redesign or new dependency.
- No detached/background process management outside the extension-owned child.

## Requirements

1. Replace fire-and-forget listener termination with an awaitable lifecycle that observes the exact child process exiting.
2. On explicit stop, mark in-memory listener state unavailable immediately so no command can use the terminating listener.
3. Send `SIGTERM` first and wait a bounded interval for `exit`/`close`.
4. If the child does not exit within the bound, send `SIGKILL` and wait a final bounded interval. Report failure rather than claiming disconnection if termination still cannot be observed.
5. Handle already-exited or absent listeners idempotently.
6. Ensure stale events from an old child cannot clear or overwrite a newer listener's state.
7. Distinguish expected explicit stops from unexpected listener exits so disconnect/rename/session shutdown do not produce misleading reconnect warnings.
8. Await termination before starting a replacement listener during connect/rename and before completing `session_shutdown`.
9. `/inter-agent disconnect` must await the stop result, persist/update disconnected state, and notify success only after observed termination (or when no listener exists). Surface a bounded error notification on failure.
10. Preserve existing unexpected-exit state cleanup and reconnect guidance.
11. Keep disconnect from invoking server `shutdown`.
12. Update documentation to state that disconnect waits for listener exit and permits immediate same-name reconnect.
13. Remove only the completed disconnect TODO after implementation and acceptance; leave the other TODO entries unchanged.
14. Add focused static coverage for the awaitable stop, bounded TERM→KILL sequence, awaited callers, expected-stop handling, state updates, success/failure notifications, and absence of server shutdown.
15. Keep changes behavior-focused and avoid unrelated Pi formatting churn beyond the formatter's required output.

## Acceptance criteria

- Repeated connect/disconnect cycles release the routing name reliably.
- Disconnect success is not reported before child exit is observed.
- Rename/connect never overlap old and new listener children.
- Session shutdown waits for owned listener termination.
- Unexpected exits still clear state and provide reconnect guidance.
- Focused tests, Pi type/build/format checks, live process UAT, and the full repository gate pass.
- `git diff --check` is clean and only allowed files are modified.

## Checks

Run at minimum:

```bash
uv run pytest tests/test_pi_extension_static.py -q
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check src/index.ts README.md package.json
./run-checks.sh
git diff --check
```

## End-to-end acceptance test

Using the locally installed Pi extension and runtime:

1. Start Pi with the extension and connect a unique name.
2. Verify the name appears from another bus client.
3. Run `/inter-agent disconnect` and observe the success notification only after the listener exits.
4. Verify the name disappears from the bus.
5. Immediately reconnect with the same name and confirm no `NAME_TAKEN` retry/failure.
6. Repeat the disconnect/reconnect cycle at least three times.
7. Confirm the server remains available after disconnect.

If interactive Pi cannot run in the environment, create a bounded process-level acceptance harness around the same extension child lifecycle and record the exact limitation; static assertions alone are not sufficient acceptance for this reliability item.

## Completion report

Record changed files, observed process/reconnect behavior, exact checks, UAT method/results, environment limitations, TODO cleanup, and allowed-file confirmation.
