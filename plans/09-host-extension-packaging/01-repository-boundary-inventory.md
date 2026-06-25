# Repository Boundary Inventory and Migration Plan

Phase: 9 — Host Extension Installability and Setup Simplification
Milestone: 5 — Repository/package split decision

## Purpose

Define the target repository and package boundaries before moving code. The split is driven by deployment ownership: the core bus should be independently installable, and each host integration should be independently installable through the host's idiomatic extension mechanism.

This document is an extraction map, not a command to immediately split repositories. It records what should move where, what should remain private, and what must stay invariant while the migration happens.

## Target repository topology

### Private wrapper repo

`inter-agent-meta` is the private/internal coordination repository. It may contain the maintainer's local workflow rules, internal agent instructions, scratch planning, and any rough material that should not ship in public user-facing repositories.

The private wrapper is not a runtime package and not the public entry point for users.

### Public ecosystem superproject

`inter-agent/inter-agent` is the public ecosystem landing repository. It should contain clean public documentation and coordination material for the inter-agent ecosystem, such as:

- public README and high-level architecture overview;
- public agent/contributor instructions that are suitable for the project;
- public roadmap or plan material when useful;
- pointers to the core package and host extension repositories;
- optional submodules or pinned checkouts for coordinated development, if that proves useful.

The public superproject should not be the runtime dependency that host extensions install. Host extensions depend on the core package and their own host-specific assets.

If the public superproject uses checked-in directories or submodules, use the existing conceptual naming scheme:

```text
inter-agent/
├── core/                   # inter-agent-core checkout/package
└── extensions/
    ├── claude-code/        # inter-agent-claude-code checkout/package
    └── pi/                 # inter-agent-pi checkout/package
```

Do not introduce unrelated coordination directories just because the repository is being split; keep private/internal workflow material in `inter-agent-meta`.

### Public package repositories

The likely package repositories are:

- `inter-agent/inter-agent-core`: Python package for the protocol, server, auth/state/routing, reusable client helpers, generic CLI, spec, schemas, examples, canonical error codes, and conformance tests.
- `inter-agent/inter-agent-claude-code`: Claude Code plugin package containing Claude plugin metadata, skill assets, wrappers/bootstrap, and Claude-specific adapter code that depends on the core package.
- `inter-agent/inter-agent-pi`: Pi extension package containing Pi package metadata, TypeScript extension code, Pi-specific runtime resolution, and any Pi-specific adapter code that depends on the core package.
- Future host repositories such as `inter-agent/inter-agent-opencode` follow the same pattern: thin host integration, shared core dependency.

Keep existing user-facing CLI names where practical, including `inter-agent-server`, `inter-agent-claude`, and `inter-agent-pi`. Repository and package names can become more precise without forcing users to learn new command names.

## Runtime and installation model

The long-term runtime model is:

1. The core is independently installable on a user's workstation, preferably from PyPI once release packaging is ready.
2. Local directory installs, GitHub/archive installs, and development `PATH` overrides remain available for development and pre-release workflows.
3. Each host extension installs or resolves the core in the idiomatic way for that host:
   - Claude Code can use plugin config, a skill-local wrapper, and a gated managed Python venv.
   - Pi can use extension settings, explicit helper overrides, a managed venv path, or documented manual setup.
   - Future hosts should use their own host-native install/config surfaces.
4. Host extensions may use different core runtime installs and still share the same bus when endpoint and state settings match.
5. Separate runtime installs must never imply separate default token or state directories.

The core package is the runtime dependency. The public superproject coordinates the ecosystem; it should not become an implicit runtime dependency.

## Boundary rules

1. Core owns protocol semantics. Host extensions must not redefine protocol operation behavior, error meaning, auth, state, target resolution, or server lifecycle rules.
2. Host extensions own host UX. Skills, slash commands, notification policy, plugin manifests, extension metadata, host-specific wrappers, and host install guidance live with the host extension.
3. Cross-harness interoperability depends on bus endpoint and state, not helper location.
4. Public docs should be stable and user-facing. Rough notes, local plans, and private agent workflow belong in `inter-agent-meta` unless deliberately cleaned up for public use.
5. Package extraction must keep tests with the code they validate, while retaining public ecosystem smoke tests where cross-repo behavior matters.

## Current file ownership inventory

