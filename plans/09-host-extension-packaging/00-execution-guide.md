# Host Extension Installability and Setup Simplification

Phase: 9 — Host Extension Installability and Setup Simplification

## Purpose

Make the Claude Code and Pi integrations easier to install, verify, and configure without changing the core protocol semantics or fragmenting the default inter-agent bus state.

This plan replaces the earlier assumption that repository/package splitting must be the first step. The immediate problem is narrower: the integrations mostly work today, but persistent installation and setup are difficult to reason about. Start by proving installability and reducing configuration friction. Revisit repository/package separation only after the installability and setup behavior is understood.

## Required first step: discuss with the user

Before implementing code, package metadata, managed venv behavior, or repository layout changes, stop and discuss this plan with the user.

The discussion is required because the desired shape changed during planning and earlier conclusions were too broad. Confirm the immediate objective, assumptions, and first milestone before changing runtime behavior.

At minimum, confirm:

1. Whether the immediate goal is still to make the Claude Code plugin persistently installable.
2. Whether the first implementation should keep the existing runtime assumption that `inter-agent-claude` is on PATH.
3. Whether managed Python environments should be deferred until plugin installability is proven.
4. Whether Pi changes should wait until after the Claude installability proof.
5. Whether repository/package splitting should remain a later option rather than the first milestone.

Do not proceed past this checkpoint without explicit user acceptance.

## Eventual packaging direction

The intended end state is not a permanently tangled repository where the core, Claude Code plugin, and Pi extension all depend on a checkout layout.

The expected direction is tentative: it is understood to be a good direction based on current information, but it should be reviewed again before execution when the final packaging state is determined. The likely shape is a cleaner monorepo-ish or superproject layout with explicit package boundaries:

- the host-agnostic `inter-agent` core is published as a reusable Python package, such as a PyPI package;
- the Claude Code plugin is independently installable and deployable through Claude Code's plugin system;
- the Pi extension is independently installable and deployable through Pi's extension system;
- host extensions remain thin, host-specific adapters that install or invoke the shared core runtime rather than redefining protocol behavior;
- separate host extension runtimes still default to the same inter-agent bus endpoint and state so cross-harness messaging works without extra configuration.

The current phase is a half step toward that end state. It keeps the combined repository layout long enough to prove persistent extension installability and runtime setup behavior before deciding whether to keep a monorepo, move to a package-oriented superproject, or split repositories.

## Key model: runtime source and bus state are separate

Keep these two concerns independent.

### Core runtime source

The core runtime source is where a host integration finds executable helpers such as `inter-agent-claude`, `inter-agent-pi`, and `inter-agent-server`.

Possible runtime sources:

- global install on PATH;
- local development checkout, for example `<projectPath>/.venv/bin/inter-agent-*`;
- host-managed venv, for example a Claude-managed or Pi-managed Python environment;
- future package registry install.

### Bus endpoint and state

The bus endpoint and state determine which message bus a host joins.

Relevant values:

- `host`;
- `port`;
- `dataDir` / token location;
- `INTER_AGENT_HOST`;
- `INTER_AGENT_PORT`;
- `INTER_AGENT_DATA_DIR`;
- `INTER_AGENT_CONFIG`.

### Required invariant

Different host integrations may use different core runtime sources and still interoperate, provided they use compatible protocol versions and the same bus endpoint/state.

Do not make per-extension token/data directories the default. A Claude-managed venv and a Pi-managed venv are acceptable. A Claude-only default token directory and a Pi-only default token directory are not acceptable for normal cross-harness use.

Default cross-harness operation should continue to use the core defaults unless explicitly configured otherwise:

- `127.0.0.1:16837`;
- platform default inter-agent state directory, such as `~/.local/state/inter-agent` on Linux.

Intentional isolation should require explicit configuration, such as a different `dataDir` and/or `port`.

## Confirmed facts

1. Claude Code and Pi use different extension systems.
   - Claude Code plugins use `.claude-plugin/plugin.json`, skills, and Monitor-driven shell commands.
   - Pi extensions use an npm-style package with `package.json` and `pi.extensions` pointing at a TypeScript extension entry point.

2. A single extension runtime cannot serve both hosts.
   - The shared component is the inter-agent core package/protocol.
   - Host-facing integration code remains host-specific.

