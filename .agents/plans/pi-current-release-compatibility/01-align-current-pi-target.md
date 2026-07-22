# Task 1 — Align the Pi integration with the current stable release

Status: ready for dispatch

## Goal

Make the Pi integration develop, typecheck, package, and pass installed acceptance against the current stable Pi distribution instead of the deprecated pre-fork package line, without changing inter-agent product semantics or absorbing later kick, reload-continuity, compaction, TLS, or repository-extraction work.

## Context

Closeout item 8 was accepted in `7c208d2`. At activation, the installed `pi` executable and the published `@earendil-works/pi-coding-agent` release are 0.81.1, while `integrations/pi/package.json` still develops against deprecated `@mariozechner/pi-coding-agent` 0.72.1. The old registry line currently ends at 0.73.1 and its lockfile metadata directs consumers to `@earendil-works`.

The current extension runs under Pi 0.81.1, but its TypeScript contract is not checked against that host. The current host package also uses `@earendil-works/pi-tui`, `typebox`, and the supported `agent_settled` event. This task establishes one explicit current-release baseline before additional Pi behavior is added.

Re-query the published stable `@earendil-works/pi-coding-agent` version at task start. Use that current stable release if it has advanced, and report the exact resolved version. Do not target an arbitrary historical 0.80 release or retain deprecated packages merely because they still compile.

## Allowed files to modify

- `package.json`
- `integrations/pi/package.json`
- `integrations/pi/package-lock.json`
- `integrations/pi/src/index.ts`
- `integrations/pi/src/mailbox.ts`
- `integrations/pi/tests/mailbox.test.ts`
- `integrations/pi/tests/extension-mailbox.test.ts`
- `integrations/pi/tsconfig.json`
- `integrations/pi/tsconfig.test.json`
- `integrations/pi/README.md`
- `tests/test_pi_extension_static.py`

Modify only the minimum subset required. Do not change versions of the inter-agent product itself.

## Additional files allowed to read

- `AGENTS.md`
- `integrations/pi/AGENTS.md`
- `integrations/pi/.gitignore`
- the current installed and published `@earendil-works/pi-coding-agent`, `@earendil-works/pi-tui`, and `typebox` package metadata, extension API declarations, changelog sections, extension documentation, and official extension examples needed for migration
- the deprecated package metadata only to verify migration/deprecation facts
- `tests/test_pi_listener.py`
- `tests/integration/test_pi_adapter_live.py`
- `src/inter_agent/adapters/pi/listener.py`
- `src/inter_agent/adapters/pi/commands.py`

Do not traverse or print dependency trees or `node_modules`. Read only explicit package metadata, declarations, documentation, and examples needed for the bounded migration. Do not expose credentials, private environment values, registry tokens, or UAT marker bodies.

## Non-goals

- No new inter-agent command, tool, protocol operation, delivery mode, mailbox persistence, compaction behavior, TLS behavior, transport, auth, server, Python adapter/helper, channel, or Claude Code feature.
- No effective-kick implementation; that remains closeout item 8b.
- No same-process reload mailbox handoff; that remains item 8c.
- No compaction continuity repair; that remains item 8d.
- No repository extraction, package publication, global package installation/update, credential use, remote changes, or version bump for `pi-inter-agent`.
- No broad dependency refresh. Change only Pi lineage packages, their required schema package, and lockfile transitive changes produced by that migration.
- No compatibility shim for both deprecated and current Pi package names unless current installed/package acceptance proves it necessary and the leader approves the demonstrated deficiency.

## Requirements

1. At task start, record without printing unrelated registry configuration:
   - `pi --version`;
   - installed package name/version;
   - `npm view @earendil-works/pi-coding-agent version`.
   Stop and report if the installed host cannot exercise the published stable target.
