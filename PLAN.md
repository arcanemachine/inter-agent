# Active Plan

`PLAN.md` is for short-term work that is actively being done or ready to be done next in the current session. It is intentionally small.

Use [`ROADMAP.md`](ROADMAP.md) for accepted medium- and long-term direction. Use [`IDEAS.md`](IDEAS.md) for exploratory or unaccepted ideas.

## Current active work

No implementation work is selected.

When active work exists, record only the immediate objective, current status, files likely to change, validation, and acceptance criteria needed to finish that work. Do not use this file as a backlog for prospective integrations or broad future phases.

Future agents should treat this section as authoritative for what phase or slice is active. If this section says no implementation work is selected, roadmap items are not active even when detailed prospective notes exist elsewhere.

## Planning workflow

1. Keep `README.md` focused on present, implemented behavior.
2. Keep prospective or not-yet-implemented work out of the supported integration list.
3. Track accepted medium- and long-term direction in `ROADMAP.md`.
4. Track rough or exploratory ideas in `IDEAS.md` until the user accepts them for the roadmap or active work.
5. When a roadmap item becomes active, copy only the next concrete slice into this file.
6. When an active item is completed, remove it from this file and update product docs only for behavior that now exists.

## Completion standard

Before handing back completed code or checked documentation work, run the relevant checks for the changed area. For normal code changes, use the repository gate:

```bash
./run-checks.sh
```

For documentation-only wording or planning changes that do not touch generated or checked artifacts, `git diff --check` is sufficient unless the user asks for the full gate.
