# Plans

`docs/plans/` holds execution notes for accepted or likely upcoming work that is more detailed than `ROADMAP.md` but not active enough for `PLAN.md`.

## Boundaries

- `ROADMAP.md` records accepted direction and sequencing.
- `PLAN.md` records only the currently active work slice.
- `docs/plans/**` records concrete or seed implementation plans for future activation.
- `docs/IDEAS.md` and `docs/ideas/**` hold exploratory ideas that are not yet accepted or sequenced.
- `docs/archive/plans/**` holds historical execution notes.

## Status levels

Plan files should use one of these statuses near the top:

- `seed`: enough context to orient a worker, but requires an inventory/design pass before implementation.
- `concrete`: scoped enough to copy a slice into `PLAN.md` and implement.
- `completed`: preserved for reference after implementation, when not moved to `docs/archive/plans/**`.

## Activation workflow

1. Read the relevant roadmap item and plan directory.
2. If the plan is `seed`, perform a bounded inventory/design task and update or add a concrete plan before coding.
3. Copy only the next concrete slice into `PLAN.md`.
4. Implement with tests, docs, and verification.
5. Remove completed active work from `PLAN.md` and update roadmap/docs to match implemented behavior.

## Upcoming action queue

1. `pubsub-channels/00-design-seed.md` — next protocol feature; convert to a concrete plan before implementation.
2. `opencode-support/00-execution-guide.md` — first new host integration after channels; start with direct WebSocket/package scaffold validation.
3. `codex-support/00-validation-spike.md` — validate Codex App Server sidecar assumptions after OpenCode.
4. `repo-split/00-first-slices.md` — prepare independent package/repository extraction once core and extension boundaries stabilize.
