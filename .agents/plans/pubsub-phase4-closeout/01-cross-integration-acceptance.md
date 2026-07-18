# Task 1 — Pub/sub Phase 4 closeout

Status: active

## Goal

Close pub/sub Phase 4 by proving Pi and Claude adapter interoperability on the same live server, validating both installed integration surfaces and packages, aligning evergreen documentation, and marking Phase 4 implemented only after the whole repository gate passes.

## Context

Core protocol and APIs (Phases 1–2), Python adapters (Phase 3), and installed Pi/Claude user UX slices (Phase 4) are implemented. Existing live tests validate each adapter independently. This closeout adds a focused cross-adapter live test and runs the complete local acceptance matrix; it does not add product behavior.

## Allowed files to modify

- `tests/integration/test_cross_adapter_pubsub_live.py` (new)
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ROADMAP.md`
- `docs/plans/pubsub-channels/00-design-seed.md`
- `integrations/pi/README.md`
- `integrations/claude-code/README.md`

## Additional files allowed to read

- `tests/conftest.py`
- `tests/integration/test_pi_adapter_live.py`
- `tests/integration/test_claude_adapter_live.py`
- `src/inter_agent/adapters/pi/listener.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/commands.py`
- `tests/test_pi_extension_static.py`
- `tests/test_claude_skill_static.py`
- `tests/test_pi_listener.py`
- `tests/test_claude_listener.py`

Do not read or modify other files without recording why this packet is insufficient.

## Non-goals

- No protocol, server, core API, adapter, extension, skill, wrapper, package, or behavior changes.
- No new pub/sub operation or semantic change.
- No interactive host automation that depends on credentials or unavailable harness UI.
- No OpenCode, Codex, release, PyPI, repository-split, or TODO-defect work.

## Requirements

1. Add a focused live test running Pi and Claude listeners against one `LiveServer`.
2. Use distinct routing names and shared endpoint/auth configuration.
3. Prove a channel delivery published with the Claude adapter reaches a subscribed Pi listener with correct `from_name`, `channel`, and text.
4. Prove a channel delivery published with the Pi adapter reaches a subscribed Claude listener with correct channel metadata, sender, and text.
5. Prove publisher exclusion or otherwise preserve it through focused existing live assertions without weakening either adapter's established output conventions.
6. Exercise channel diagnostics from both adapters on the shared server and verify both subscribers appear.
7. Unsubscribe/stop listeners reliably in cleanup; avoid fixed ports and timing-only success where bounded readiness polling is practical.
8. Keep the test scoped to adapter interoperability. Installed UI dispatch/policy remains covered by the static suites already added in items 1–3.
9. Review README, ARCHITECTURE, SECURITY, both integration READMEs, ROADMAP, and the design seed for stale prospective/partial wording.
10. Mark Phase 4 implemented only after cross-adapter live acceptance, static installed-surface coverage, strict Claude validation, Pi type/build/format checks, spec/conformance coverage, and `./run-checks.sh` pass.
11. Record environment limitations if interactive authenticated Claude/Pi UI acceptance cannot run; do not substitute claims for observed checks.
12. Keep assertions behavior-focused and the worktree limited to allowed files.

## Acceptance criteria

- The cross-adapter live test passes and observes delivery in both directions on one server.
- Both adapters report the same active channel/subscriber state.
- Installed Pi and Claude static suites pass.
- Existing per-adapter live round trips pass.
- Strict Claude plugin validation passes.
- Pi typecheck, build, and Prettier checks pass.
- Full repository gate passes with spec/conformance coverage.
- Evergreen docs describe Phase 4 as implemented and name item 5 as the next closeout activation.
- `git diff --check` is clean.

## Checks

Run at minimum:

```bash
uv run pytest \
  tests/integration/test_cross_adapter_pubsub_live.py \
  tests/integration/test_pi_adapter_live.py::test_pi_subscribe_unsubscribe_publish_channels_round_trip \
  tests/integration/test_claude_adapter_live.py::test_claude_subscribe_unsubscribe_publish_channels_round_trip \
  tests/test_pi_extension_static.py \
  tests/test_claude_skill_static.py \
  -q
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check src/index.ts README.md package.json
claude plugin validate --strict integrations/claude-code
./run-checks.sh
git diff --check
```

## End-to-end acceptance test

Run the cross-adapter live test against one ephemeral server and observe both directions:

```bash
uv run pytest tests/integration/test_cross_adapter_pubsub_live.py -q
```

Interactive Pi/Claude UI acceptance is supplementary. If both authenticated interactive hosts are available, connect one session from each host, subscribe both to a unique channel, publish in each direction, list channels from each installed command, then unsubscribe and confirm empty diagnostics. Otherwise record the exact environment limitation and rely on the cross-adapter live test plus installed-surface static/package validation.

## Completion report

Record changed files, observed two-way delivery/diagnostics, exact check results, documentation status, interactive limitations, allowed-file confirmation, and that no product behavior changed.
