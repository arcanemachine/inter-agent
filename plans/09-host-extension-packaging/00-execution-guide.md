# Host Extension Packaging and Superproject Layout

Phase: 9 — Host Extension Packaging and Superproject Layout

## Purpose

Plan the transition from a single core repository with nested integration assets into a coordinated package layout where:

- the `inter-agent` core remains reusable and host-agnostic;
- Claude Code, Pi coding agent, and future host integrations are separate distributable packages;
- this repository acts as the superproject/container for project-wide instructions, roadmap, plans, architecture documentation, and cross-package coordination;
- extension packages consume the core as a package dependency or through an explicit local development checkout, not by implicitly relying on nested source paths.

This file is a planning artifact. Do not move packages, split repositories, or change runtime install behavior until the decisions and acceptance criteria below are explicitly accepted.

## Worker quick start

1. Read this file before changing Claude Code, Pi, or repository/package layout.
2. Do not flatten host integrations into one shared extension runtime. Claude Code and Pi use different extension systems.
3. Preserve the core boundary: protocol, server, transport, auth, routing, limits, and reusable command APIs belong to the core package; host UX belongs to host packages.
4. Treat managed Python environments as host integration runtime details, not as protocol state.
5. Keep custom local core checkout support for development.
6. Ask the user before choosing a repository-splitting mechanism, publishing package names, or changing live install behavior.

## Confirmed facts

These points are considered established for this plan:

1. Claude Code and Pi do not load the same kind of extension.
   - Claude Code plugins use `.claude-plugin/plugin.json`, skills, and Monitor-driven shell commands.
   - Pi extensions use an npm-style package with `package.json` and `pi.extensions` pointing at a TypeScript extension entry point.

2. A single host extension cannot literally run in both Claude Code and Pi.
   - The shared component is the inter-agent protocol/core package.
   - Host packages must remain host-specific adapters.

3. Claude Code does not require Python for Claude Code itself.
   - Python is a dependency of this integration because the inter-agent core is Python.
   - Claude installation and missing-Python errors must be explicit.

4. Pi exposes a user agent directory at `~/.pi/agent` by default, with override support through Pi's `PI_CODING_AGENT_DIR` behavior.
   - Existing Pi extension code already reads `~/.pi/agent/settings.json`.
   - A Pi-managed inter-agent runtime under `~/.pi/agent/inter-agent/` is consistent with current Pi layout, though Pi does not expose a generic extension data directory API.

5. The current Claude listener starts the server using `sys.executable -m inter_agent.core.server`.
   - If the listener runs from a managed venv, the auto-started server also runs from that venv.
   - The server does not need to be found separately on PATH in that case.

6. `claude-code-inter-session` is self-contained because it vendors its own Python application code inside the plugin package and uses pip only for third-party dependencies.
   - `inter-agent` should not copy that exact model by default because the reusable core is a real package intended for multiple host integrations.

7. Claude Code marketplaces support plugin `source` values that point at subdirectories of a marketplace repository.
   - This means the current repository can expose an installable Claude plugin while the plugin assets remain in a subdirectory, if that remains the chosen transitional path.

## Target architecture

The target architecture is a superproject plus distributable packages:

```text
inter-agent/                         # superproject / coordination repo
├── AGENTS.md                        # agent workflow
├── AGENTS.PLAN.md                   # roadmap
├── plans/                           # cross-package plans
├── docs/                            # cross-package docs, as needed
├── packages/                        # planned package/repo checkouts or package dirs
│   ├── inter-agent-core/            # Python core package, protocol, server
│   ├── claude-code-inter-agent/     # Claude Code plugin package
│   └── pi-inter-agent/              # Pi npm extension package
└── ...
```

The exact mechanism for `packages/` is intentionally undecided in this plan:

- regular directories in a monorepo;
- git submodules;
- git subtrees;
- external repositories referenced by documentation only;
- a staged migration from the current `integrations/` directories.

The user prefers a superproject shape. Before implementation, decide which mechanism supports day-to-day development, package publishing, and user installation with the least friction.

## Non-goals

- Do not create one combined extension that attempts to run in both Claude Code and Pi.
- Do not vendor the core source into each host package by default.
- Do not require users to clone the superproject or its submodules to use a host extension.
- Do not make host extension package installation depend on mutable local repository layout.
- Do not add declarative Claude Code monitors that race the skill-driven listener.
- Do not continue OpenCode packaging work under this phase unless it is explicitly brought into scope after Claude and Pi decisions are settled.

