# Active Plan

`.agents/PLAN.md` is for short-term work that is actively being done or ready to be done next in the current session. It is intentionally small.

Use [`../ROADMAP.md`](../ROADMAP.md) for accepted medium- and long-term direction. Use [`../docs/plans/`](../docs/plans/) for future execution notes. Use [`../docs/IDEAS.md`](../docs/IDEAS.md) for exploratory or unaccepted ideas.

Detailed active task packets live in `.agents/plans/<plan-name>/`.

## Current active work

### Project closeout — item 8: Pi queued mailbox

Queue inbound direct, broadcast, and channel bodies by default; add explicit immediate delivery, metadata-only notices, bounded in-memory storage, and selected/all reads. Priority insertion 7a was accepted in `37aec5b`.

Task packet:

- [Task 1 — Pi queued mailbox and explicit immediate delivery](plans/pi-queued-mailbox/01-queued-delivery-and-read-tool.md)

The user has authorized redispatch of this same task after executor reset and compaction. User-invoked effective kick is the next roadmap item after item 8 is accepted.

Continuity after this item is tracked as individually named work in [`../ROADMAP.md`](../ROADMAP.md#closeout-execution-queue). Only the current item belongs in this active plan.

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
