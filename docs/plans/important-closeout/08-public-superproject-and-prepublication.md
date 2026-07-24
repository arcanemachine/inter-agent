# Public ecosystem superproject and pre-publication acceptance

Status: concrete; queued after all three child extractions

## Goal

Create the public `arcanemachine/inter-agent` collector repository with real submodules and prove the extracted packages work together before any registry publication.

## Required structure

```text
inter-agent/
├── .gitmodules
├── README.md
├── ARCHITECTURE.md              # ecosystem overview, not duplicated child internals
├── COMPATIBILITY.md             # compatible released/candidate versions
├── LICENSE.md
├── core/                        # inter-agent-core submodule
├── extensions/pi/               # inter-agent-pi submodule
├── extensions/claude-code/      # inter-agent-claude-code submodule
└── scripts/                     # thin orchestration/check helpers
```

The repository contains no copied runtime source. Submodule URLs use stable canonical public remotes. Gitlinks pin the tested source set; README prose uses relative/canonical links, not commit hashes.

## User experience

Support:

```bash
git clone --recurse-submodules <ecosystem-url>
```

Also document recovery for an ordinary clone:

```bash
git submodule update --init --recursive
```

The README explains:

- what core, Pi, and Claude packages do;
- install-everything/development workflow from the recursive checkout;
- independent child installation links;
- stable released sources versus source-checkout development;
- shared endpoint/state interoperability;
- where package-specific docs, issues, security reports, and changelogs live.

## Thin orchestration

Root scripts may:

- confirm submodules are initialized;
- create isolated test environments;
- run each child's documented gate;
- run cross-repository interoperability acceptance.

They must not duplicate child build logic, rewrite child files, install silently outside explicit commands, or become a runtime dependency.

## Compatibility record

`COMPATIBILITY.md` records semantic package/plugin versions and protocol compatibility, not raw submodule hashes copied from Git. Before releases exist it may identify candidate versions and state that Git pins the exact tested source internally.

Each child versions independently after initial coordinated `0.1.0`. Updating a submodule requires running the cross-repository gate and updating compatibility notes when the supported version set changes.

## Pre-publication dependency strategy

Use local built artifacts or explicit path sources only inside isolated acceptance environments:

- core candidate wheel;
- Pi helper candidate wheel + npm pack tarball;
- Claude helper candidate wheel + plugin checkout.

Do not leave local absolute paths or editable dependencies in release metadata/lockfiles.

## Required acceptance matrix

From a clean recursive clone:

1. child package-local gates all pass;
2. core candidate installs without host assets;
3. Pi and Claude helpers install against the same core candidate;
4. Pi and Claude exchange direct/broadcast/channel messages on defaults;
5. Pi mailbox behavior passes;
6. explicit TLS cross-adapter matrix passes;
7. disconnect/reconnect and pre-connect diagnostics pass;
8. separate runtime installs share one bus by default;
9. explicit endpoint/state isolation prevents cross-bus delivery;
10. artifact inspections find no private workflow or unrelated package source.

## Public/private boundary

Public superproject docs are stable and user-oriented. Do not copy `.agents/**`, internal packets, maintainer private AGENTS rules, credential instructions, migration scratch, or chat/session history. Link child public docs rather than duplicating thick package documentation.

## Checks

- `git submodule status --recursive` shows initialized expected children.
- Root orchestration exits nonzero on missing/wrong child or failed child gate.
- `git diff --check` and link/path validation pass.
- Cross-repository tests run from isolated temporary state.
- No child worktree is dirtied by root acceptance.

## Non-goals

- No registry publication.
- No root aggregate runtime package.
- No floating branch downloads as release installation.
- No OpenCode/Codex submodules until those products are implemented and accepted later.