3. Claude Code does not require Python for Claude Code itself.
   - Python is required only because this integration uses the Python inter-agent core.
   - Missing Python must be handled as an integration setup problem, not assumed away.

4. The current Claude Code integration is development-loadable with `claude --plugin-dir ./integrations/claude-code`.
   - Persistent plugin installation is not proven until `/plugin marketplace add` and `/plugin install` have been tested.

5. Claude Code marketplaces support plugin sources that point at repository subdirectories.
   - A root `.claude-plugin/marketplace.json` can point at `./integrations/claude-code` if the current repository remains the marketplace source.

6. The current Claude plugin must not declare a plugin-level monitor.
   - Existing static tests enforce that declarative monitors are absent because a declarative monitor would race the skill-driven listener.

7. The current Claude listener starts the server with `sys.executable -m inter_agent.core.server`.
   - If a later managed venv is used, the listener-started server runs from that same venv.

8. Pi uses `~/.pi/agent` as the default agent directory and can be configured through Pi's agent-dir behavior.
   - The existing Pi extension already reads `~/.pi/agent/settings.json`.
   - Pi does not expose a generic extension data directory API in the extension context.

9. The `claude-code-inter-session` project vendors its own Python application code into the plugin and installs only third-party dependencies into a venv.
   - That model is informative but not automatically appropriate for inter-agent because inter-agent is intended to be a reusable core package used by multiple host integrations.

## Non-goals for the first milestone

Do not do these before the first Claude persistent-install proof:

- split repositories;
- move integration directories into `packages/`;
- add submodules or subtrees;
- vendor the core source into host extensions;
- implement managed venv bootstrap;
- change default token/data directory behavior;
- redesign Pi packaging;
- add declarative Claude monitors.

These may be revisited after the first proof if they are still necessary.

## Milestone 1: Prove Claude Code persistent plugin installation

### Goal

Answer the immediate question: can the existing Claude Code plugin be installed persistently through Claude Code's plugin system from this repository?

### Minimal intended change

Add root marketplace metadata:

```text
.claude-plugin/marketplace.json
```

The marketplace should list the `inter-agent` plugin with source:

```json
"source": "./integrations/claude-code"
```

Do not change the runtime model in this milestone. Keep the existing assumption that `inter-agent-claude` must be available to the Claude session, likely through PATH or an existing local development install.

### Why this comes first

If persistent plugin install does not work, managed venv design and repo splitting are premature. If it does work, the remaining problem is runtime setup convenience, not plugin discovery.

### Implementation steps

1. Confirm with the user that this milestone is the immediate target.
2. Add `.claude-plugin/marketplace.json` at repository root.
3. Keep `integrations/claude-code/.claude-plugin/plugin.json` minimal unless metadata changes are required for install.
4. Add or update static tests for marketplace metadata.
5. Update Claude integration documentation to distinguish:
   - development load with `claude --plugin-dir`;
   - persistent install with `/plugin marketplace add` and `/plugin install`.
6. Do not add managed venv behavior in this milestone.
7. Run appropriate checks.
8. Perform a live Claude Code install test.

### Live acceptance test

From a Claude Code session, test a local marketplace first if possible:

```text
/plugin marketplace add /workspace/projects/inter-agent
/plugin install inter-agent
```

Then test the GitHub form when appropriate:

```text
/plugin marketplace add https://github.com/arcanemachine/inter-agent
/plugin install inter-agent
```

After install, verify that `/inter-agent` skill commands are available. If `inter-agent-claude` is missing, that is not a failure of plugin installation; it is the next milestone's setup problem.

### Acceptance criteria

- Claude Code recognizes the repository as a plugin marketplace.
- Claude Code can install the `inter-agent` plugin from the marketplace.
- The installed plugin exposes the `inter-agent` skill.
- Any runtime failure due to missing `inter-agent-claude` is documented as a setup issue for Milestone 2.

### Recorded result

Milestone 1 is complete. The repository has root Claude marketplace metadata pointing at the Claude plugin subdirectory with relative source `./integrations/claude-code`. `claude plugin validate --strict .` and `claude plugin validate --strict integrations/claude-code` pass. Local persistent installation with `claude plugin marketplace add /workspace/projects/inter-agent`, `claude plugin install inter-agent`, and `claude plugin details inter-agent` proves the installed plugin exposes the `inter-agent` skill.

