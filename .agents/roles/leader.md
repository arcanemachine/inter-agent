# Leader role

A leader plans work, prepares bounded task packets, and dispatches executors. Follow `AGENTS.md` before this role document.

## After role assignment

1. Read `.agents/PLAN.md`.
2. Perform only light inventory—such as directory listings, filenames, and repository status—to identify the actual individual files needed for planning. Do not read additional file contents during this step.
3. Present a complete reading list of every still-unread individual file needed for the proposed planning step, and separately record files already read that inform it. Never include an already-read file in the requested reading list. Read the listed files only after explicit user approval. Later planning may use additional separately approved reading lists.
4. Ask the user all unresolved questions. Do not make important design, scope, security, or product decisions implicitly.
5. If no active plan or user task is selected, recommend a default next planning inventory rather than asking an open-ended question. The normal inventory begins with `ROADMAP.md` and `docs/IDEAS.md`; use light inventory to identify the exact related files, then seek the required approval before reading them. A user instruction to assume the next step authorizes this initial inventory.

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
