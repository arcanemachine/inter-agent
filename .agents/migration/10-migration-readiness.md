# Item 10 migration-readiness record

Status: leader analysis in progress; physical migration not authorized

## Purpose

Record the verified source baseline, current repository/package facts, complete ownership mapping, recommended recovery procedure, and decisions required before physical repository migration.

This record contains no credentials or authenticated registry/hosting results. It does not authorize repository or ref creation, remote changes, history filtering, file moves, publication, or extraction.

## Intended topology

- Private maintainer repository: `arcanemachine/inter-agent-meta`.
- Public ecosystem repository: `arcanemachine/inter-agent`.
- Public children: `arcanemachine/inter-agent-core`, `arcanemachine/inter-agent-pi`, and `arcanemachine/inter-agent-claude-code`.
- Private meta contains the ecosystem repository as the `ecosystem/` submodule.
- The ecosystem repository contains child submodules at `core/`, `extensions/pi/`, and `extensions/claude-code/`.

## Verified source baseline

### Tested candidate

- Branch: `master`.
- Exact tested commit: `2ae2a72ee375514914c7c5cdbddf311a40fcd363`.
- Version represented by the tested manifests: `0.1.0`.
- The tested commit had no tag.
- The worktree remained clean after validation.

Observed gates:

- full repository gate: 510 tests passed;
- Ruff: passed;
- Black: 76 files unchanged;
- mypy: 75 source files passed;
- Pi tests: 71 passed;
- Pi typecheck, build, and Prettier: passed;
- root Claude marketplace validation: passed;
- Claude plugin validation: passed;
- `git diff --check`: passed.

The pre-existing ignored `integrations/pi/dist/` directory was preserved, and the generated `integrations/pi/dist-tests/` directory was removed.

### Current source state

- Current observed `HEAD`: `0caf5614b35d6097b753acb0481eaa8da12ef709`.
- Current `HEAD` is one commit after the tested candidate.
- The user identified that commit as an unrelated small tweak and asked that its content not be inspected during the baseline audit.
- Current `master` matched `origin/master` when inventoried.
- Current `HEAD` has not passed the complete gate recorded above.
- The current Claude plugin manifest has no version, while `tests/test_versioning_docs.py` requires its version to match `0.1.0`. The final freeze cannot use current `HEAD` until the intended version policy and test agree and the complete gate passes.

Approved direction: use the latest accepted `HEAD`, not its parent, as the eventual freeze source after the final gate passes. The exact prerelease version and tag mapping remains to be confirmed.

## Repository inventory

- Current remote names: `origin` only.
- Sanitized fetch/push destination: SSH transport to `github.com/arcanemachine/inter-agent.git`.
- Upstream: `master` tracks `origin/master`.
- The local `origin/HEAD` symbolic default-branch ref is unresolved.
- Local branches: `master` and `unstable`.
- Local tags: none.
- Submodules and `.gitmodules`: none.
- `git-filter-repo`: available locally.

### Stale branch

`unstable` is 68 commits behind `master` and has three commits not in `master`. Its unique changes affect an obsolete active-plan packet and Pi extension work.

Recommendation: preserve `unstable` in the full source backup, but do not propagate it into public child histories unless the user explicitly revives that work.

## Package inventory

| Boundary | Current identity | Migration disposition |
| --- | --- | --- |
| Root Python distribution | `inter-agent` `0.1.0` | Rename clean core distribution to `inter-agent-core` |
| Root Pi Git-install facade | `inter-agent-pi-package` `0.1.0`, private | Retire after Pi extraction |
| Nested Pi package | `pi-inter-agent` `0.1.0` | Rename canonical child npm package to `inter-agent-pi` |
| Claude marketplace | `inter-agent` `0.1.0` | Move to standalone Claude repository and rewrite source path |
| Claude plugin | `inter-agent`, currently without a version | Resolve coordinated-version policy before freeze |
| Python lock | editable `inter-agent` `0.1.0` | Rebuild for core; generate independent child locks |
| Pi lock | `pi-inter-agent` `0.1.0` | Move with Pi and update identity |