The runtime model is unchanged: persistent plugin installation installs Claude Code assets only. `inter-agent-claude` still needs to be available from the Claude Code session environment until Milestone 2 changes that setup story.

## Milestone 2: Simplify Claude runtime setup

### Goal

Reduce or remove the current requirement that users manually arrange for `inter-agent-claude` to be on PATH.

### Inputs from Milestone 1

Use the results of the persistent install proof to decide how much runtime setup should be automated.

### Options

#### Option A: Keep PATH/global install and improve guidance

Users install the core package separately, and the plugin keeps calling `inter-agent-claude`.

Pros:

- smallest runtime change;
- preserves current behavior;
- simple to debug.

Cons:

- still requires users to understand Python package installation;
- not zero-config.

#### Option B: Managed Claude venv

The plugin guides or performs setup of a managed venv, for example:

```text
~/.claude/data/inter-agent/venv
```

The skill or wrapper then invokes `inter-agent-claude` from that venv.

Pros:

- no PATH requirement;
- isolated from system Python;
- aligns with Claude plugin installation expectations.

Cons:

- requires Python to be installed;
- requires setup UX and error handling;
- raises version/update policy questions.

#### Option C: Custom local checkout only

The plugin requires a configured local core checkout and uses `<projectPath>/.venv/bin/inter-agent-claude`.

Pros:

- good for development;
- simple if users already work from a checkout.

Cons:

- not a good normal-user install story.

### Required behavior regardless of option

- Missing helper errors must include the expected command/path.
- Missing Python errors must be actionable if managed venv setup is introduced.
- The plugin must not change the default bus token/data directory to a Claude-specific location.
- A local development checkout override should remain possible.

### Recorded decision

Milestone 2 uses a bundled Claude skill wrapper and guided managed-runtime bootstrap rather than a silent install. The wrapper resolves runtime helpers in this order:

1. `INTER_AGENT_CLAUDE_HELPER`, an exact executable path override.
2. Claude plugin `project_path` config, using `<project_path>/.venv/bin/inter-agent-claude`.
3. Claude-managed venv helper at `~/.claude/data/inter-agent/venv/bin/inter-agent-claude`.
4. `inter-agent-claude` on PATH.
5. A short setup-needed message that points to runtime setup docs.

The managed bootstrap creates or reuses `~/.claude/data/inter-agent/venv` only after explicit user approval and a required `--yes` flag. It does not change the default inter-agent bus endpoint or state directory. The temporary pre-release install source is the GitHub `main` archive; future release work should switch managed bootstrap to a stable PyPI release, tag, or pinned archive.

### Recorded result

Milestone 2 is complete. The Claude plugin now ships a skill-local wrapper and gated bootstrap script. The skill invokes the wrapper for Monitor and short-lived commands, documents the `project_path` plugin config and `INTER_AGENT_CLAUDE_HELPER` override, and requires explicit approval before managed runtime installation. Static tests cover wrapper resolution, setup-needed output, bootstrap approval gating, plugin config metadata, and package data. `claude plugin validate --strict .`, `claude plugin validate --strict integrations/claude-code`, and the repository quality gate pass. Local persistent installation with `claude plugin marketplace add /workspace/projects/inter-agent` and `claude plugin install inter-agent --config project_path=/workspace/projects/inter-agent` still exposes the `inter-agent` skill.

The managed bootstrap source remains the GitHub `main` archive as a temporary pre-release choice. Switching to PyPI, a release tag, or a pinned archive is future release packaging work.

## Milestone 3: Pi setup and distribution parity

### Goal

Review the Pi extension after the Claude installability proof and decide what is needed to make Pi equally easy to install and configure.

### Current Pi behavior

The Pi extension currently resolves a configured inter-agent project path and uses helper scripts from the checkout's `.venv/bin` directory. This works but requires users to clone/setup the core repository or configure a path.

### Required invariants

- Preserve `interAgent.projectPath` for development and custom local installs.
- Keep default bus state shared with Claude and other hosts.
- Do not default Pi to a Pi-specific token/data directory.
- Missing helper errors should include expected absolute paths.

