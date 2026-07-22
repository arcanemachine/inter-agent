# Plans

`docs/plans/` holds execution notes for accepted or likely upcoming work that is more detailed than `ROADMAP.md` but not active enough for `.agents/PLAN.md`.

## Boundaries

- `ROADMAP.md` records accepted direction and sequencing.
- `.agents/PLAN.md` records only the currently active work slice.
- `docs/plans/**` records concrete or seed implementation plans for future activation.
- `docs/IDEAS.md` and `docs/ideas/**` hold exploratory ideas that are not yet accepted or sequenced.
- `docs/archive/plans/**` holds historical execution notes.

## Status levels

Plan files should use one of these statuses near the top:

- `seed`: enough context to orient a worker, but requires an inventory/design pass before implementation.
- `concrete`: scoped enough to copy a slice into `.agents/PLAN.md` and implement.
- `completed`: preserved for reference after implementation, when not moved to `docs/archive/plans/**`.

## Activation workflow

1. Read the relevant roadmap item and plan directory.
2. If the plan is `seed`, perform a bounded inventory/design task and update or add a concrete plan before coding.
3. Copy only the next concrete slice into `.agents/PLAN.md`.
4. Implement with tests, docs, and verification.
5. Remove completed active work from `.agents/PLAN.md` and update roadmap/docs to match implemented behavior.

## Upcoming action queue

1. Complete the active reliability sequence recorded in `ROADMAP.md` and summarized by `important-closeout/03-reliability-closeout.md`.
2. `important-closeout/01a-user-invoked-kick.md` through `important-closeout/01c-pi-compaction-continuity.md` — complete the accepted kick, reload, and compaction reliability follow-ons after the active current-Pi compatibility baseline.
3. `important-closeout/02-installed-tls-acceptance.md` — prove installed Pi/Claude interoperability over TLS.
4. `important-closeout/04-migration-checkpoint-and-meta.md` through `important-closeout/11-released-ecosystem-acceptance.md` — split clean repositories before publication, publish stable packages through explicit gates, and verify released artifacts.
5. `opencode-support/00-execution-guide.md` — first deferred promotion candidate after important-action closeout and a new user activation decision.
6. `codex-support/00-validation-spike.md` — remains deferred until after the accepted OpenCode outcome.

`important-closeout/00-execution-guide.md` is the durable program index. `repo-split/00-first-slices.md` summarizes the accepted physical topology and links the detailed migration plans. Pub/sub is implemented; `pubsub-channels/00-design-seed.md` remains implementation history/reference rather than upcoming work.
