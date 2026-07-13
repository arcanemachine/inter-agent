# Correct leader plan-selection guidance

## Goal

Make the leader workflow follow the existing accepted work sequence when no active plan is present, instead of offering arbitrary roadmap directions.

## Allowed files

- Read and modify `.agents/roles/leader.md`.
- Read `.agents/PLAN.md` and `ROADMAP.md` only for context.

## Non-goals

- Do not modify product, protocol, implementation, test, or roadmap content.
- Do not select or activate a product-work plan.
- Do not alter executor workflow rules.

## Requirements

1. Replace the no-active-plan default-inventory guidance with guidance that identifies the next accepted, ordered activation step from the existing plan/roadmap before consulting exploratory ideas.
2. Require a leader to recommend that concrete existing next step rather than asking the user to choose among unrelated roadmap directions.
3. Preserve the requirement to use light inventory, list exact unread files, and obtain approval before reading them.
4. Limit user questions to genuine unresolved decisions in the selected concrete step.
5. Keep the guidance concise and consistent with the existing role-document style.

## Acceptance criteria

- A leader with no active plan follows the documented accepted sequence and proposes its next concrete activation step.
- The workflow does not direct the leader to begin by reading exploratory ideas or to solicit arbitrary direction choices when the roadmap provides a next step.
- Existing approval boundaries remain intact.

## Checks

Run `git diff --check`.