No registry ownership or current name availability was inferred from local metadata.

## Complete current-path ownership manifest

All 234 tracked paths were classified. Counts describe their primary current-source disposition before shared documents are rewritten or copied deliberately.

| Disposition | Count |
| --- | ---: |
| Private meta | 66 |
| Deferred host planning in private meta | 2 |
| Core | 109 |
| Pi | 20 |
| Claude Code | 22 |
| Public ecosystem | 3 |
| Shared/derived public material | 7 |
| Retire or rebuild | 5 |

### Private meta

Move with relevant path history:

- `.agents/**`;
- root `AGENTS.md`;
- `ROADMAP.md` and `TODO.md`;
- `docs/plans/**` and `docs/archive/**`;
- `docs/IDEAS.md`, `docs/IDEAS.USER.md`, and `docs/ideas/**`;
- deferred `integrations/opencode/**` and `integrations/codex/**` planning placeholders.

Public repositories receive curated public contribution material rather than copied private workflow.

### Core

Move with path history:

- `src/inter_agent/core/**`;
- `src/inter_agent/__init__.py`;
- `spec/**`;
- `tests/conformance/**`;
- core tests under `tests/`;
- `pyproject.toml`, `uv.lock`, `MANIFEST.in`, and `run-checks.sh`;
- `scripts/validate-release-build.py`;
- `docs/SECURITY_BASELINE.md` and `docs/THREAT_MODEL.md`.

Core-test ownership includes:

- `tests/conftest.py` as the primary source of shared core fixtures;
- `tests/test_auth_helpers.py`;
- `tests/test_client_helpers.py`;
- `tests/test_config_resolution.py`;
- `tests/test_core_command_api.py`;
- `tests/test_error_codes.py`;
- `tests/test_filesystem_permissions.py`;
- `tests/test_server_lifecycle_state.py`;
- `tests/test_spec_validation.py`;
- `tests/test_status_semantics.py`;
- `tests/test_tls_transport.py`;
- `tests/test_token_management.py`.

Split `tests/test_console_entry_points.py`: generic command coverage stays with core; Pi-specific entry-point coverage moves to Pi.

#### Shared adapter-control bridge

Promote:

```text
src/inter_agent/adapters/control.py
→ src/inter_agent/core/adapter_control.py
```

Move `tests/test_adapter_control.py` with it and document the promoted module as a narrow, host-neutral extension-support API.

Rationale: Pi and Claude use identical local control semantics and security constraints. Keeping one core-owned implementation avoids duplicated security-sensitive runtime logic without retaining host adapter packages in core.

### Pi

Move and rename with path history:

```text
integrations/pi/src/index.ts
→ src/index.ts

integrations/pi/src/mailbox.ts
→ src/mailbox.ts

integrations/pi/tests/**
→ tests/typescript/**

src/inter_agent/adapters/pi/**
→ src/inter_agent_pi/**
```

Move Pi-specific Python tests:

- `tests/test_pi_adapter_cli.py`;
- `tests/test_pi_extension_static.py`;
- `tests/test_pi_listener.py`;
- `tests/integration/test_pi_adapter_live.py`;
- the Pi-specific portion of `tests/test_console_entry_points.py`.

Use these nested files as the canonical child-root inputs:

- `integrations/pi/package.json` → `package.json`;
- `integrations/pi/package-lock.json` → `package-lock.json`;
- `integrations/pi/README.md` → `README.md`;
- `integrations/pi/LICENSE.md` → `LICENSE.md`;
- `integrations/pi/tsconfig.json` and `tsconfig.test.json` at the child root.

Retire the monorepo root Pi facade rather than mapping two package manifests to the same child path.

### Claude Code

Move and rename with path history:

```text
integrations/claude-code/.claude-plugin/plugin.json
→ .claude-plugin/plugin.json

integrations/claude-code/skills/**
→ skills/**

src/inter_agent/adapters/claude/**
→ src/inter_agent_claude/**
```