## Core package contract

The core package is the stable dependency consumed by host integrations.

Required core responsibilities:

1. Provide the local WebSocket protocol implementation.
2. Provide the server and lifecycle behavior.
3. Provide reusable client/control APIs where appropriate.
4. Provide console scripts required by existing integrations:
   - `inter-agent-server`
   - `inter-agent-connect`
   - `inter-agent-status`
   - `inter-agent-list`
   - `inter-agent-shutdown`
   - `inter-agent-pi`
   - `inter-agent-claude`
5. Keep host-specific UX in adapter modules or host packages.
6. Maintain protocol docs, schemas, examples, and conformance tests.

Required install sources:

- Development: editable install from a local checkout.
- Pre-release distribution: install from a git URL or git tag.
- Release distribution: install from a published package when available.

Open decision: choose the first supported non-local install source for host packages. Prefer a versioned source, such as a git tag or package registry release, over an unpinned branch.

## Managed Python environment model

Host integrations that need the Python core should manage an isolated Python environment unless the user explicitly points them at a local checkout.

Shared requirements:

1. Python must be treated as an integration dependency.
2. If Python is missing, show an actionable setup message.
3. If `python3 -m venv` is unavailable, show an actionable setup message.
4. Do not modify the user's system Python or user site packages.
5. Do not require `pipx` or `uv` for normal users.
6. Allow `uv` as an optional optimization only if the host package has a clear fallback to vanilla `python3 -m venv` and `pip`.
7. Do not store bus runtime state inside the managed venv.

Default venv locations currently proposed:

- Claude Code: `~/.claude/data/inter-agent/venv`
- Pi: `~/.pi/agent/inter-agent/venv`

Open decision: confirm these paths before implementation.

## Custom local core checkout model

Each host package must support development against a local core checkout.

Shared behavior:

1. If a custom core project path is configured, it wins over the managed venv.
2. The host package should use helper scripts from `<projectPath>/.venv/bin/` when that path is configured.
3. If the configured custom path does not contain the expected helper, fail with a message that includes the expected absolute path.
4. Relative and `~` paths should be expanded consistently.
5. Environment-variable expansion for `$VAR` and `${VAR}` is desired for path-like settings where host configuration supports it.

Existing Pi behavior:

- Pi already supports `interAgent.projectPath` in Pi settings.
- Pi already resolves `~` and relative paths for `projectPath` and `dataDir`.
- TODO currently asks for `$VAR` and `${VAR}` expansion.

Claude decision required:

- Choose the custom path mechanism for Claude:
  - environment variable such as `INTER_AGENT_PROJECT_PATH`;
  - Claude plugin `userConfig` if environment injection behavior is verified;
  - a config file read by wrapper scripts;
  - or more than one of the above.

Do not assume Claude `userConfig` environment variable names until verified in a live or documented source.

## Claude Code package plan

### Package role

The Claude Code package should be a thin plugin package that:

- provides the Claude plugin manifest and marketplace metadata;
- provides the `inter-agent` skill and bootstrap guidance;
- starts a Monitor-backed listener through the skill;
- invokes the core package through a managed venv or a configured local checkout;
- does not vendor the core package source by default.

### Proposed package contents

```text
claude-code-inter-agent/
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
├── skills/
│   └── inter-agent/
│       ├── SKILL.md
│       ├── bootstrap.md
│       └── bin/
│           └── inter-agent-claude
├── README.md
└── LICENSE.md
```

The `bin/inter-agent-claude` file should be a small wrapper, not the core implementation.

Wrapper responsibilities:

1. Resolve the configured local core checkout, if any.
2. Otherwise resolve the managed venv binary.
3. Execute the resolved `inter-agent-claude` script.
4. Preserve arguments exactly.
5. Print clear setup guidance when no usable helper exists.

### Claude bootstrap behavior

The Claude skill should expose or document a first-time setup flow that:

1. Checks for Python 3.10 or newer.
2. Creates the managed venv if it does not exist.
3. Installs the core package into the venv from the accepted source.
4. Verifies `inter-agent-claude status` through the wrapper.
5. Leaves normal message bus state in the core data directory, not the venv.

