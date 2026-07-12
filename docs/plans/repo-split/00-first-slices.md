# Repository split first slices

Status: concrete planning notes; not active.

## Purpose

Prepare the physical repository/package split without disrupting current development.

The accepted target remains:

- private `inter-agent-meta` wrapper;
- public `inter-agent/inter-agent` ecosystem superproject;
- independently deployable `inter-agent-core`, `inter-agent-claude-code`, `inter-agent-pi`, and future extension repositories.

Reference inventory: `docs/archive/plans/09-host-extension-packaging/01-repository-boundary-inventory.md`.

## Recommended first physical slice

Extract the Pi TypeScript extension package (`integrations/pi/`) to an independent `inter-agent-pi` repository while leaving Python helper commands in the current/core package.

Rationale:

- `integrations/pi/` already has package metadata, TypeScript source, README, and extension-specific instructions.
- The TypeScript extension shells out to helper commands; it does not import Python modules directly.
- Keeping `src/inter_agent/adapters/pi/` in the current package avoids changing Python packaging boundaries in the first split slice.
- The root `package.json` Pi install shim can remain during transition.

## Files likely moving in the first slice

Move or copy to `inter-agent-pi`:

- `integrations/pi/AGENTS.md`
- `integrations/pi/README.md`
- `integrations/pi/package.json`
- `integrations/pi/package-lock.json` if present/tracked
- `integrations/pi/tsconfig.json`
- `integrations/pi/src/**`
- Pi extension static tests or equivalent package-local tests
- relevant license and package docs

Remain in core/current repository for this slice:

- `src/inter_agent/adapters/pi/**`
- Python console script `inter-agent-pi`
- core protocol/client/server code
- root `package.json` shim, unless the user accepts removing the transition install path

## Required transition decisions

Before extraction, decide:

1. New repository name and remote ownership.
2. Whether to preserve `pi install https://github.com/arcanemachine/inter-agent` temporarily through the root shim.
3. Where static extension tests live during transition.
4. How extension docs point users to the Python/core runtime install source.
5. Whether Pi TODO items move to the Pi repository immediately.

## Suggested first active slice

Copy this into `.agents/PLAN.md` only when ready:

> Prepare Pi extension extraction by creating an `inter-agent-pi` package boundary document, moving Pi extension-specific tests into a package-local test plan or smoke script, and updating docs so the extension can be installed from an independent repository while still resolving the core Python helper commands.

## Acceptance criteria for first slice

- Current repository checks still pass.
- Pi extension install docs identify both transitional monorepo and future independent-repo paths without claiming an unpublished package is available.
- Extension tests have an explicit future home.
- No Python package boundary changes are made.
- No default endpoint, state directory, token, or TLS behavior changes are made.

## Later slices

1. Extract Claude Code plugin assets and Claude adapter helper package.
2. Rename or publish the core Python package as appropriate while preserving CLI command names where practical.
3. Create the public ecosystem superproject with clean docs and optional submodules/checkouts.
4. Move private workflow and rough internal notes to `inter-agent-meta`.
5. Add cross-repository interoperability smoke tests.
