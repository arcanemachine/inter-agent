# Agent Workflow

This file is for coding agents working in this repository.

## Role assignment

This repository uses exactly two agent roles:

- `leader` — plans, prepares bounded task packets, and dispatches work.
- `executor` — executes one bounded task packet at a time.

Before task work begins, the user must explicitly assign one of these roles to the agent. An agent with no assigned role must stop and ask for one. An agent assigned an unknown role must stop and list the available roles (`leader`, `executor`).

- A `leader` must follow `.agents/roles/leader.md` after reading this file.
- An `executor` must follow `.agents/roles/executor.md` after reading this file.

The authoritative active-plan file is `.agents/PLAN.md`. Detailed active task packets live in `.agents/plans/`.

## Core rules

1. Preserve universal core boundaries; keep host-specific behavior in adapters.
2. Keep behavior aligned with the protocol spec in `spec/`.
3. When adding protocol operations, update spec, implementation, and tests together.
4. Keep security behavior consistent with `SECURITY.md`.
5. Keep informational documents evergreen (`README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `ROADMAP.md`, `AGENTS.md`).
6. Write docs as stable descriptions of what the project is and how it works; avoid temporary status language and date-specific status notes.
7. Use precise project terminology. Prefer `sub-agent` for delegated coding-agent work; avoid overloaded role names.
8. Use `.agents/PLAN.md` only for short-term active work. Use `ROADMAP.md` for accepted medium- and long-term direction. Use `docs/plans/**` for future execution notes that are more detailed than the roadmap but not active work. Keep exploratory work in `docs/IDEAS.md` until it is promoted into the roadmap or active plan.
9. When active plan work is completed, update or remove the relevant plan item. Update `README.md`, `ARCHITECTURE.md`, and `SECURITY.md` only for behavior or architecture that now exists.
10. Prefer concrete types over `Any`; use `Any` only when a concrete type is impractical.
11. Match existing project style and conventions in code, tests, docs, and commits.
12. The `leader` keeps commits atomic per logical step.
13. The `leader` uses [Conventional Commits](https://www.conventionalcommits.org/) style for commits: `type: description` (e.g., `fix: prevent duplicate names on concurrent connections`, `test: add concurrent duplicate name rejection test`).
14. The `leader` commits completed work before handing back unless the user explicitly requests no commits.
15. After completing a task, summarize what was done, describe what is coming next, and continue with the plan unless there is an important reason to stop, such as a required user decision or significant new information.

## Required workflow for every feature/change

1. Add or update tests for the behavior change.
2. Run all configured repository checks locally before finishing, including tests, linters, formatters/style checks, type checkers, and spec validation. Use `./run-checks.sh` for the full gate. It runs `uv sync --locked` and the current required commands:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run black --check .`
   - `uv run mypy src tests`

   Exception: for documentation-only wording changes (for example, skill prompt wording that does not affect code, package metadata, schemas, or generated artifacts), do not spend time running the full gate unless the user asks for it or the edit touches a checked/generated document.
3. The `leader` commits completed work when the task is done, keeping commits atomic per logical step.
4. When completing a plan phase, provide a user acceptance test when possible, along with the commit hash where that acceptance test applies.
5. If Git needs an explicit author identity for a maintainer-requested commit, use `Nicholas Moen <arcanemachine@gmail.com>` unless instructed otherwise.
6. Keep docs evergreen and scoped:
   - Agent process belongs in `AGENTS.md`.
   - User-oriented product docs belong in `README.md`.
   - Todo items (e.g. bugs, necessary fixes) belong in `TODO.md`.
   - Short-term active work belongs in `.agents/PLAN.md`.
   - Accepted medium- and long-term direction belongs in `ROADMAP.md`.
   - Future execution notes belong in `docs/plans/**`.
   - Exploratory ideas belong in `docs/IDEAS.md`.
   - Security model and assumptions belong in `SECURITY.md`.

## Workflow notes

- After changing package entry points or project metadata, run `uv sync --locked` before command smoke tests so generated scripts reflect `pyproject.toml`.
- For live-server tests, prefer `unused_tcp_port` over fixed ports to avoid local collisions.
- For protocol examples, keep example `op` values aligned with schema filenames so validation can stay table-driven.

## Host extension packaging notes

- Keep the core runtime source separate from bus state. Host extensions may use different helper installs, but default interoperability depends on the shared default endpoint and state directory.
- Claude Code marketplace metadata lives at root `.claude-plugin/marketplace.json`. A marketplace entry can point to a plugin subdirectory with a relative `source`, such as `./integrations/claude-code`; absolute sources are invalid.
- Claude marketplace metadata should include `$schema`, `name`, `version`, `description`, `owner`, and `plugins`. Include plugin `author` metadata and keep it aligned with `integrations/claude-code/.claude-plugin/plugin.json` so `claude plugin validate --strict` stays clean.
- Useful Claude CLI checks:
  - `claude plugin validate --strict .`
  - `claude plugin validate --strict integrations/claude-code`
  - `claude plugin marketplace add /path/to/inter-agent`
  - `claude plugin install inter-agent`
  - `claude plugin details inter-agent`
- Claude persistent plugin installation installs Claude Code assets and uses a bundled wrapper in `skills/inter-agent/bin/`. Runtime resolution is: `INTER_AGENT_CLAUDE_HELPER`, plugin `project_path` config, Claude-managed venv, then `inter-agent-claude` on `PATH`.
- Pi git installability from this repository uses root `package.json` with `pi.extensions` pointing at `./integrations/pi/src/index.ts`. The nested `integrations/pi/package.json` remains for local/separate package installs. Pi runtime resolution is: `INTER_AGENT_PI_HELPER`, configured `interAgent.projectPath`, legacy `~/.local/share/inter-agent` if present, Pi-managed venv, then helper commands on `PATH`.
- The target split direction is a private `inter-agent-meta` wrapper, a public `inter-agent/inter-agent` ecosystem superproject, and independently deployable `inter-agent-core`, `inter-agent-claude-code`, `inter-agent-pi`, and future extension repos. Keep internal workflow material private by default and keep protocol material with core.

## Design boundary

- `src/inter_agent/core/`: transport/auth/identity/routing/limits.
- `src/inter_agent/adapters/`: UX and host-integration behavior.
- `spec/`: protocol contract, examples, and canonical error code docs.
- `tests/conformance/`: black-box protocol semantics.

When the package layout changes, update this section and the required check paths in the same change.
