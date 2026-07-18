# Pi repository extraction

Status: concrete; queued after migration checkpoint

## Goal

Create an independently testable and publishable `inter-agent-pi` repository containing both the Pi TypeScript package and its Python helper adapter, with an explicit dependency on `inter-agent-core` and no monorepo layout dependency.

## Target package layout

```text
inter-agent-pi/
├── README.md
├── LICENSE.md
├── CHANGELOG.md
├── package.json                 # npm/Pi package: inter-agent-pi
├── package-lock.json
├── pyproject.toml               # Python helper distribution: inter-agent-pi
├── src/
│   ├── index.ts                 # Pi extension entry
│   └── inter_agent_pi/          # Python adapter/helper package
├── tests/                       # TypeScript/static/Python/live tests
└── scripts/                     # package-local validation only
```

Exact layout may separate TypeScript and Python source directories, but the activation packet must fix one layout before execution; the executor must not choose ad hoc.

## Ownership

Move from the monorepo:

- Pi TypeScript source, package metadata, lockfile, README, license, and Pi instructions;
- Python Pi CLI/commands/listener code;
- Pi static, CLI, listener, wrapper/config, and live integration tests;
- Pi-specific TODOs and changelog entries.

Do not move:

- core protocol/server/auth/TLS/routing implementations;
- Claude assets/code/tests;
- private `.agents/**` workflow;
- public ecosystem-level docs that are not Pi-specific.

Shared source may be copied only when it becomes package-owned documentation/config, not duplicated runtime logic.

## Python boundary

- Rename extension-owned imports from `inter_agent.adapters.pi` to `inter_agent_pi`.
- Python distribution name: `inter-agent-pi`.
- Preserve console script `inter-agent-pi`.
- Depend on `inter-agent-core` through a temporary local/path source during migration and a versioned PyPI requirement before publication.
- Import reusable endpoint/auth/client/status APIs from `inter_agent`; do not copy them.
- Keep concrete result/config types and strict mypy coverage.

## Pi package boundary

- npm package name: `inter-agent-pi`.
- Put `pi.extensions` at repository root and point it at the shipped TypeScript entry.
- Include `pi-package` keyword for Pi package-gallery discovery.
- Runtime dependencies belong in `dependencies`; Pi core/TUI packages remain peer dependencies as documented by Pi.
- Correct the files allowlist to ship the actual license filename and required source/docs only.
- Remove root-shim assumptions and stale monorepo/Git URLs.
- Support `pi install npm:inter-agent-pi@<version>` and tagged Git installation from the child repository.

## Runtime resolution

Preserve precedence and fail-fast behavior:

1. `INTER_AGENT_PI_HELPER` exact override;
2. explicit configured local project/runtime path where retained for development;
3. extension-managed/documented runtime;
4. `inter-agent-pi` on PATH;
5. actionable setup-needed failure.

Do not default to Pi-specific bus state. Runtime installs share core endpoint/config/data defaults.

Before stable publication, temporary editable or local wheel dependencies may be used in tests. No floating default-branch archive may remain in release docs.

## Documentation

The child README must independently document:

- npm and tagged-Git Pi installation;
- Python helper/runtime installation and exact supported versions;
- configuration, TLS, mailbox, commands, tools, security, and troubleshooting;
- development/type/build/test commands;
- links to the public ecosystem parent and core child;
- no commit-hash instructions.

## Tests and quality gate

Move behavior tests with their code. Replace monorepo path-string assumptions. Add package-local automated tests for config loading, helper resolution, message parsing/mailbox behavior, listener lifecycle, and command/tool boundaries.

Required checks include:

```bash
npm ci
npm run typecheck
npm run build
npx prettier --check .
uv sync --locked
uv run pytest
uv run ruff check .
uv run black --check .
uv run mypy src tests
npm pack --dry-run
uv build
```

Also inspect both npm and Python artifact contents. No private docs, caches, fixtures with secrets, or unrelated host/core source may ship.

## End-to-end acceptance

From a clean temporary HOME and no monorepo checkout on PATH:

1. install the Pi package from a local packed tarball/tag candidate;
2. install the Pi Python helper and local candidate core into an isolated venv;
3. start the core server;
4. load/connect Pi, send/receive direct, broadcast, and channel messages;
5. exercise queued mailbox and immediate mode;
6. exercise explicit TLS;
7. disconnect and immediately reconnect under the same name;
8. verify helper/runtime paths differ from bus state without fragmenting the bus.

## Non-goals

- No npm/PyPI publication in this extraction item.
- No direct TypeScript WebSocket rewrite.
- No protocol/security default changes.
- No OpenCode/Codex work.
- No permanent dependency on the public superproject checkout.