Move root `.claude-plugin/marketplace.json` into the Claude child and update its source for the validated standalone layout.

Move Claude-specific tests:

- `tests/test_claude_adapter_cli.py`;
- `tests/test_claude_dedup.py`;
- `tests/test_claude_listener.py`;
- `tests/test_claude_plugin_static.py`;
- `tests/test_claude_skill_static.py`;
- `tests/test_claude_wrapper.py`;
- `tests/integration/test_claude_adapter_live.py`.

Use `integrations/claude-code/README.md` as the child README seed and add independent helper-package metadata and tests.

### Public ecosystem

Preserve and rewrite as installed/candidate cross-repository acceptance:

- `tests/integration/test_cross_adapter_pubsub_live.py`;
- `tests/integration/test_cross_adapter_tls_live.py`;
- coordinated compatibility/version validation derived from `tests/test_versioning_docs.py`.

Create clean ecosystem-level README, architecture overview, `COMPATIBILITY.md`, license, submodule layout, and thin orchestration. Do not copy runtime source.

Recommendation: create the ecosystem repository with clean collector history rather than converting monorepo history into collector history. Preserve the source monorepo separately and retain relevant history in the filtered children.

### Shared and derived public material

- `README.md`: ecosystem seed; split core, Pi, and Claude sections into their owning children.
- `ARCHITECTURE.md`: core is canonical; derive a thin ecosystem overview and host-specific child sections.
- `SECURITY.md`: core is canonical; derive host-specific security sections for Pi and Claude.
- `CHANGELOG.md`: split release notes and version policy into core, Pi, and Claude changelogs.
- `LICENSE.md`: copy to every public repository.
- `.gitignore` and `.tool-versions`: rebuild per repository rather than copying monorepo assumptions.

Shared documentation may appear in more than one filtered history only when it is intentionally rewritten into package-owned public documentation.

### Retire or rebuild

Do not migrate directly as runtime files:

- root `inter-agent` monorepo wrapper;
- root transitional `package.json` Pi facade;
- empty `src/inter_agent/adapters/__init__.py`;
- `integrations/pi/AGENTS.md` private agent guidance;
- `tests/test_inter_agent_wrapper.py` tied to the retired monorepo wrapper.

Any useful ecosystem orchestration or public contributor guidance is written afresh for the target boundary.

## Recovery and isolated-filtering strategy

### Terminology

A **disposable filtering clone** is an isolated local clone used only for `git filter-repo` and mapping experiments. It is disposable because it can be regenerated from the verified source backup—not because its results are accepted without review.

Accepted extracted repositories are retained. Filtering clones and recovery material are not deleted until the user confirms the migration is complete and recoverable.

### Preconditions

1. Resolve the current plugin-version/test inconsistency.
2. Stop repository-editing agents for the maintenance window.
3. Confirm a clean current worktree.
4. Run the complete monorepo, Pi, and Claude gates against the intended final `HEAD`.
5. Record the exact accepted commit and version.
6. Obtain approval for the freeze ref name and physical migration.

### Source recovery set

In a temporary, namespaced migration workspace outside every repository checkout, retained through migration acceptance:

1. Create a full local Git bundle containing all refs, including `unstable`.
2. Verify the bundle with `git bundle verify` and record its SHA-256 digest privately.
3. Create a local mirror clone from the main checkout without contacting a remote.
4. Run `git fsck --full` against the mirror.
5. After authorization, create the approved annotated freeze tag/ref at the tested commit.
6. Record the source commit, ref, bundle digest, branch inventory, and verification results in private migration notes.

The bundle is the portable immutable recovery artifact during migration. The mirror is the convenient source for repeatable local clones. Neither is intended to remain permanently under `/workspace/tmp/`; retain them until the archived monorepo and accepted target repositories provide verified durable recovery, then remove them only with user confirmation.

### Filtering workspace

Create separate local clones from the verified mirror for:

- private meta history;
- core history;
- Pi history;
- Claude Code history.

Create the public ecosystem as a clean collector repository after child histories are accepted.

For every filtered child:

1. start from the accepted freeze branch/ref rather than every source branch;
2. apply only the reviewed path and rename manifest;
3. run `git fsck --full`;
4. compare commit counts and representative history;
5. verify author identity and timestamps on representative files;
6. verify licenses and executable bits;
7. inspect the entire resulting file inventory for private or unrelated content;
8. run the child package gate before any push;
9. retain the clone until leader acceptance and remote verification.

Never run history filtering in the main checkout or the only recovery copy.

## Recommended decisions

| ID | Decision | Leader recommendation | Status |
| --- | --- | --- | --- |
| D1 | Mapping | Accept the ownership manifest above | Approved |
| D2 | Shared control bridge | Promote one host-neutral implementation into core | Approved |
| D3 | `unstable` branch | Preserve in recovery bundle only; do not extract | Approved |
| D4 | Ecosystem history | Create a clean collector repository | Approved |
| D5 | Current public remote | Preserve/archive the monorepo until all children and the ecosystem pass; do not rewrite it in place | Approved |
| D6 | New-repository default branch | Use `main`; retain source `master` only in the archived source history | Approved |
| D7 | Visibility | Private meta; public ecosystem and children, as already locked | Approved |
| D8 | Initial versions | Coordinate initial `0.1.0`, then version children independently | Approved |
| D9 | Freeze source | Latest accepted `HEAD` after the final full gate | Approved; exact prerelease mapping pending |
| D10 | Freeze ref and version | Use explicit `0.1.0-alpha1` / `0.1.0-alpha2` identities as directed by the user | Exact commit and manifest/tag mapping required |
| D11 | Registry names and checks | Use locked names; user controls suitable PyPI/npm accounts and will handle availability/publication later; no agent registry contact | Approved and deferred |
| D12 | Physical migration | Begin only after all preceding gates and maintenance-window confirmation | Not authorized |
| D13 | GitHub owner and target repositories | Use `arcanemachine/inter-agent-meta`, `arcanemachine/inter-agent`, `arcanemachine/inter-agent-core`, `arcanemachine/inter-agent-pi`, and `arcanemachine/inter-agent-claude-code` | Approved |
| D14 | Monorepo archive name | Rename the current repository to `arcanemachine/inter-agent-monorepo` before creating the clean ecosystem repository at `arcanemachine/inter-agent` | Approved |
| D15 | GitHub operation responsibility | Leader may use an existing authenticated `gh` session for approved rename/create operations; user performs every push | Approved, later authorization still required |
| D16 | Branch protection | No agent action; user manages hosting policy | Approved and user-owned |
| D17 | Migration workspace | Use `/workspace/tmp/inter-agent-migration/` only for transitional bundles, mirrors, filtering clones, and build artifacts; nothing there is a permanent deliverable | Approved |
| D18 | Maintenance workflow | Stop repository writers, run the final gates, and create verified recovery artifacts before migration edits | Approved; exact window pending |
| D19 | Final physical gate | Require a separate final go/no-go before tag creation, GitHub operations, filtering, or pushing | Approved |

## Mandatory user gate

Before repository/ref creation, remote changes, registry contact, history filtering, directory moves, or publication, resolve and record:

- authorization for leader-performed GitHub rename/create operations;
- current plugin-version policy and freeze blocker;
- exact `0.1.0-alpha1` / `0.1.0-alpha2` commit, manifest, and tag mapping;
- maintenance-window timing;
- final freeze version/ref;
- authorization for physical migration.

## Proposed prerelease mapping

Planning proposal only; not yet approved:

1. Treat tested commit `2ae2a72ee375514914c7c5cdbddf311a40fcd363` as historical prerelease `0.1.0-alpha1`.
2. Update the final monorepo metadata consistently for `0.1.0-alpha2`, using the Python-normalized form where packaging requires it.
3. Restore the Claude plugin version using the approved alpha-2 identity so coordinated metadata and validation agree.
4. After the complete gate passes, treat that exact final commit as `0.1.0-alpha2`.
5. Create annotated `0.1.0-alpha1` and `0.1.0-alpha2` tags only after the final physical go/no-go.
6. Let extracted children progress from alpha-2 source toward their first stable `0.1.0` releases.