2. Replace deprecated `@mariozechner/pi-coding-agent` and `@mariozechner/pi-tui` development, peer, source-import, and root-package references with the current `@earendil-works` packages.
3. Replace `@sinclair/typebox` with the current host-compatible `typebox` package and official import form. Keep schema dependencies in the correct production/development sections for both root git installation and nested package development.
4. Set a meaningful supported peer range anchored at the chosen current stable Pi baseline rather than `*`. Keep peer dependencies optional if that remains necessary for Pi host-provided packages and root git installation.
5. Update `integrations/pi/package-lock.json` through the package manager. The lockfile must resolve the selected current Pi line and contain no remaining deprecated `@mariozechner/pi-*` packages.
6. Compile the extension and package-local behavior tests directly against the selected current Pi declarations. Do not use path aliases, copied declarations, `skipLibCheck`, `any`, or casts merely to hide migration errors.
7. Use current supported lifecycle APIs. In particular, evaluate the item-8 deferred `agent_end` workaround against current `agent_settled`, whose contract fires only after retries, compaction, and queued continuations are finished. Prefer the current event and remove obsolete settlement scheduling if behavior remains generation-safe and tests prove the same bounds. Do not redesign mailbox semantics.
8. Preserve all accepted item-8 behavior:
   - queued default and session-only immediate override;
   - metadata-only queued notices and explicit reads;
   - 128-entry bound, order, overflow, malformed/duplicate diagnostics;
   - direct/broadcast/channel formatting;
   - at most one later trigger per waiting burst;
   - no delivery before the run and queued continuations fully settle;
   - listener reconnect preservation and current reload-clearing boundary;
   - no steering, abort, automatic send, or body leakage.
9. Preserve startup identity, command/tool surfaces, transport/auth/TLS propagation, listener lifecycle, helper resolution, pub/sub, renderer behavior, and shared defaults.
10. Update Pi README dependency/support wording only where the current package line or minimum supported host must be stated. Do not add temporary migration notes or unrelated documentation churn.
11. Update static and behavior tests so they assert the current package/schema names and current settlement integration without replacing behavior coverage with source-string assertions.
12. Keep generated `dist/` and `dist-tests/` output out of the final worktree. Do not commit.

## Acceptance criteria

- Project and nested package metadata consistently target the same current stable `@earendil-works` Pi line.
- Source imports and tool schemas use the current official packages and typecheck without suppressions.
- The lockfile contains no deprecated `@mariozechner/pi-*` packages.
- Settlement behavior uses current supported semantics and retains item-8 timing, generation, trigger, and body-secrecy guarantees.
- Root git installation and nested package development both resolve runtime/schema requirements correctly.
- Installed current-Pi acceptance covers startup identity, connect/listener behavior, queued notice/read, immediate delivery, disconnect, and clean shutdown.
- No unrelated product behavior or future closeout item is implemented.
- Every focused/package/full check passes, generated output is removed, `git diff --check` is clean, and only allowed files changed.

## Checks

Run at minimum:

```bash
pi --version
npm view @earendil-works/pi-coding-agent version
npm --prefix integrations/pi install
npm --prefix integrations/pi test
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
cd integrations/pi && npx prettier --check "src/**/*.ts" "tests/**/*.ts" README.md package.json package-lock.json tsconfig.json "tsconfig*.json"
uv run pytest tests/test_pi_extension_static.py tests/test_pi_listener.py tests/integration/test_pi_adapter_live.py -q
./run-checks.sh
git diff --check
```

Also inspect the lockfile with a Git-aware search limited to `integrations/pi/package-lock.json` and prove no `@mariozechner/pi-` dependency remains. Do not search or print `node_modules`.

Remove `integrations/pi/dist/` and `integrations/pi/dist-tests/` after verification.

## End-to-end acceptance test

Use the installed current stable Pi executable and an isolated real inter-agent server. Use controlled unique markers only in temp transcripts/assertions and remove them afterward; never print secrets or marker bodies.

1. Confirm the installed Pi package name/version equals the selected current stable target.
2. Start two real Pi sessions with the repository extension explicitly loaded and unique startup identities.
3. Confirm both listeners register once without overlap and pre-connect/list/status behavior remains bounded.
4. Send a queued direct message. Confirm a metadata-only notice triggers a turn, the body is absent before explicit `inter_agent_read_messages`, and selected read returns/removes it.
5. Exercise one broadcast or subscribed-channel delivery and confirm kind/format metadata remains correct and body-free before read.
6. Switch the receiver session to immediate and confirm a future body arrives through body-bearing non-steering follow-up delivery without entering the mailbox.
7. While queued continuations exist, prove the current settlement event/path emits neither queued notice nor immediate body early and triggers at most once after full settlement; deterministic package coverage may supply this timing proof.
8. Disconnect both sessions and confirm their isolated server registrations disappear cleanly.
9. Verify all UAT tmux sessions/processes and temporary files are removed after first checking that no tmux clients are attached.

## Completion report

Report exact selected/installed Pi package versions, dependency and import migration, settlement API decision and evidence, changed files, lockfile deprecation search, package/focused/full checks, installed UAT observations, cleanup, environment limitations, allowed-file confirmation, and secret safety. Do not commit.
