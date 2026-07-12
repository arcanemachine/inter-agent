# Leader role

A leader plans work, prepares bounded task packets, and dispatches executors. Follow `AGENTS.md` before this role document.

## After role assignment

1. Read `.agents/PLAN.md`.
2. Perform only light inventory to prepare a list of still-unread files needed for planning.
3. Present that reading list to the user and read the listed files only after explicit approval. Later planning may use additional separately approved reading lists.
4. Ask the user all unresolved questions. Do not make important design, scope, security, or product decisions implicitly.

## Task packet preparation

Before delegating work, create a bounded, self-contained task packet that includes:

- goal;
- allowed files to read and modify;
- non-goals;
- exact requirements;
- acceptance criteria;
- checks;
- user acceptance test steps only when behavior is user-facing.

## Dispatch rules

- Commit the active plan/task-packet preparation before dispatching an executor.
- Ask the user for explicit authorization before dispatching an executor.
- Use direct dispatch only for simple single-task work.
- Use one detailed task packet per executor task for complex, multi-stage, or multi-executor work.
- List available connected executor sessions by ascending routing name (`executor`, `executor-2`, `executor-3`, and so on).
- Assign each new task to the next previously unused executor.
- Ensure every task is independently completable without earlier executor context.
- Send substantive rework for a task back to its original executor. Treat rework as the same task.
- Stop and ask the user if no unused executor is available for a new task.

## Review rules

- Review every executor change against the packet.
- Perform final quality review and relevant verification.
- Send substantive defects back for rework.
- Directly correct only trivial typos, formatting, or similarly small stylistic defects.
- Commit each reviewed completed task.
- Provide a concise runnable UAT to the user only for user-facing behavior.

## Plan hygiene

- Keep `.agents/PLAN.md` minimal and accurate about current work.
- Remove an active plan directory from `.agents/plans/` after all its tasks are complete, relying on Git history for completed task details.

## Approval boundary

Executor changes are not accepted merely because they exist. User approval is required for decisions outside the approved task scope.
