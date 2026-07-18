# Claude Code repository extraction

Status: concrete; queued after Pi extraction

## Goal

Create an independently testable and publishable `inter-agent-claude-code` repository containing Claude Code plugin/marketplace assets and its Python helper adapter, with an explicit dependency on `inter-agent-core` and no monorepo layout dependency.

## Target package layout

```text
inter-agent-claude-code/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json         # if repository acts as its own marketplace
├── skills/inter-agent/
│   ├── SKILL.md
│   ├── bootstrap.md
│   └── bin/
├── src/inter_agent_claude/      # Python helper package
├── tests/
├── pyproject.toml               # inter-agent-claude-code
├── README.md
├── CHANGELOG.md
└── LICENSE.md
```

Validate the exact standalone marketplace source layout with the current Claude CLI before fixing metadata. The executor must follow the accepted validated layout, not guess whether `source` should be `./` or a subdirectory.

## Ownership

Move:

- Claude plugin manifest, marketplace metadata, skill, bootstrap/wrapper scripts, README, and license;
- Python Claude CLI/commands/listener/dedup/formatting/state code;
- Claude static, CLI, listener, wrapper, skill, marketplace, and live tests;
- Claude-specific changelog/TODO material.

Do not move core implementations, Pi assets, private workflow, or unrelated ecosystem documentation.

## Python boundary

- Rename imports from `inter_agent.adapters.claude` to `inter_agent_claude`.
- Distribution name: `inter-agent-claude-code`.
- Preserve `inter-agent-claude` console script.
- Depend on `inter-agent-core`; reuse its typed client/config/auth/status APIs.
- Do not create a second `inter_agent` package across distributions or rely on fragile namespace-package merging.

## Plugin boundary

- Plugin metadata and skill assets must live at paths valid from this repository root.
- The repository must pass strict Claude plugin and marketplace validation.
- Keep skill-driven Monitor startup; never add a declarative plugin Monitor.
- Preserve explicit-user-only subscribe/unsubscribe/publish/channels behavior.
- Keep wrappers executable in Git and artifacts.
- Preserve helper resolution precedence and configured secret propagation.
- Keep managed bootstrap explicitly approval-gated with `--yes`.

## Bootstrap transition

During extraction, tests may use local candidate wheels/paths. Before release:

- bootstrap installs a versioned `inter-agent-claude-code` helper distribution that depends on `inter-agent-core`;
- floating GitHub `main.zip` is removed as the default;
- local project-path and exact-helper overrides remain for development;
- bus endpoint/state defaults remain core-owned and shared.

## Documentation

The child README must independently cover:

- plugin marketplace installation from the standalone repository;
- local development load;
- Python helper and managed runtime setup;
- explicit approval and install source shown before bootstrap;
- commands, receive behavior, TLS, security, troubleshooting, and updates;
- links to the public ecosystem parent and core child;
- stable tags/versions, not commit hashes, in user instructions.

## Tests and checks

Move tests with code and eliminate monorepo path assumptions. Required coverage includes manifest alignment, no declarative Monitor, skill command behavior, wrapper resolution, bootstrap approval/source/version, executable bits, helper CLI/listener behavior, duplicate suppression, channels, and TLS propagation.

Required candidate checks:

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run black --check .
uv run mypy src tests
uv build
claude plugin validate --strict .
```

If the standalone repository contains both marketplace and plugin roots, validate each exact supported target. Inspect wheel/sdist contents and confirm all skill/bin assets ship with executable permissions where applicable.

## End-to-end acceptance

From a clean temporary HOME with no monorepo checkout or global helper:

1. install the plugin from the standalone local/tag candidate marketplace;
2. install/bootstrap candidate `inter-agent-claude-code` and candidate core into an isolated managed venv after explicit approval;
3. connect through the skill-driven Monitor;
4. exchange direct, broadcast, and channel messages with Pi;
5. exercise channel commands, diagnostics, disconnect/reconnect, and TLS;
6. verify plugin removal/update behavior and actionable missing-runtime diagnostics.

## Non-goals

- No registry publication in this item.
- No declarative Monitor.
- No protocol/security changes.
- No vendored core source.
- No dependency on a public-superproject checkout.
