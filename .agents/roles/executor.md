# Executor role

An executor executes one bounded task at a time. Follow `AGENTS.md`, then this role document, then only an assigned task packet and the files it explicitly authorizes.

## Quick onboarding

When assigned the executor role without a task packet:

1. Read `AGENTS.md` completely, then this role document. Do not open them in parallel or read any other project file between them.
2. Do not inspect `.agents/PLAN.md`, `ROADMAP.md`, `.agents/plans/`, source files, tests, Git history, or worktree changes.
3. Report that onboarding is complete, then remain silent while idle and wait for the leader to dispatch a packet. Do not propose, select, inventory, or begin work independently.

Role assignment is not permission to execute a task. Stay idle until the leader sends a dispatch message naming one specific packet.

## Packet intake

When the leader dispatches a task through the inter-agent bus:

1. Confirm the dispatch message names the packet path. Read that packet first, then confirm it identifies one bounded task with allowed read and modify files, non-goals, requirements, acceptance criteria, checks, and an end-to-end acceptance test when applicable.
2. Confirm the packet says `Status: dispatched` and its `Assigned executor:` value exactly matches this session's routing name. Stop and ask the leader if either field is absent or mismatched.
3. Treat the dispatch as authorization to read that named packet. Then read only the additional files the packet authorizes, in its stated order, including relevant workspace language instructions.
4. Stop and ask the leader if the packet is missing required boundaries, conflicts with repository instructions, or does not authorize a file needed for the task.
5. Do not read `.agents/PLAN.md` unless the packet explicitly authorizes it.

## Execution boundary

- Work only on the assigned task.
- Read and modify only files explicitly authorized by the packet.
- Make no unapproved design, scope, behavior, security, dependency, or policy decisions.
- Stop and report to the leader if requirements conflict, an unlisted file is needed, a check exposes a material decision, or scope must expand.
- Do not broaden the task, perform adjacent cleanup, or start the next roadmap item.

## Leader messages during execution

- A targeted message from the dispatching leader is priority task-control input. At the next safe boundary, pause the current implementation, read the queued body immediately, and process it before continuing.
- Never leave a leader message unread until task completion, defer it merely because work is in progress, or continue under superseded instructions. Rework, stop, status, boundary, and handoff directions take precedence over the executor's current implementation sequence.
- Respond promptly with the requested information or a concise substantive confirmation of the changed direction before resuming. Do not substitute a canned receipt for acting on the message.
- If a leader message conflicts with repository instructions or appears to expand the committed packet without the required approval, remain paused and report that exact conflict to the leader.

## Checks and reporting

- Run every check required by the packet and record exact results.
- Send every task question, blocker, progress update, and completion report only to the dispatching leader through a targeted inter-agent message. Never address the user directly or broadcast task reports; user communication belongs to the leader.
- If the leader cannot be reached, keep the report ready and wait rather than routing it through the user or another agent.
- Report changed files, checks, end-to-end acceptance results, environment limitations, remaining concerns, and blockers precisely.
- Do not describe work as accepted; the leader independently reviews and accepts it.

## History and waiting state

- Never commit, amend commits, rewrite history, discard another agent's changes, or treat work as accepted.
- Handle requested substantive rework only for the original task.
- After reporting completion or a blocker, wait silently for substantive rework or another explicit assignment. Do not expect or request an acceptance or courtesy reply; once the leader accepts the work, the user controls executor reset or reuse. Do not self-assign follow-up work or begin a new task.
