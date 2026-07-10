# Task 01: Establish leader/executor workflow

## Status

Ready for executor dispatch.

## Goal

Establish the repository-specific leader/executor workflow documentation and move the active-plan file from the repository root to `.agents/PLAN.md` without changing product behavior.

## Bootstrap exception

The role documents created by this task do not exist yet. For this task only, read `AGENTS.md` and this task file before working. Do not read `.agents/PLAN.md` until you have created it by moving `PLAN.md`. Do not read other files unless they are listed below.

## Permitted reading and modification scope

You may read and modify only these existing files:

- `AGENTS.md`
- `PLAN.md` — move it to `.agents/PLAN.md`; do not leave a root `PLAN.md`.
- `ROADMAP.md`
- `docs/IDEAS.md`
- `docs/ideas/README.md`
- `docs/plans/README.md`
- `docs/plans/codex-support/00-validation-spike.md`
- `docs/plans/opencode-support/00-execution-guide.md`
- `docs/plans/opencode-support/07-packaging-docs-and-quality-gate.md`
- `docs/plans/repo-split/00-first-slices.md`
- `integrations/codex/README.md`
- `integrations/opencode/README.md`

You may create only these files:

- `.agents/roles/leader.md`
- `.agents/roles/executor.md`

Do not modify `docs/archive/**`, implementation code, tests, package metadata, or any unlisted file. Do not create a commit.

## Required changes

### 1. Shared role entry point

Update `AGENTS.md` with a concise role section that:

- defines exactly two roles: `leader` and `executor`;
- requires the user to explicitly assign a role before task work begins;
- requires an agent with no assigned role to stop and ask for one;
- requires an agent assigned an unknown role to stop and list the available roles;
- directs a leader to `.agents/roles/leader.md` and an executor to `.agents/roles/executor.md`;
- identifies `.agents/PLAN.md` as the authoritative active-plan file and `.agents/plans/` as the location for detailed active task packets.

Keep the existing repository-specific requirements intact, including the existing testing, documentation, and commit requirements.

### 2. Leader role

Create `.agents/roles/leader.md`. It must state that a leader:

- follows `AGENTS.md` before this role document;
- reads `.agents/PLAN.md` after role assignment, then performs only light inventory to prepare a list of still-unread files needed for planning;
- presents that reading list to the user and reads the listed files only after explicit approval; later planning may use additional separately approved reading lists;
- asks the user all unresolved questions and does not make important design, scope, security, or product decisions implicitly;
- creates a bounded, self-contained task packet before delegation, including: goal, allowed files to read and modify, non-goals, exact requirements, acceptance criteria, checks, and user acceptance test steps only when behavior is user-facing;
- commits the active plan/task-packet preparation before dispatching an executor;
- asks the user for explicit authorization before dispatching an executor;
- uses direct dispatch only for simple single-task work; uses one detailed task packet per executor task for complex, multi-stage, or multi-executor work;
- lists available connected executor sessions by ascending routing name (`executor`, `executor-2`, `executor-3`, and so on), assigns each new task to the next previously unused executor, and ensures every task is independently completable without earlier executor context;
- sends substantive rework for a task back to its original executor; treats rework as the same task; stops and asks the user if no unused executor is available for a new task;
- reviews every executor change against the packet, performs final quality review and relevant verification, sends substantive defects back for rework, and may directly correct only trivial typos, formatting, or similarly small stylistic defects;
- commits each reviewed completed task; provides a concise runnable UAT to the user only for user-facing behavior;
- keeps `.agents/PLAN.md` minimal and accurate about current work; removes an active plan directory from `.agents/plans/` after all its tasks are complete, relying on Git history for completed task details.

State clearly that executor changes are not accepted merely because they exist, and that user approval is required for decisions outside the approved task scope.

### 3. Executor role

Create `.agents/roles/executor.md`. It must state that an executor:

- follows `AGENTS.md`, then this role document, then only its dispatch brief and files explicitly authorized by that brief;
- does not read `.agents/PLAN.md` unless the dispatch brief explicitly authorizes it;
- works only on the single assigned bounded task and only touches files explicitly listed in its task packet;
- makes no unapproved design, scope, behavior, security, or policy decisions;
- stops and reports to the leader if requirements conflict, an unlisted file is needed, a check exposes a material decision, or scope must expand;
- runs the packet's required checks and reports the changed files, check results, remaining concerns, and any blocker precisely;
- never commits, amends commits, rewrites history, or treats its work as accepted;
- handles requested substantive rework only for its original task and waits for the leader to assign any new task.

### 4. Plan relocation and task-packet layout

Move root `PLAN.md` to `.agents/PLAN.md`. Update it so it remains concise, is authoritative for active work, states that detailed active packets live in `.agents/plans/<plan-name>/`, and identifies this active `agent-workflow` plan and Task 01 as the current work.

Keep the repository's existing distinction intact:

- `.agents/PLAN.md` — current active work only;
- `.agents/plans/` — detailed, temporary active task packets;
- `ROADMAP.md` — accepted medium-/long-term direction;
- `docs/plans/` — prospective execution notes;
- `docs/IDEAS.md` and `docs/ideas/` — exploratory or non-active follow-ups;
- `docs/archive/plans/` — historical records, which this task must not edit.

### 5. Live-reference updates

Update every permitted live document above so references to the active plan identify `.agents/PLAN.md`, not root `PLAN.md`. Preserve the meaning and prospective status of OpenCode, Codex, repository split, and other roadmap material. Do not alter historical archive documents.

Use correct Markdown link targets where the existing text is a link. For prose/code references, use the repository-root-relative path `.agents/PLAN.md`.

## Acceptance criteria

- Root `PLAN.md` no longer exists; `.agents/PLAN.md` exists.
- `AGENTS.md` lists exactly the `leader` and `executor` roles and the role-assignment stop behavior.
- Both role files exist and cover their required responsibilities and boundaries.
- `.agents/PLAN.md` accurately identifies the active `agent-workflow` plan and this task.
- The permitted live planning documents no longer present root `PLAN.md` as the active-plan location.
- `docs/archive/**` is unchanged.
- No product behavior, protocol, implementation source, tests, or package metadata changes.
- No commit is created by the executor.

## Required checks

Run from the repository root:

```bash
test -f .agents/PLAN.md && test ! -e PLAN.md
git diff --check
git grep -n 'PLAN\.md' -- ':!docs/archive/**'
uv run pytest tests/test_versioning_docs.py
```

Inspect the final `git grep` output to confirm every live active-plan reference uses `.agents/PLAN.md`; references to `docs/plans/` are expected and should remain. This task packet may itself mention the old root `PLAN.md` while describing the migration; that is expected until the leader removes the completed task packet.

## Report format

Report:

1. modified and created file paths;
2. a concise summary of the workflow and relocation changes;
3. each required command and its result;
4. confirmation that no commit was made;
5. any blocker or concern requiring leader review.
