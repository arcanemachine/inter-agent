# Released ecosystem acceptance and next promotion

Status: concrete; final important-action gate

## Goal

Prove that public released artifacts and the recursive public superproject deliver the complete current product without local monorepo assumptions, then close the program and promote OpenCode ahead of Codex.

## Test environments

Use isolated temporary HOME/config/state/cache directories and no development checkout helpers on PATH. Keep registry caches controlled so tests demonstrate installation rather than accidentally reusing editable/local packages.

Test both:

1. independent package installation from public registries/tagged repositories;
2. `git clone --recurse-submodules` of the public ecosystem superproject, using its documented orchestration.

## Required released-artifact matrix

### Installation and metadata

- PyPI core/helper names and versions match public docs.
- npm Pi package contents and version match docs.
- Claude marketplace/plugin metadata and tag match docs.
- no floating branch archive, local absolute path, private URL, or commit-hash README instruction.
- licenses/changelogs/security contacts are present in each public child.

### Core behavior

- server start/status/list/shutdown;
- auth success/failure;
- direct, broadcast, channels, diagnostics, limits, and publisher exclusion;
- generated-certificate and configured-certificate TLS paths;
- clean wheel/sdist import and every generic CLI.

### Pi behavior

- npm and tagged-Git installation;
- helper resolution without monorepo path;
- connect/list/status/send/broadcast/channel commands;
- queued mailbox default, selected/all reads, immediate mode, overflow/debounce automated coverage;
- disconnect and immediate same-name reconnect;
- pre-connect list intentional behavior;
- explicit TLS.

### Claude behavior

- tagged marketplace/plugin installation;
- approval-gated stable bootstrap and helper resolution;
- skill-driven Monitor with no declarative Monitor;
- direct/broadcast/channel commands and notifications;
- disconnect/reconnect and sandbox/setup diagnostics;
- explicit TLS.

### Cross-host and state

- Pi-to-Claude and Claude-to-Pi direct delivery;
- cross-host broadcast and pub/sub in both directions;
- channel diagnostics and publisher exclusion;
- separate runtime installs share the default endpoint/state;
- explicit shared endpoint/state across isolated homes works with a shared high-entropy secret;
- intentional endpoint/state separation prevents cross-bus delivery;
- no secret appears in output/logs.

## Recursive superproject acceptance

- submodules initialize at expected paths and are clean;
- root check script runs child gates without modifying children;
- relative documentation links resolve;
- compatibility table names the tested semantic versions;
- individual child links/install paths work independently;
- no OpenCode/Codex submodule is present before implementation.

## Documentation closeout

Update public docs to released present tense only after acceptance. Private meta records:

- exact observed checks and environment limitations;
- release/tag/package versions;
- final roadmap completion state;
- remaining accepted next direction.

Remove promoted/resolved idea files and stale temporary planning. Keep package-specific details in child docs and thin ecosystem links at the parent.

## Failure policy

A failed released artifact is not patched in place. Determine owning child, add regression coverage, increment the affected version, republish through its gated plan, update the superproject pin/compatibility table, and rerun the complete affected matrix. Do not declare partial success as ecosystem completion.

## Completion and promotion

When every important item is complete:

1. clear `.agents/PLAN.md` in private meta;
2. mark all important-closeout roadmap items implemented with release evidence;
3. archive/remove completed active packets according to workflow;
4. run final gates from clean clones;
5. prepare maintainer acceptance summary;
6. promote the OpenCode validation spike as the next active roadmap item only after user dispatch authorization;
7. keep Codex sequenced after OpenCode's accepted outcome.

## Non-goals

- No OpenCode or Codex implementation during this acceptance.
- No remote/multi-user security expansion.
- No automatic publication or version bump without the owning release gate.
