# Agent Workflow

This file is for coding agents working in this repository.

## Role assignment

This repository uses exactly two agent roles:

- `leader` — plans, prepares bounded task packets, and dispatches work.
- `executor` — executes one bounded task packet at a time.

Before task work begins, the user must explicitly assign one of these roles to the agent. An agent with no assigned role must stop and ask for one. An agent assigned an unknown role must stop and list the available roles (`leader`, `executor`). This may be bypassed only if explicitly authorized by the user.

- A `leader` must follow `.agents/roles/leader.md` after reading this file.
- An `executor` must follow `.agents/roles/executor.md` after reading this file.

Role assignment and task dispatch are separate. A newly assigned executor without a task packet finishes the short onboarding in its role document, does not inspect project work, and waits for the leader. The leader alone selects active work, prepares and commits its packet, obtains dispatch authorization, and assigns it.

### Ordered onboarding

Mandatory onboarding reads are sequential, not a set that may be opened in parallel:

1. Every role reads this file completely before opening another project file.
2. The assigned role then reads only its role document.
3. A `leader` next reads `.agents/PLAN.md` and, when it links current work, that one active packet. The packet is part of mandatory active-state review; all other project content remains subject to the leader's filename-inventory and user-approval boundary.
4. An unassigned `executor` stops after its role document and waits. After dispatch, it reads the named packet before any packet-authorized references.
5. Once the task language is known, read the relevant `/workspace/.agents/languages/<language>/` file or `/workspace/.agents/languages/<language>.md` before language-specific task work. A filename-only root inventory is sufficient to identify the language; do not open a manifest early just to infer it.

When discovering additional agent or LLM guidance, inspect filenames only at first. Check case-insensitively for `*usage*.md`, `*claude*.md`, `*agent*.md`, and `.claude/`, while pruning `.git`, `node_modules`, virtual environments, caches, build outputs, and generated dependency trees. Dependency documentation is not project guidance. Read only relevant files after the applicable role or packet authorization.

The authoritative active-plan file is `.agents/PLAN.md`. Detailed active task packets live in `.agents/plans/`.

## Core rules

1. Preserve universal core boundaries; keep host-specific behavior in adapters.
2. Keep behavior aligned with the protocol spec in `spec/`.
3. When adding protocol operations, update spec, implementation, and tests together.
4. Keep security behavior consistent with `SECURITY.md`.
5. Keep informational documents evergreen (`README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `ROADMAP.md`, `AGENTS.md`).
6. Write docs as stable descriptions of what the project is and how it works; avoid temporary status language and date-specific status notes.
7. Use precise project terminology. Prefer `sub-agent` for delegated coding-agent work; avoid overloaded role names.
8. Use `.agents/PLAN.md` only for short-term active work. Use `ROADMAP.md` for accepted medium- and long-term direction and its documented activation sequence. Use `docs/plans/**` for future execution notes that are more detailed than the roadmap but not active work. When no active work is selected, follow the next accepted activation step; do not treat exploratory work in `docs/IDEAS.md` as an alternative unless the user asks or no accepted next step exists.
9. When active plan work is completed, update or remove the relevant plan item. Update `README.md`, `ARCHITECTURE.md`, and `SECURITY.md` only for behavior or architecture that now exists.
10. Prefer concrete types over `Any`; use `Any` only when a concrete type is impractical.
11. Do not inject canned acknowledgment or receipt wording (for example, "Inter-agent message received; no reply needed.") into prompts sent to peer agents. Instructing a model toward a fixed passive receipt biases it into stopping at the receipt instead of acting on the request. Keep outward peer-message guidance about how to *decide whether to reply* and to *stay silent when idle*; never suggest a default response the model can emit in place of doing the work.
12. Match existing project style and conventions in code, tests, docs, and commits.
13. A `leader` delegates only work required by the active plan or explicitly requested by the user. Do not create or dispatch work merely because it can be bounded.
14. Every active packet records its durable dispatch state with `Status:` and `Assigned executor:` fields. `Assigned executor: none` means it has not been dispatched. Never infer unused or eligible executor state solely from connection order or a routing-name suffix.
15. The `leader` keeps commits atomic per logical step.
16. The `leader` uses [Conventional Commits](https://www.conventionalcommits.org/) style for commits: `type: description` (e.g., `fix: prevent duplicate names on concurrent connections`, `test: add concurrent duplicate name rejection test`).
17. The `leader` commits completed work before handing back unless the user explicitly requests no commits.
18. After completing a task, summarize what was done, describe what is coming next, and continue with the plan unless there is an important reason to stop, such as a required user decision or significant new information.

## Required workflow for every feature/change

Apply these requirements within the assigned role: executors perform only packet-authorized work and never commit, while leader-labeled acceptance and history steps belong only to the leader.

1. Add or update tests for the behavior change.
2. Run all configured repository checks locally before finishing, including tests, linters, formatters/style checks, type checkers, and spec validation. Use `./run-checks.sh` for the full gate. It runs `uv sync --locked` and the current required commands:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run black --check .`
   - `uv run mypy src tests`

   Exception: for documentation-only wording changes (for example, skill prompt wording that does not affect code, package metadata, schemas, or generated artifacts), do not spend time running the full gate unless the user asks for it or the edit touches a checked/generated document. This exception does **not** cover wording embedded in agent-facing inter-agent prompts (for example, reply/acknowledgment guidance emitted by an adapter): that wording directly changes model behavior, so treat it as a behavior change — add or update the relevant static prompt assertions and run the gate.
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
