# ⚠️ AGENT CONCERNS — READ FIRST

> **These concerns were raised by a previous agent working on Phase 6a and must be addressed before that phase is considered complete.**
> **A future agent should prioritize resolving these items before continuing with new Phase 6a work.**
>
> **Important:** Do not treat this list as ground truth. Validate each concern yourself by reading the relevant files, running the checks, and confirming the current state. These items are markers and guides for follow-up, not verified facts. If a concern no longer applies, update or remove it.

## Phase 6a: Pi Extension — Status Update

> **An agent has begun implementing the Pi extension.**
> **Repository:** `/workspace/projects/pi/pi-inter-agent`
> **Current state:** Core implementation complete, TypeScript compiles, listener spawn and message delivery verified against a live server.
> **Remaining work:** full interactive testing inside Pi, potential structural tests, documentation polish.

### Decisions made

- **Extension file placement:** Separate repo at `/workspace/projects/pi/pi-inter-agent` following existing Pi extension conventions (`package.json` with `pi.extensions`, `src/index.ts`, `README.md`, `AGENTS.md`).
- **Entry point resolution:** Uses `uv run inter-agent-pi ...` and `uv run inter-agent-connect ...` with `cwd` set to `/workspace/projects/inter-agent` and `PYTHONUNBUFFERED=1` for reliable output.
- **Notification truncation:** 1000 character limit.
- **Installation:** `pi install /workspace/projects/pi/pi-inter-agent` or `pi -e /workspace/projects/pi/pi-inter-agent/src/index.ts`.

### Open concerns (validate before continuing)

1. **TypeScript quality gate coverage**
   - `run-checks.sh` currently only runs Python checks.
   - The Pi extension repo has its own `npm run typecheck` but this is not wired into the inter-agent project's quality gate.
   - **Decision needed:** should `run-checks.sh` validate the extension file too?

2. **Testing strategy for the TypeScript extension**
   - The existing inter-agent test suite is entirely Python.
   - Live Pi extension tests require a running `pi` process.
   - **Decision needed:** what level of testing is acceptable — structural Python tests, a smoke test, or manual validation only.

3. **Full interactive testing inside Pi**
   - The extension has been validated to load without errors (`pi -e ./src/index.ts -p "say hello"`).
   - Listener spawn and message delivery have been verified at the Node.js spawn level.
   - **Not yet done:** running the full set of commands (`/inter-agent-connect`, `/inter-agent-send`, etc.) inside an interactive Pi session.

4. **Documentation polish**
   - README is drafted but may need updates after interactive testing.
   - No `settings.json` configuration is currently supported; this may or may not be desired.

---

# Roadmap

`inter-agent` is complete when it provides a stable localhost message bus for coding agents, a reliable Pi adapter, reproducible packaging and checks, documented protocol semantics, and operational safeguards that match the security model.

The roadmap is the high-level view. Detailed sub-agent-ready work items live under `plans/`, grouped by the same phases shown here. Phases 1 through 6 are the core completion path. Extra phases after that point are planned follow-on integrations. Ideas outside planned scope live in `IDEAS.md`.

## Scope

- Core protocol, server, client helpers, and conformance suite.
- Pi adapter as the primary host adapter.
- Packaging, command entry points, local quality gates, and release validation.
- Localhost, single-user security model as described in `SECURITY.md`.
- Adapter boundaries that make future host integrations practical without requiring them for completion.

## Phase 1: Workflow and Packaging Foundation

Goal: make the project installable, runnable, and checkable through stable commands and reproducible tooling.

Completion criteria:

- Package imports use a stable project namespace.
- Users can run server, core commands, and Pi adapter commands through package entry points.
- Setup docs use `uv sync` and `uv run`.
- A project-local quality gate runs formatting, linting, typing, tests, and spec validation.

## Phase 2: Protocol Contract and Conformance

Goal: align docs, schemas, implementation, and tests around a complete protocol contract.

Plan items: complete.

Completion criteria:

- Every protocol operation has schema coverage, examples where useful, and conformance tests.
- Error codes are canonical and documented.
- Capability exchange has documented semantics.
- Protocol docs and implementation agree on fields and behavior.

## Phase 3: Adapter Integration and Command UX

Goal: make the Pi adapter reliable as the primary user-facing host integration while preserving the core/adapter boundary.

Plan items: complete.

Completion criteria:

