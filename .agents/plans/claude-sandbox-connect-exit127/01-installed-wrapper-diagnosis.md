# Task 1 — Claude Code sandbox connect exit 127

Status: active

## Goal

Reproduce and resolve the installed Claude Code `/inter-agent connect` Monitor exit-127 failure reported in the interline sandbox, or document a verified environment constraint with an actionable supported setup when repository-owned behavior cannot overcome it.

## Context

`TODO.md` records that `/inter-agent connect` always appears to fail with `Monitor "inter-agent bus messages" script failed (exit 127)` in the interline sandbox. The accepted investigation order and preserved behavior are defined in `docs/plans/important-closeout/03-reliability-closeout.md` (item 7).

The installed skill runs its bundled `skills/inter-agent/bin/inter-agent-claude` wrapper. That wrapper resolves the runtime helper in this order: explicit `INTER_AGENT_CLAUDE_HELPER`, plugin `project_path`, managed venv, then PATH; absent a usable helper it intentionally exits 127 with setup guidance. Connect uses a persistent Monitor invoking `listen --name <name>`. Determine which exact branch and process condition produces the reported exit before changing behavior.

## Allowed files to modify

- `integrations/claude-code/skills/inter-agent/bin/inter-agent-claude`
- `integrations/claude-code/skills/inter-agent/bin/bootstrap-runtime`
- `integrations/claude-code/skills/inter-agent/SKILL.md`
- `integrations/claude-code/skills/inter-agent/bootstrap.md`
- `integrations/claude-code/README.md`
- `integrations/claude-code/.claude-plugin/plugin.json`
- `tests/test_claude_wrapper.py`
- `tests/test_claude_skill_static.py`
- `tests/test_claude_plugin_static.py`
- `tests/integration/test_claude_adapter_live.py`
- `TODO.md`

## Additional files allowed to read

- `.claude-plugin/marketplace.json`
- `src/inter_agent/adapters/claude/cli.py`
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/state.py`
- `tests/test_claude_adapter_cli.py`
- `tests/test_claude_listener.py`
- `docs/plans/important-closeout/03-reliability-closeout.md`

Do not read or modify other files without reporting why this packet is insufficient. Do not expose secrets, plugin credentials, or private environment values in output, tests, documentation, or the completion report.

## Non-goals

- No protocol, server, shared endpoint/state default, auth, TLS-policy, routing, listener reconnect, pub/sub, or packaging/repository-extraction redesign.
- No declarative Monitor and no second listener launch path.
- No silent bootstrap, dependency installation, or bypass of explicit user approval.
- No change to runtime-resolution precedence without evidence that the accepted precedence itself causes the defect.
- No claim that an environment constraint is resolved without installed-path evidence.
- No broad support for arbitrary sandbox process restrictions.
- No external publication, credentials, remote changes, or repository migration.
- No unrelated Claude or Pi changes.

## Requirements

1. Reproduce the failure with the installed Claude plugin/wrapper in the affected sandbox when available, otherwise in the closest isolated environment that preserves installed plugin paths, configuration injection, HOME/PATH isolation, executable bits, shebang behavior, and Monitor-style invocation.
2. Record the exact runtime-resolution branch selected: explicit helper, configured `project_path`, managed venv, PATH helper, or setup-needed.
3. Distinguish with evidence among: missing helper; invalid configured path; stale or broken venv shebang/interpreter; missing executable permission; missing Python or venv support; plugin option propagation failure; PATH isolation; bundled wrapper permission/shebang failure; and sandbox process/Monitor policy.
4. Inspect both the wrapper's own exit and the selected helper's exit. Do not label every exit 127 as "helper missing" when the wrapper or helper can exist but fail to execute.
5. Preserve resolution precedence and the exact configured helper override semantics unless reproduction proves a repository-owned defect requiring a narrowly scoped correction.
6. Preserve plugin `secret` propagation as `INTER_AGENT_SECRET`; diagnostics must never print secret values.
7. Preserve explicit approval before bootstrap. Setup-needed output must remain short, actionable, and point to packaged setup guidance without a traceback.
8. Preserve the single skill-driven persistent Monitor and the instruction not to run `listen` manually in Bash. Do not add a declarative Monitor.
9. If repository-owned behavior is defective, add regression tests before implementing the narrow fix. Cover the reproduced branch using isolated temporary directories and real wrapper subprocesses, including exit code and bounded stderr.
10. Add focused coverage as applicable for configured helper, managed helper, PATH helper, missing helper, non-executable helper, stale shebang/interpreter, plugin option propagation, executable wrapper assets, and bootstrap prerequisites/approval.
11. Exercise the selected helper's real `listen --name <name>` path against an isolated server when the environment supports it; confirm a connected line and absence of an unintended duplicate listener.
12. If the environment forbids the required execution and repository behavior is correct, document the verified constraint and a supported actionable setup. Do not make speculative code changes merely to remove exit 127.
13. Update installed skill/bootstrap/README guidance only to reflect verified behavior and the supported recovery path.
14. Remove only the completed Claude Code exit-127 TODO after a repository fix or verified environment-constraint acceptance; leave unrelated TODO entries unchanged.
15. Keep all changes inside the allowed-file boundary and avoid unrelated formatting churn.

## Acceptance criteria

- The exact exit-127 source and selected resolution branch are demonstrated, not inferred.
- A repository-owned defect is fixed with isolated wrapper/process regression coverage, or an environment constraint is documented with evidence and an actionable supported setup.
- Supported installed connect reaches the real helper listener and emits a connected/already-connected line.
- Resolution precedence, secret handling, explicit bootstrap approval, single-Monitor behavior, and shared defaults remain intact.
- Failures are bounded, actionable, traceback-free, and secret-free.
- Focused wrapper/plugin/adapter tests, installed-path acceptance where available, and the full repository gate pass.
- `git diff --check` is clean and only allowed files are modified.

## Checks

Run at minimum:

```bash
uv run pytest tests/test_claude_wrapper.py tests/test_claude_skill_static.py tests/test_claude_plugin_static.py tests/integration/test_claude_adapter_live.py -q
./run-checks.sh
git diff --check
```

Also run strict Claude plugin/marketplace validation when the installed Claude CLI provides it. Record the exact command and result, or the exact missing capability.

## End-to-end acceptance test

Prefer the affected interline sandbox:

1. Record the installed plugin source and wrapper path without printing secrets.
2. Invoke `/inter-agent connect <unique-name>` through the installed skill and capture the Monitor's bounded output and exit status.
3. Record which resolution branch was selected and verify the selected helper path, executability, shebang/interpreter availability, and plugin option propagation.
4. Apply the repository fix or supported configuration/bootstrap recovery.
5. Retry connect and observe `[inter-agent] connected as "<name>"` or the intentional already-connected line from the real listener.
6. Confirm the listener appears on the bus and only one listener was launched.
7. Disconnect cleanly.

If the affected sandbox is unavailable, create an isolated installed-plugin harness with a temporary HOME and controlled PATH/config/runtime directories. Exercise each relevant resolution branch as real subprocesses, reproduce the exit-127 condition, and then prove the corrected/supported path starts the real listener against an isolated server. Record why this is the closest available substitute; unit mocks alone are insufficient.

## Completion report

Report the reproduction environment, exact resolution branch, root cause evidence, changed files, fix or verified constraint, installed/process UAT, plugin validation, exact focused/full checks, environment limitations, TODO decision, secret-safety confirmation, and allowed-file confirmation. Do not commit.
