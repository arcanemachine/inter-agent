# Documentation Evergreen Pass

Phase: 6 — Release Readiness

## Purpose

Ensure user, architecture, security, adapter, and agent docs describe the completed project without stale planning language.

## Scope

- Review and update stable documentation.
- Remove superseded planning references.
- Keep incomplete or exploratory ideas in planning docs only.

## Work

1. Review `README.md` for install, quickstart, command, and troubleshooting accuracy.
2. Review `ARCHITECTURE.md` for layer boundaries, protocol semantics, capabilities, and lifecycle behavior.
3. Review `SECURITY.md` for controls, assumptions, limits, and token lifecycle.
4. Review adapter docs for Pi workflow accuracy.
5. Review `AGENTS.md` for current workflow rules.
6. Remove references to superseded files, old file-path commands, or outdated setup flows.
7. Ensure `IDEAS.md` contains exploratory work that is not part of completion scope.

## Acceptance criteria

- Stable docs match implemented behavior.
- Planning-only language is absent from user-facing product docs.
- No doc refers to superseded planning files.
- Command examples are runnable through documented entry points.

## Files likely to change

- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `AGENTS.md`
- `adapters/pi/README.md` or namespaced equivalent
- `ERROR_CODES.md`
- `IDEAS.md`

## Checks

- `uv run pytest`
- Manual command-example review
