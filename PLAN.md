# PLAN.md

## Top priorities for next session

- Improve installation/setup instructions to use `uv sync` (or equivalent `uv` workflow), not `pip install` command sequences.
- Clarify startup model in docs:
  - Primary quickstart should be Pi-based: start server, install Pi extension, start Pi, use adapter commands.
  - If `start.sh` remains, document it explicitly as a local demo/dev helper path (not the primary coding-agent UX).

## Purpose

This file is the next-session execution plan for `inter-agent`.

Use it to restart quickly with consistent workflow and scope.

## Current state snapshot

- MVP exists and is functional.
- Core docs exist and should be kept evergreen:
  - `README.md`
  - `ARCHITECTURE.md`
  - `SECURITY.md`
  - `AGENTS.md`
- Incomplete work is tracked in `TODO.md`.
- Tooling/checks are in place and pinned.

## Prior plan status

- Accounted for:
  - Repository skeleton
  - Protocol/spec scaffold
  - Core server/client/send/list flow
  - Custom envelope pass-through behavior
  - Pi adapter command surface
  - Conformance/spec tests
  - Security baseline docs
- Deferred (still applicable and tracked in `TODO.md`):
  - CI workflow
  - richer protocol semantics/target resolution
  - capability negotiation tests
  - lifecycle hardening and optional extensions

## Next-session startup checklist

1. Run setup and checks first (prefer `uv sync` workflow):
   - `uv sync`
   - `uv run black --check .`
   - `uv run ruff check .`
   - `uv run mypy core adapters tests`
   - `uv run pytest -q`

2. Confirm docs/workflow alignment:
   - `AGENTS.md` rules still match team expectations.
   - `TODO.md` is the only incomplete-work tracker.

3. Execute next work in order:
   - Implement top chronological item in `TODO.md`.
   - Add/update tests for behavior changes.
   - Update evergreen docs if behavior changes.
   - Remove completed item from `TODO.md`.
   - Commit atomically.

## Immediate recommended next task

Add package entry points so users can run server and adapter commands without direct file paths.

Acceptance:
- New user can run server/connect/send/list/status via stable command entry points.
- README quickstart updated accordingly.
- Tests/checks pass.

## Commit discipline

- Atomic commits per logical step.
- Author identity:
  - Name: Nicholas Moen
  - Email: arcanemachine@gmail.com
