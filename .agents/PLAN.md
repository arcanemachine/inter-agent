# Active Plan

`.agents/PLAN.md` is for short-term work that is actively being done or ready to be done next in the current session. It is intentionally small.

Use [`../ROADMAP.md`](../ROADMAP.md) for accepted medium- and long-term direction. Use [`../docs/plans/`](../docs/plans/) for future execution notes. Use [`../docs/IDEAS.md`](../docs/IDEAS.md) for exploratory or unaccepted ideas.

Detailed active task packets live in `.agents/plans/<plan-name>/`.

## Current active work

- Correct leader plan-selection guidance so an inactive plan follows the accepted work sequence instead of prompting arbitrary roadmap choices.
  - Task packet: `.agents/plans/leader-plan-selection-guidance/01-correct-leader-plan-selection.md`

## Planning workflow

1. Keep `README.md` focused on present, implemented behavior.
2. Keep prospective or not-yet-implemented work out of the supported integration list.
3. Track accepted medium- and long-term direction in `ROADMAP.md`.
4. Track future execution notes in `docs/plans/**` when they are more detailed than `ROADMAP.md` but not active enough for `.agents/PLAN.md`.
5. Track rough or exploratory ideas in `docs/IDEAS.md` until the user accepts them for the roadmap or active plan.
6. When a roadmap item becomes active, copy only the next concrete slice into `.agents/PLAN.md`.
7. When an active item is completed, remove it from this file and update product docs only for behavior that now exists.

## Completion standard

Before handing back completed code or checked documentation work, run the relevant checks for the changed area. For normal code changes, use the repository gate:

```bash
./run-checks.sh
```

For documentation-only wording or planning changes that do not touch generated or checked artifacts, `git diff --check` is sufficient unless the user asks for the full gate.
