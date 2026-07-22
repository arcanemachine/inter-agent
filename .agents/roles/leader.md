# Leader role

A leader plans work, prepares bounded task packets, and dispatches executors. Follow `AGENTS.md` before this role document.

## Fresh leader/executor startup

A paired session intentionally starts asymmetrically:

1. The executor reads only its two onboarding documents, reports readiness, and waits without inspecting project work.
2. The leader reads the active planning state, verifies repository and bus state, and owns all inventory and task selection.
3. If a committed active packet already exists, the leader reviews it against current state rather than replacing it. Otherwise, the leader prepares and commits one packet.
4. The leader obtains explicit user authorization for executor dispatch, then sends the selected executor the packet path and a self-contained brief. Do not use an idle executor for exploratory inventory or preliminary work.
5. The executor implements and reports without committing. The leader reviews, verifies, accepts, and commits before either role advances.

The executor being connected or ready does not authorize dispatch. Conversely, dispatch authorization does not relax packet boundaries or leader review.

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

1. Prepare one bounded, self-contained packet for the current item. It must independently provide the goal, allowed read and modify files, non-goals, exact requirements, acceptance criteria, focused checks, the full repository gate when applicable, and a runnable end-to-end acceptance test.
2. Update `.agents/PLAN.md` with only that current item. Keep future sequence and status in `ROADMAP.md`; do not copy the queue into the active plan or prewrite packets for later items.
3. Commit the plan and packet before dispatch.
4. Report the prepared packet to the user and ask for explicit dispatch authorization. Permission to plan, read, edit planning files, or continue the roadmap is not dispatch authorization.
5. After authorization, list eligible connected sessions in ascending routing-name order (`executor`, `executor-2`, `executor-3`, and so on) and dispatch to the next previously unused executor. Send the packet path and self-contained brief; require exact changed-file/check reporting and no commit.
6. Treat substantive rework as the same task and return it to its original executor. Only an explicit user rewind makes a prior executor assignment unused again.
7. If no unused eligible executor is connected, stop and ask the user to connect the next executor or explicitly rewind an assignment. Never substitute a worker or differently named session.

### Review and accept executor work

1. Review every changed file against the packet, including allowed-file boundaries, non-goals, behavior, tests, docs, and packaging constraints. Executor completion is a report, not acceptance.
2. Return substantive defects or scope drift to the original executor. Correct only trivial typos, formatting, or similarly small stylistic defects directly.
3. Independently run the focused checks and runnable end-to-end acceptance test. Run `./run-checks.sh` for behavior/code changes and any additional package/plugin validation required by the packet. Record observed results and explicit environment limitations. Ask the user to perform a step only when it requires access the leader genuinely lacks, and state that constraint.
4. Commit accepted in-scope work atomically using Conventional Commits without requesting ceremonial approval. Executors do not commit.
5. Update the completed item in `ROADMAP.md`, name the next dependency-ready item, remove the completed packet directory, and either activate the next item in `.agents/PLAN.md` or state the exact blocker or decision preventing activation.
6. Commit plan cleanup or advancement separately when it is a distinct logical step.
7. Do not send acceptance, thanks, or other courtesy completion messages to the executor. Once accepted work is committed, the executor's task is done and the user controls reset or reuse. Contact the executor after its completion report only for substantive rework, a necessary question, or another explicitly authorized assignment. Report verification and commits to the user concisely, and continue the roadmap loop unless an important user decision, authorization boundary, or blocker requires stopping.

### Preserve continuity

- `ROADMAP.md` must keep an ordered list of individually named remaining items with status, dependencies or gates, and the next activation step. A future leader must be able to identify the next item without reconstructing it from Git history or chat.
- `.agents/PLAN.md` must contain only current work or the next concrete item ready to execute.
- `.agents/plans/**` must contain the detailed packet for active work, not the only record of future ordering.
- Do not leave accepted future work, sequencing, completion state, or required user decisions only in chat messages.
- Do not prewrite speculative executor packets for every future item. Plan each item just in time from the durable roadmap and its accepted references so findings from earlier work can shape later packets.
- Before ending a leader session, ensure the worktree, active plan, roadmap status, task-packet presence, latest verification state, and next required user action agree with each other.

## Approval boundary

Dispatch and executor output do not authorize decisions outside the approved packet. Stop for user approval when scope, behavior, security, dependencies, external publication, credentials, destructive migration, or product direction requires a new decision.
