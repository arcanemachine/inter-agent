# Active Plan

`.agents/PLAN.md` is for short-term work that is actively being done or ready to be done next in the current session. It is intentionally small.

Use [`../ROADMAP.md`](../ROADMAP.md) for accepted medium- and long-term direction. Use [`../docs/plans/`](../docs/plans/) for future execution notes. Use [`../docs/IDEAS.md`](../docs/IDEAS.md) for exploratory or unaccepted ideas.

Detailed active task packets live in `.agents/plans/<plan-name>/`.

## Current active work

### Closeout item 10 — migration checkpoint and private meta repository

#### Purpose

Establish a safe, explicitly approved starting point for splitting the monorepo. This checkpoint prepares the migration; it does not itself authorize repository extraction, publication, credential use, or remote changes.

The intended topology remains:

- private maintainer repository `inter-agent-meta`;
- public ecosystem repository `inter-agent/inter-agent`;
- public child repositories `inter-agent-core`, `inter-agent-pi`, and `inter-agent-claude-code`.

#### Leader-owned migration-readiness analysis

The leader performs this decision and synthesis work directly rather than delegating it:

1. Verify the current repository state and run the full monorepo, Pi, and Claude validation gates.
2. Identify the candidate tested source commit/version and inventory current package, repository, and remote facts without exposing credentials.
3. Produce the complete path and history-ownership mapping for private meta material, core, Pi, Claude Code, and ecosystem-level files and tests.
4. Design the recoverable backup/ref and throwaway-clone strategy.
5. Identify conflicts and unresolved decisions, then give the user concrete recommendations.

#### User decision and authorization gate

Before any external, credentialed, destructive, or physical migration action, the leader presents recommendations and obtains explicit user decisions for:

- Git hosting owner/organization and exact intended repository URLs;
- private/public visibility;
- authorization to create repositories and push;
- default branches and branch-protection expectations;
- package-registry ownership and namespaces;
- disposition of the current public remote;
- maintenance-window timing;
- final freeze ref, tag, or version;
- authorization to begin physical migration.

#### Mechanical execution after approval

Only after those decisions are locked may the leader prepare a bounded executor packet for concrete mechanical work such as creating the approved recoverable workspace, applying the approved mapping in throwaway clones, or scaffolding the approved private meta repository. Credentialed actions remain with the user when the container lacks authorized access. Pi extraction remains roadmap item 11 and must not begin during item 10.

#### Completion standard

The leader verifies the tested freeze state, recovery path, approved repository visibility and URLs, private/public content boundary, and complete ownership mapping. Item 10 is complete only when item 11 can begin without unresolved naming, ownership, safety, or authorization questions.

#### Current authorization boundary

This active plan records the agreed process only. No executor dispatch, migration-readiness audit, repository or ref creation, credential use, registry contact, remote change, history rewrite, file move, publication, or extraction is currently authorized.

Detailed accepted requirements remain in [`../docs/plans/important-closeout/04-migration-checkpoint-and-meta.md`](../docs/plans/important-closeout/04-migration-checkpoint-and-meta.md). Continuity is tracked in [`../ROADMAP.md`](../ROADMAP.md#closeout-execution-queue).

## Planning workflow

1. When no active work or user task is selected, follow the next concrete accepted activation step in `ROADMAP.md`; do not start from exploratory ideas or ask the user to choose among unrelated roadmap directions.
2. Keep `README.md` focused on present, implemented behavior.
3. Keep prospective or not-yet-implemented work out of the supported integration list.
4. Track accepted medium- and long-term direction in `ROADMAP.md`.
5. Track future execution notes in `docs/plans/**` when they are more detailed than `ROADMAP.md` but not active enough for `.agents/PLAN.md`.
6. Track rough or exploratory ideas in `docs/IDEAS.md` until the user accepts them for the roadmap or active plan.
7. When a roadmap item becomes active, copy only the next concrete slice into `.agents/PLAN.md`.
8. When an active item is completed, remove it from this file and update product docs only for behavior that now exists.

## Completion standard

Before handing back completed code or checked documentation work, run the relevant checks for the changed area. For normal code changes, use the repository gate:

```bash
./run-checks.sh
```

For documentation-only wording or planning changes that do not touch generated or checked artifacts, `git diff --check` is sufficient unless the user asks for the full gate.