Open decision: choose whether this is an explicit `/inter-agent install-deps` command, automatic guidance after a missing-helper error, or both.

### Claude Monitor behavior

Current design constraints remain:

1. Do not declare a plugin-level monitor in `plugin.json`.
2. The skill starts exactly one persistent Monitor with the user-selected routing name.
3. The Monitor command should call the wrapper under `skills/inter-agent/bin/`.
4. The wrapper should avoid relying on shell `~` expansion inside Monitor commands.

### Claude acceptance tests

Static tests:

- plugin manifest has no declarative monitors;
- marketplace metadata is valid;
- wrapper exists and includes expected resolution branches;
- skill references the wrapper path rather than bare `inter-agent-claude`;
- bootstrap docs describe missing Python, venv creation, install source, and verification.

Live acceptance tests:

1. Install marketplace/plugin through Claude Code.
2. Run first-time setup on a machine without a local core checkout.
3. Connect as a named Claude session.
4. List sessions.
5. Send to another session.
6. Receive a direct message notification.
7. Disconnect cleanly.
8. Repeat using a local core checkout override.

## Pi package plan

### Package role

The Pi package should be a thin npm/Pi extension package that:

- provides Pi commands and tools;
- starts the existing Python listener through the core package;
- invokes the core package through a managed venv or a configured local checkout;
- preserves existing `interAgent.projectPath` behavior;
- does not require users to clone the core repository for normal installation.

### Proposed package contents

```text
pi-inter-agent/
├── package.json
├── src/
│   └── index.ts
├── README.md
└── LICENSE.md
```

### Pi helper resolution behavior

Resolution order:

1. If `interAgent.projectPath` is set, use helpers from `<projectPath>/.venv/bin/`.
2. Otherwise use helpers from `~/.pi/agent/inter-agent/venv/bin/`.
3. If the selected helper is missing, show an error that includes the expected absolute helper path.

The Pi extension should keep passing endpoint/state overrides to helper subprocesses through:

- `INTER_AGENT_HOST`
- `INTER_AGENT_PORT`
- `INTER_AGENT_DATA_DIR`

### Pi bootstrap behavior

Open decision: choose one of these UX flows.

Option A — explicit setup command:

- Add `/inter-agent install-deps` or `/inter-agent setup`.
- The command creates the managed venv and installs the core package.
- Normal commands fail with clear setup guidance until the setup command succeeds.

Option B — lazy auto-bootstrap:

- On first `/inter-agent connect` or `/inter-agent status`, detect missing managed venv.
- Ask for confirmation if Pi exposes an appropriate confirmation UI.
- Create the venv and install the core package.
- Continue the original command if setup succeeds.

Option C — documentation-only bootstrap:

- Keep runtime simple.
- Require the user to run documented setup commands manually.

Recommendation to decide later: prefer explicit setup first, then consider lazy auto-bootstrap after live testing.

### Pi acceptance tests

Static tests:

- resolver preserves `interAgent.projectPath` precedence;
- managed venv default path is documented and used only when no project path is configured;
- missing helper errors include absolute expected helper paths;
- path expansion covers accepted forms.

Live acceptance tests:

1. Install the Pi package normally.
2. Run setup with no local core checkout.
3. Connect as a named Pi session.
4. Send, broadcast, list, status, rename, and disconnect.
5. Receive an inbound notification.
6. Repeat with `interAgent.projectPath` pointing to a local core checkout.

## Superproject/package split sequence

Perform the split in small, reversible steps.

### Step 1: Document and freeze package boundaries

- Complete this plan.
- Update architecture docs to describe the intended superproject/package roles.
- Do not move code yet.

### Step 2: Stabilize core dependency contract

- Ensure the core package can be installed cleanly from local checkout and git URL.
- Ensure required console scripts work after install.
- Add build validation if needed.
- Decide version pinning rules for host packages.

### Step 3: Claude package extraction or staging

- Decide whether the Claude package first lives under `packages/claude-code-inter-agent/`, remains under `integrations/claude-code/`, or moves to a separate repository immediately.
- Implement wrapper and managed venv flow.
- Add marketplace/distribution docs.
- Run static and live acceptance tests.

### Step 4: Pi package extraction or staging

- Decide whether the Pi package first lives under `packages/pi-inter-agent/`, remains under `integrations/pi/`, or moves to a separate repository immediately.
- Implement managed venv fallback while preserving `interAgent.projectPath`.
- Add package distribution docs.
- Run static and live acceptance tests.

