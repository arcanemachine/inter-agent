# Final Completion Review

Phase: 6 — Release Readiness

## Purpose

Verify that all roadmap goals are satisfied and no completion-scope work remains undocumented.

## Scope

- Review every roadmap phase.
- Review plan directories for remaining items.
- Run repository checks.
- Confirm ideas are separated from completion scope.

## Work

1. Confirm every phase in `ROADMAP.md` meets its completion criteria.
2. Confirm each plan item has either been completed or intentionally revised into another completion-scope plan.
3. Confirm `IDEAS.md` contains exploratory work that is not required for completion.
4. Run the local quality gate command and individual checks if needed for diagnosis.
5. Review `git status` for generated artifacts.
6. Update docs to remove planning references that no longer apply.
7. Prepare a concise completion summary for maintainers.

## Acceptance criteria

- `ROADMAP.md` accurately describes completed scope.
- No completion-scope work is hidden only in chat history or removed planning files.
- Required checks pass.
- The repository is ready for maintainer review.

## Files likely to change

- `ROADMAP.md`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `AGENTS.md`
- `IDEAS.md`

## Checks

- local quality gate command
- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`
- `uv build`