- Pi commands are covered by live-server integration tests.
- Adapter code calls reusable core APIs rather than relying on fragile script paths.
- Command output and failure modes are predictable for humans and host tooling.
- User docs present Pi as the primary workflow and `start.sh` as a development helper.
- If a live agent is needed, use the 'local-llama/default' agent when experimenting with Pi adapter support. Keep tasks tightly scoped and do not the let the agent run amok.

## Phase 4: Lifecycle and Routing UX

Goal: make routine operation smooth: routing is ergonomic, server state is managed, shutdown is safe, and status reflects reality.

Plan items: complete.

Completion criteria:

- Target resolution supports documented ergonomic rules without ambiguity.
- Server identity and PID metadata are created, refreshed, and removed predictably.
- Users can shut down the server safely through a command.
- Status and list commands report useful, accurate state.

## Phase 5: Security and Operational Hardening

Goal: strengthen the local security controls and resource boundaries promised by `SECURITY.md`.

Plan items: complete.

Completion criteria:

- Identity verification is stronger within the localhost threat model.
- Duplicate session IDs have explicit behavior.
- Connection count and payload shape limits prevent accidental resource abuse.
- Token and filesystem security behavior is documented and tested.

## Phase 6: Release Readiness

Goal: prepare the project for dependable use and future evolution.

Plan items:

1. `plans/06-release-readiness/03-versioning-and-changelog.md`
2. `plans/06-release-readiness/04-adapter-boundary-for-future-hosts.md`
3. `plans/06-release-readiness/05-final-completion-review.md`

Completion criteria:

- User, architecture, security, adapter, and agent docs describe the completed behavior without stale planning language.
- Source distributions and wheels build cleanly.
- Versioning and changelog practices are documented.
- Future host adapters can use the same core boundary without changing the core protocol.
- Repository checks pass through the documented commands.

## Phase 6a: Create inter-agent Pi extension

Goal: create a Pi coding agent extension that can be used to connect to the inter-agent server and communicate with other agents.

Plan items:

1. None yet (Still needs to be created)

Completion criteria:

- Pi coding agent sessions can join the inter-agent bus through a Monitor-backed listener.
- Pi coding agent users can send, broadcast, list, check status, connect, and disconnect through documented commands.
- Incoming bus messages are delivered as bounded Pi coding agent notifications with safe continuation behavior for long messages.
- Plugin or skill installation is documented and does not redefine core protocol semantics.
- Pi coding agent support passes the same project-local quality gate as core and Pi support.
- If a live agent is needed, use the 'local-llama/default' agent from the /workspace/.pi config when experimenting with Pi adapter support. Keep tasks tightly scoped and do not the let the agent run amok.

Extra notes:

- A local instance of Pi coding agent is available (`claude`) to ensure that the plugin works as expected.

## Phase 7: Claude Code Support

Goal: add Claude Code as a supported host integration after the core project is release-ready.

Design notes: `docs/CLAUDE_CODE_SUPPORT.md`

Plan items:

1. `plans/07-claude-code-support/01-monitor-first-adapter-design.md`
2. `plans/07-claude-code-support/02-claude-code-plugin-and-skill-scaffold.md`
3. `plans/07-claude-code-support/03-monitor-listener-and-session-state.md`
4. `plans/07-claude-code-support/04-claude-command-surface-and-reaction-policy.md`
5. `plans/07-claude-code-support/05-live-integration-tests-and-fixtures.md`
6. `plans/07-claude-code-support/06-packaging-docs-and-entry-points.md`

Completion criteria:

- Claude Code sessions can join the inter-agent bus through a Monitor-backed listener.
- Claude Code users can send, broadcast, list, check status, connect, and disconnect through documented commands.
- Incoming bus messages are delivered as bounded Claude Code notifications with safe continuation behavior for long messages.
- Plugin or skill installation is documented and does not redefine core protocol semantics.
- Claude Code support passes the same project-local quality gate as core and Pi support.
- If a live agent is needed, use the 'local-llama/default' agent from the /workspace/.pi config when experimenting with Pi adapter support. Keep tasks tightly scoped and do not the let the agent run amok.

Extra notes:

- A local instance of Claude Code is available (`claude`) to ensure that the plugin works as expected.

## Completion standard

A phase is complete when its plan items meet their acceptance criteria and the repository checks pass:

- `uv run pytest`
- `uv run ruff check .`
- `uv run black --check .`
- `uv run mypy src tests`

When package names or source layout change, update the mypy paths in this standard at the same time as the code change.
