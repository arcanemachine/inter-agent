# Migration checkpoint and private meta repository

Status: concrete; user-gated physical migration; queued after mailbox and TLS acceptance

## Goal

Freeze an accepted source state, confirm ownership and naming, create the private maintainer superproject, and establish a safe migration workspace before extracting public packages.

## Locked topology and names

- Private: `arcanemachine/inter-agent-meta`.
- Public ecosystem: `arcanemachine/inter-agent`.
- Public children: `arcanemachine/inter-agent-core`, `arcanemachine/inter-agent-pi`, `arcanemachine/inter-agent-claude-code`.
- Private meta contains the public ecosystem repository as a submodule at `ecosystem/`.
- Public ecosystem later contains real child submodules at `core/`, `extensions/pi/`, and `extensions/claude-code/`.

## Mandatory user/maintainer gate

Before any remote creation, history rewrite, directory move, or visibility change, confirm:

- Git hosting owner/organization and exact remote URLs;
- that `inter-agent-meta` is private and every product repository is public;
- authorization to create repositories and push rewritten/extracted history;
- default branch and branch-protection expectations;
- package registry ownership/namespace availability;
- whether the current public remote is converted into the ecosystem superproject or replaced by a new remote;
- a maintenance window in which no executor is modifying the monorepo.

Never request, display, copy, or commit credentials. If repository creation requires maintainer authentication unavailable in the container, provide exact commands for the maintainer and verify results afterward.

## Freeze procedure

1. Finish and commit all pre-migration behavior work.
2. Run the monorepo full gate plus Pi and Claude package validation.
3. Record the accepted source tag/version and clean commit in private migration notes, not public README instructions.
4. Confirm no attached/running agents are editing the repository.
5. Create a recoverable backup/ref before history filtering.
6. Perform filtering in separate temporary clones under a namespaced workspace temp directory, never destructively in the only checkout.
7. Verify commit counts, tags, licenses, authorship, and representative history before pushing.

Git submodules necessarily store commit IDs as gitlinks. Do not copy those hashes into README install instructions.

## Private meta contents

Move or recreate maintainer-only coordination here:

- `.agents/`, active plan, role docs, task packets, and future internal execution state;
- maintainer-specific `AGENTS.md` and private workflow rules;
- internal roadmap/plans/decision records not intended as product documentation;
- migration orchestration notes and acceptance records;
- public ecosystem superproject as the `ecosystem/` submodule.

Do not put runtime code, package artifacts, secrets, registry tokens, generated environments, or duplicated child histories in meta.

Public repositories own stable product README/architecture/security/changelog/license material. If generic public contributor instructions are useful, use an intentionally public `CONTRIBUTING.md`; do not copy private agent workflow by default.

## History extraction strategy

Prefer path-filtered history preservation with `git filter-repo` (or an equivalently reviewed tool), performed in throwaway clones:

- Pi extraction includes `integrations/pi/**`, `src/inter_agent/adapters/pi/**`, Pi tests, Pi docs, and shared files intentionally copied/rebuilt at the child root.
- Claude extraction includes `integrations/claude-code/**`, `src/inter_agent/adapters/claude/**`, Claude tests, and intentional shared docs/license.
- Core extraction includes `src/inter_agent/core/**`, protocol/spec, core/conformance tests, generic scripts/docs/package metadata, and excludes host adapters/assets.

Because files come from multiple current paths, define and review an explicit mapping manifest before running history filters. Do not improvise path renames in the destructive step.

## Transition policy

- The split happens before initial registry publication, so no released monorepo package compatibility promise is required.
- Preserve user-facing CLI names where specified.
- Temporary local editable/path dependencies are allowed only during migration and must be removed before publication.
- Default endpoint, state, token, TLS, and protocol behavior must not change.
- Keep the current monorepo usable until all child extraction branches pass their focused checks.

## Acceptance criteria

- User gates are recorded without credentials.
- Private meta exists with correct visibility and public ecosystem placeholder/submodule strategy.
- A clean, tested freeze commit/ref exists.
- A reviewed path ownership/mapping manifest exists for all children.
- Migration occurs in recoverable clones.
- No public artifact contains private workflow material.
- The next active item can extract Pi without unresolved ownership or naming decisions.

## Checks

Planning-only checkpoint changes require `git diff --check`. Any scripts added for mapping/filter verification require focused tests and the applicable repository gate. Remote visibility and submodule URL verification must be observed from Git, not assumed from documentation.