### Step 5: Superproject layout

- Decide whether `packages/` contains checked-in package directories, submodules, subtrees, or external checkout documentation.
- Update repository instructions for agents working across packages.
- Update README and architecture docs to reflect the chosen layout.

### Step 6: Distribution and discovery

- Publish or document the Claude plugin marketplace source.
- Publish or document the Pi package source and any npm/Pi package registry entry.
- Update the Pi packages page if appropriate.
- Update user-facing docs with stable install commands.

## Repository mechanism options

### Regular monorepo directories

Pros:

- easiest local development;
- atomic cross-package commits;
- no submodule commands.

Cons:

- publishing package roots may require extra tooling;
- host package git installs may clone more than needed unless package managers support subdirectories.

### Git submodules

Pros:

- separate repos with pinned revisions;
- superproject can coordinate exact tested combinations.

Cons:

- fragile for casual contributors;
- users must know recursive clone/update commands;
- not suitable as a runtime dependency mechanism.

### Git subtrees

Pros:

- vendored history without submodule checkout friction;
- package source is present in the superproject.

Cons:

- duplicated history;
- sync workflow is manual;
- easy to patch copied code in the wrong place.

### External repos referenced by docs

Pros:

- simplest distribution story per host;
- least coupling between package ecosystems.

Cons:

- no single checkout contains everything unless the user clones all repos manually.

Open decision: choose the mechanism after writing down release and development workflows.

## Versioning and compatibility

Required policy decisions:

1. How host packages declare the minimum compatible core version.
2. Whether host packages pin an exact core version, compatible range, or git tag.
3. How host packages upgrade the managed venv.
4. How users intentionally use a local development checkout instead of the packaged core.
5. How mismatch errors are detected and displayed.

Acceptance criteria for this section:

- A user can tell which core version a host package installed.
- A user can upgrade or reset the managed venv.
- A developer can point a host package at a local core checkout without editing package source.

## Security and operational notes

- Managed venvs contain executable code and should be treated as local application files, not message bus state.
- Token and server lifecycle state continue to use the core data directory resolution described in `SECURITY.md`.
- Host packages must not silently execute unreviewed install commands without a documented user action or host-appropriate confirmation.
- Missing Python, failed venv creation, and failed package install must produce actionable messages.
- Custom local checkout paths must be explicit and should not be guessed from unrelated current working directories.

## Documentation updates required before completion

- Root README: describe superproject/package roles.
- Architecture docs: describe core package boundary and host package boundary.
- Claude README: install, setup, custom path, managed venv, live acceptance test.
- Pi README: install, setup, custom path, managed venv, live acceptance test.
- SECURITY.md: clarify what is state, what is application code, and where managed venvs fit.
- AGENTS.md: update workflow notes if the repository layout or package roots change.
- AGENTS.PLAN.md: update this phase as sub-items complete.

## Stop conditions

Stop and ask the user before:

- moving code between repositories or package roots;
- choosing submodule vs subtree vs regular directories;
- changing the core package name;
- changing public CLI names;
- adding automatic dependency installation without explicit user confirmation behavior;
- publishing package names or marketplace entries;
- changing the security model or token/data directory behavior.

## Immediate next decisions

Before implementation, decide:

1. Should `packages/` initially contain real directories in this repo, submodules, subtrees, or only planned future repos?
2. What exact custom local core path mechanism should Claude use?
3. Should Claude setup be explicit `/inter-agent install-deps`, automatic after missing dependency, or both?
4. Should Pi setup be explicit `/inter-agent install-deps`, lazy auto-bootstrap, or documentation-only at first?
5. What core install source should host packages use before a registry release exists?
6. Should host packages pin a git tag for the core, or track a branch during early development?

## Completion criteria

This phase is complete when:

- the superproject/package layout is accepted and documented;
- the core package can be consumed by host packages from an accepted install source;
- Claude Code package distribution works through a documented install path;
- Pi package distribution works through a documented install path;
- both host packages support a managed venv and a custom local core checkout;
- both host packages handle missing Python and missing helpers with actionable errors;
- docs distinguish application files, managed venvs, config, and runtime state;
- static tests and live acceptance tests pass for the core, Claude Code, and Pi paths.