| Current path | Future home | Notes |
| --- | --- | --- |
| `README.md` | Public superproject, with extracted package-specific sections copied/trimmed into child repos | Current file mixes ecosystem overview, core CLI, Claude, and Pi setup. Split by audience during extraction. |
| `ARCHITECTURE.md` | Mostly `inter-agent-core`; ecosystem overview may be summarized in public superproject | Core architecture owns protocol/server/lifecycle. Host-specific adapter sections should move to extension docs. |
| `SECURITY.md` | Mostly `inter-agent-core`; extension repos may add host-specific security notes | Token/state/auth model is core. Monitor/plugin/package-manager caveats belong with host extensions. |
| `spec/` | `inter-agent-core` | AsyncAPI, schemas, examples, and `spec/error-codes.md` are protocol contract material. |
| `src/inter_agent/core/` | `inter-agent-core` | Core runtime implementation. |
| `src/inter_agent/adapters/claude/` | `inter-agent-claude-code` or a Claude-specific Python package inside that repo | Depends on core APIs. Should leave the core package when extension repos split. |
| `src/inter_agent/adapters/pi/` | `inter-agent-pi` or a Pi-specific Python package inside that repo | Depends on core APIs. Should leave the core package when extension repos split. |
| `integrations/claude-code/` | `inter-agent-claude-code` | Claude Code plugin metadata, skill, wrapper, bootstrap, and README. |
| `integrations/pi/` | `inter-agent-pi` | Pi extension package metadata, TypeScript extension, README, lockfile. |
| `.claude-plugin/marketplace.json` | Public superproject while it acts as a marketplace; possibly Claude repo if marketplace ownership changes | Current marketplace points at the Claude plugin subdirectory. Revisit after split because Claude Code local/GitHub install behavior drives this location. |
| `package.json` at repo root | Transitional; eventually `inter-agent-pi` or public superproject only if it remains an install convenience | Root Pi metadata exists because Pi git installs load repo root. Long-term direct Pi install should come from the Pi extension repo. |
| `pyproject.toml`, `uv.lock`, `MANIFEST.in`, `inter-agent`, `scripts/`, `run-checks.sh` | Mostly `inter-agent-core`; extension repos get their own package metadata/check scripts | Current Python package owns core plus adapters. Extraction must separate package metadata and console scripts. |
| `tests/conformance/` | `inter-agent-core` | Protocol black-box semantics. |
| Core unit tests under `tests/` | `inter-agent-core` | Tests for config, token, lifecycle, client helpers, spec validation, filesystem permissions, core CLI. |
| Claude tests under `tests/` | `inter-agent-claude-code` | Tests for Claude CLI/listener/plugin/skill/wrapper. Keep only cross-harness smoke tests outside if needed. |
| Pi tests under `tests/` | `inter-agent-pi` | Tests for Pi CLI/listener/extension static behavior. Keep only cross-harness smoke tests outside if needed. |
| Cross-harness integration validation | Public superproject or a dedicated ecosystem smoke-test suite | Validates independently installed packages still share the bus. |
| `CHANGELOG.md` | Package-specific; initially `inter-agent-core`, plus extension changelogs when split | Avoid one changelog claiming releases for packages it no longer ships. |
| `LICENSE.md` | All public repos | Keep licensing explicit in every public repo. |
| `AGENTS.md` | Public superproject and each public repo, cleaned for public contribution context | Private/internal rules stay in `inter-agent-meta`. |
| `PLAN.md` and `plans/` | Public superproject if kept public; private `inter-agent-meta` for rough/internal planning | Keep only stable public roadmap material in public repos. |
| `IDEAS.md`, `TODO.md` | Default to `inter-agent-meta` unless curated for public roadmap | Treat as clutter until deliberately cleaned. |
| `docs/` | Split by subject | Security baseline/threat-model docs likely belong with core security docs unless they are stale or internal. |
| `dist/`, caches, virtualenvs | No public repo | Generated/local artifacts stay untracked or ignored. |

## Small cleanup completed in this milestone

`ERROR_CODES.md` moved to `spec/error-codes.md` because canonical error codes are part of the protocol contract. References, packaging manifests, and tests should treat it as spec/core material.

## Migration sequence

1. Stabilize the core package boundary in the current repository.
   - Confirm which `src/inter_agent/*` modules are core and which are host-specific.
   - Decide whether the Python distribution name becomes `inter-agent-core` while preserving the import namespace and generic CLI names.
   - Keep the protocol spec, conformance tests, and core docs together.
2. Extract host-specific Python adapter code from the core package boundary.
   - Claude-specific Python helper code moves with the Claude Code extension package or a package owned by that repo.
   - Pi-specific Python helper code moves with the Pi extension package or a package owned by that repo.
   - Existing command names can remain as extension-provided entry points.
3. Prepare independent extension package metadata.
   - Claude repo owns plugin manifest, marketplace/install docs, skill assets, wrapper/bootstrap, and tests.
   - Pi repo owns Pi package manifest, lockfile, TypeScript extension, runtime setup docs, and tests.
4. Create or populate public package repositories.
   - `inter-agent-core`
   - `inter-agent-claude-code`
   - `inter-agent-pi`
5. Create the public `inter-agent/inter-agent` superproject.
   - Add clean ecosystem docs.
   - Link or submodule child repositories only if that improves public development/install workflows.
6. Create or maintain private `inter-agent-meta` separately.
   - Move rough/internal plans and private agent workflow there.
   - Keep public repos free of private workflow assumptions.
7. Switch managed runtime bootstrap sources from temporary GitHub `main` archives to stable release sources.
   - Prefer PyPI for core package installs once released.
   - Keep local directory and pinned archive options for development and reproducibility.
8. Add cross-repository validation.
   - Verify Claude and Pi installed from their own repos can share the same default bus.
   - Verify explicit isolation still requires different endpoint/state settings.

## Do not do yet

- Do not add submodules or subtrees until repository ownership and install commands are ready.
- Do not publish package names without maintainer approval.
- Do not change default `host`, `port`, `dataDir`, token location, or bus discovery behavior as part of the split.
- Do not rename public CLI commands solely to match repository names.
- Do not move private/internal workflow material into public repos by default.

## Acceptance result

Milestone 5 decision: target a private `inter-agent-meta` wrapper plus a public `inter-agent/inter-agent` ecosystem superproject coordinating independently deployable `inter-agent-core`, `inter-agent-claude-code`, `inter-agent-pi`, and future extension repositories.

Physical repository splitting is deferred until the core package boundary, extension-owned adapter code, public docs, and release install sources are ready. The immediate concrete cleanup is to classify protocol error code documentation under `spec/` so it follows the future core package boundary.
