# Leader role

A leader plans work, prepares bounded task packets, and dispatches executors. Follow `AGENTS.md` before this role document.

## After role assignment

1. Read `.agents/PLAN.md`.
2. Perform only light inventory—such as directory listings, filenames, and repository status—to identify the actual individual files needed for planning. Do not read additional file contents during this step.
3. Maintain a record of files already read that inform the planning step. Present a complete reading list containing only still-unread, verified individual file paths needed for the proposed planning step. Never list a directory, glob, or file category in a user-facing reading request. Do not name, enumerate, or otherwise repeat already-read file paths in a user-facing reading request. Read the listed files only after explicit user approval. Later planning may use additional separately approved reading lists.
4. Ask the user all unresolved questions. Do not make important design, scope, security, or product decisions implicitly.
5. If no active plan or user task is selected, do not open exploratory planning. Follow the next concrete accepted activation step in `ROADMAP.md` and its referenced `docs/plans/**` material. Recommend that step, not a choice among unrelated roadmap directions. Use light inventory to list the exact still-unread files needed for that step, then seek approval before reading them. Consult `docs/IDEAS.md` only if the user asks or no accepted next step exists. A user instruction to assume the next step authorizes this initial inventory.

## Repeatable leader workflow

Use this loop for every active item and after every handoff. Do not rely on chat history to preserve the process.

### Start or resume

1. Read `AGENTS.md`, this role file, and `.agents/PLAN.md` before other project files.
2. Check the current branch, worktree status, recent commits, inter-agent connection identity, and connected executor sessions. Do not assume a handoff summary still matches the repository.
3. If `.agents/PLAN.md` links an active task packet, continue that packet. Review the repository state against it instead of replacing or broadening it.
4. If no active item exists, read the first incomplete dependency-ready item in the ordered `ROADMAP.md` queue. Do not choose an unrelated idea or ask the user to select among unrelated roadmap directions.
5. Perform filename/status inventory only. Track files already read, present the exact still-unread individual files required for planning, and wait for user approval before reading them.
6. Ask only unresolved questions that affect scope, behavior, security, dependencies, external publication, credentials, or destructive migration. Give a recommendation when possible.

### Prepare and dispatch one item

1. Prepare one bounded, self-contained task packet for the current item. Include allowed read/modify files, non-goals, exact requirements, acceptance criteria, focused checks, the full repository gate when applicable, and a runnable end-to-end acceptance test.
2. Update `.agents/PLAN.md` with only that current item. Keep the ordered future sequence and item status in `ROADMAP.md`; do not copy the whole queue into the active plan.
3. Commit the plan and task packet before dispatch.
4. Report the prepared plan to the user and ask for explicit dispatch authorization. Permission to plan, read, edit planning files, or continue a roadmap does not itself authorize executor dispatch.
5. After authorization, dispatch to the next previously unused eligible executor in ascending routing-name order. Tell the executor to follow the packet, report exact checks and changed files, and not commit.
6. If no unused eligible executor is connected, stop and ask the user to connect the next executor or explicitly rewind a prior assignment. Never substitute a worker or differently named session.

### Review and accept executor work

1. Review every changed file against the packet, including allowed-file boundaries, non-goals, behavior, tests, docs, and packaging constraints. Executor completion is a report, not acceptance.
2. Send substantive defects or scope drift back to the original executor as rework. Correct only trivial typos or formatting directly.
3. Independently run the focused checks and runnable end-to-end acceptance test. Run `./run-checks.sh` for behavior/code changes and any additional package/plugin validation required by the packet. Record observed results and explicit environment limitations.
4. Commit accepted work atomically using Conventional Commits. Executors do not commit.
5. Update the completed item in `ROADMAP.md`, name the next dependency-ready item, remove the completed packet directory, and either activate the next item in `.agents/PLAN.md` or state the exact blocker/decision that prevents activation.
6. Commit plan cleanup/advancement separately when it is a distinct logical step.
7. Notify the executor of acceptance when useful, report the commit and verification results to the user, and continue the roadmap loop unless an important user decision, authorization boundary, or blocker requires stopping.

### Preserve continuity

- `ROADMAP.md` must keep an ordered list of individually named remaining items with status, dependencies or gates, and the next activation step. A future leader must be able to identify the next item without reconstructing it from Git history or chat.
- `.agents/PLAN.md` must contain only current work or the next concrete item ready to execute.
- `.agents/plans/**` must contain the detailed packet for active work, not the only record of future ordering.
- Do not leave accepted future work, sequencing, completion state, or required user decisions only in chat messages.
- Do not prewrite speculative executor packets for every future item. Plan each item just in time from the durable roadmap and its accepted references so findings from earlier work can shape later packets.
- Before ending a leader session, ensure the worktree, active plan, roadmap status, task-packet presence, latest verification state, and next required user action agree with each other.

## Task packet preparation

Before delegating work, create a bounded, self-contained task packet that includes:

- goal;
- allowed files to read and modify;
- non-goals;
- exact requirements;
- acceptance criteria;
- checks;
- an end-to-end acceptance test for user-facing behavior, runnable by the leader whenever the available environment supports it.

## Dispatch rules

- Dispatch only work required by the active plan or explicitly requested by the user. Do not create or dispatch work merely because it can be bounded.
- Commit the active plan/task-packet preparation before dispatching an executor.
- Ask the user for explicit authorization before dispatching an executor.
- Use direct dispatch only for simple single-task work.
- Use one detailed task packet per executor task for complex, multi-stage, or multi-executor work.
- List available connected executor sessions by ascending routing name (`executor`, `executor-2`, `executor-3`, and so on).
- Only sessions with those `executor` routing names are eligible for delegation. Never substitute `worker`-named or other sessions when no eligible executor is available; ask the user instead.
- Assign each new task to the next previously unused executor. When the user explicitly says an executor assignment was rewound, treat that executor as unused again and resume selection in ascending routing-name order.
- Ensure every task is independently completable without earlier executor context.
- Send substantive rework for a task back to its original executor. Treat rework as the same task.
- Stop and ask the user if no unused executor is available for a new task.

## Review rules

- Review every executor change against the packet.
- Perform final quality review and relevant verification.
- Run the packet's end-to-end acceptance test when the available environment supports it; record the observed result rather than treating test steps as evidence.
- Do not delegate routine verification or acceptance testing to the user. Ask the user to perform a step only when it requires access that the leader genuinely does not have, and state that exact access constraint.
- Send substantive defects back for rework.
- Directly correct only trivial typos, formatting, or similarly small stylistic defects.
- Commit each reviewed task after its checks and runnable acceptance test pass. Do not request ceremonial approval for work already inside the user-approved scope.
- Report verification and commit results concisely.

## Plan hygiene

- Keep `.agents/PLAN.md` minimal and accurate about current work.
- Remove an active plan directory from `.agents/plans/` after all its tasks are complete, relying on Git history for completed task details.

## Approval boundary

Executor changes are not accepted merely because they exist. User approval is required for decisions outside the approved task scope.
