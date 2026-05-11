# Pi User Workflow Docs

Phase: 3 — Adapter Integration and Command UX

## Purpose

Describe the Pi adapter as the primary host workflow while keeping core protocol docs separate from host-specific usage.

## Repurposed planning item

- Clarify startup model in docs: primary quickstart is Pi-based; development helper scripts are secondary.

## Scope

- Update user-facing quickstart.
- Keep adapter-specific instructions in the adapter docs.
- Avoid temporary status language.

## Work

1. Rewrite `README.md` quickstart around `uv sync`, server entry point, and Pi adapter commands.
2. Move detailed Pi command examples into the Pi adapter README.
3. Document the distinction between core protocol commands and Pi host commands.
4. Link to `ARCHITECTURE.md`, `SECURITY.md`, and `ERROR_CODES.md` where relevant.
5. Ensure examples use command names established in Phase 1.
6. Keep `start.sh` references in a development-helper section only.

## Acceptance criteria

- A user can follow the README to start the server and use Pi commands.
- Adapter-specific details are not mixed into protocol architecture text.
- Docs do not describe old file-path command usage as the main path.
- Docs are stable descriptions, not session notes.

## Files likely to change

- `README.md`
- `adapters/pi/README.md` or namespaced equivalent
- `ARCHITECTURE.md`
- `SECURITY.md`

## Checks

- `uv run pytest`
- Manual review of documented command examples against implemented entry points