### Possible improvements

#### Option A: Documentation and error messages only

Keep current projectPath-based behavior, but improve setup instructions and errors.

#### Option B: Managed Pi venv fallback

If no `interAgent.projectPath` is configured, use a Pi-managed venv, for example:

```text
~/.pi/agent/inter-agent/venv
```

This venv contains the core package. The extension invokes helpers from the venv.

#### Option C: Separate Pi package/repository

Create or extract a `pi-inter-agent` npm/Pi package for distribution. The package may still use Option A or B for the core runtime.

### Open decisions

1. Does Pi need a managed venv now, or is better documentation enough?
2. Should Pi setup be explicit, lazy auto-bootstrap, or manual documentation-only?
3. Should Pi distribution be solved in this repository first or through a separate package repository?
4. Does Pi support installing this nested package directly, or is a separate root package required?

## Milestone 4: Cross-harness interoperability validation

### Goal

Prove that the setup model keeps cross-harness communication working.

### Required scenarios

1. Claude using its current/global runtime can talk to Pi using configured `projectPath`.
2. Claude using a future managed runtime can talk to Pi using configured `projectPath`.
3. Claude and Pi using separate managed runtimes can talk to each other with zero bus configuration.
4. Both hosts can connect to an explicitly configured shared server/state directory.
5. Intentional isolation works only when endpoint/state settings are explicitly changed.

### Key acceptance rule

Separate runtime installs must not imply separate buses.

## Milestone 5: Repository/package split decision

### Goal

Revisit repository/package separation only after installability and setup behavior are understood.

### Possible end states

#### Keep current repository layout

The current repository remains the source for core and integration assets. Claude marketplace metadata may point at a subdirectory.

#### Superproject with `packages/`

This repository becomes a coordination superproject with package directories such as:

```text
packages/inter-agent-core/
packages/claude-code-inter-agent/
packages/pi-inter-agent/
```

#### Separate package repositories

The core, Claude plugin, and Pi extension become separate repositories, while this repository becomes documentation/planning coordination or remains the core repository.

### Do not decide prematurely

Do not choose submodules, subtrees, package workspaces, or repository splits before Milestones 1 and 2 are complete unless the user explicitly changes priorities.

## Documentation updates by milestone

### Milestone 1

- Claude README: persistent install vs development load.
- Root README: status of Claude persistent plugin install.
- Plan/roadmap: record acceptance results.

### Milestone 2

- Claude README: runtime setup, custom local checkout, missing Python/helper behavior.
- SECURITY.md if managed venv/application files need clarification.

### Milestone 3

- Pi README: setup path, custom `projectPath`, managed runtime if introduced.
- Root README: Pi distribution status.

### Milestone 4

- Root README or architecture docs: cross-harness interoperability model.

### Milestone 5

- AGENTS.md, PLAN.md, README.md, and architecture docs if repository/package layout changes.

## Testing and verification

### Static checks

Add or update tests as behavior changes:

- Claude marketplace metadata validation;
- Claude plugin manifest still declares no monitors;
- error message text includes expected helper paths where applicable;
- Pi resolver precedence tests if resolver behavior changes;
- docs/static tests for new package metadata where useful.

### Local checks

For code changes, run the full repository gate:

```bash
./run-checks.sh
```

For documentation-only plan wording, full checks are not required unless generated/checked files are touched or the user asks.

### Live checks

Live host acceptance is required before calling installability done:

- Claude Code `/plugin marketplace add` and `/plugin install`;
- Pi extension install/load path when Pi changes are introduced;
- cross-harness message send/receive after setup behavior changes.

## Stop conditions

Stop and ask the user before:

- introducing managed venv bootstrap;
- changing default `dataDir` or token state behavior;
- changing public CLI names;
- splitting repositories or moving package roots;
- adding submodules or subtrees;
- making automatic dependency installation run without explicit confirmation or a clearly accepted UX;
- publishing package names or marketplace entries;
- declaring Claude or Pi installation complete without live verification.

## Immediate next action

Work Milestone 2 next: decide and implement the Claude runtime setup model that reduces or removes the manual requirement for `inter-agent-claude` to be on `PATH`. Before changing runtime behavior, confirm the Milestone 2 setup option with the user.