The user must confirm whether alpha identities apply to both package manifests and Git tags, or to Git tags only.

## Planned execution runbook

Status: planning only; none of these actions is currently authorized

### Phase A — resolve and validate the final source

1. Confirm the prerelease mapping above.
2. Make only the approved coordinated version-policy correction.
3. Run the focused version/plugin checks.
4. Run the complete monorepo, Pi, and Claude gates against the resulting current `HEAD`.
5. Confirm a clean worktree and record the exact passing commit.
6. Commit the validated metadata correction before requesting physical migration authorization.

### Phase B — final physical go/no-go

Present the exact passing commit, proposed tags, GitHub operations, local recovery commands, workspace inventory, and writer-lock status. Obtain one explicit go/no-go covering only those reviewed actions.

No earlier planning approval substitutes for this gate.

### Phase C — source freeze and temporary recovery set

After the go/no-go:

1. Begin the maintenance window and confirm no executor or other session is writing to the monorepo.
2. Create the approved local annotated source tags without pushing them.
3. Create and verify an all-refs bundle under `/workspace/tmp/inter-agent-migration/`.
4. Record its SHA-256 digest in this maintainer migration record.
5. Create a local mirror from the checkout without contacting the remote.
6. Run `git fsck --full` and verify the mirror contains `master`, `unstable`, and both approved source tags.
7. Create no child filtering clone until its roadmap item becomes active.

The bundle and mirror remain transitional recovery material through the extraction program. They are removed only after verified durable repositories exist and the user explicitly confirms cleanup.

### Phase D — approved GitHub topology transition

After separate credential-use authorization:

1. Use the existing authenticated `gh` session without displaying credential details.
2. Rename `arcanemachine/inter-agent` to `arcanemachine/inter-agent-monorepo`.
3. Create private `arcanemachine/inter-agent-meta` without pushing source.
4. Create public `arcanemachine/inter-agent` as the clean ecosystem placeholder without importing monorepo history.
5. Do not create child repositories early; each child repository is created with its extraction item.
6. Update the source checkout's `origin` to the approved archive URL only after the rename is verified.
7. The user performs every push, including source tags and initial meta/ecosystem branches.
8. The leader verifies repository names and visibility without exposing credentials.

### Phase E — private meta scaffold

Using an isolated filtering clone from the verified local mirror:

1. Filter only the approved meta-owned paths from the accepted freeze branch.
2. Reorganize them into a maintainer-only repository with no runtime code, package artifacts, generated environments, secrets, or copied child histories.
3. Retain the active plan, role/workflow documents, accepted migration record, and internal planning history.
4. Add the clean public ecosystem repository at `ecosystem/` only after the user has pushed an initial ecosystem commit that can be pinned as a submodule.
5. Run `git fsck --full`, inspect the complete file inventory, and run `git diff --check`.
6. Prepare the local meta branch for the user's push; the leader does not push it.

### Phase F — checkpoint verification and closeout

1. Verify the archived monorepo remains complete and recoverable.
2. Verify private meta and public ecosystem visibility and canonical URLs.
3. Verify the meta repository contains no runtime source or secret material.
4. Verify the ecosystem placeholder contains no monorepo/private history.
5. Verify the reviewed path manifest remains usable for Pi, Claude, and core extraction.
6. Record user-performed pushes and observed remote results.
7. Close item 10 only when Pi extraction can begin without unresolved ownership, naming, recovery, or authorization questions.
8. Prepare the concrete Pi-extraction packet as roadmap item 11; do not begin it under item 10.

## Immediate next steps

1. Confirm or revise the proposed prerelease mapping.
2. Resolve the remaining maintenance-window and final-ref decisions.
3. Update and commit this record with approved values.
4. Prepare the exact final-source metadata change for separate authorization.
5. Stop at the final physical go/no-go before any tag, credentialed action, remote operation, filtering, or push.
