# Core repository extraction and package rename

Status: concrete; queued after Pi and Claude extraction

## Goal

Create a clean `inter-agent-core` public repository and Python distribution containing only universal protocol/runtime behavior, with no host plugin assets or host adapter packages.

## Target ownership

Core owns:

- `src/inter_agent/core/**` and the `inter_agent` package initialization needed for core;
- protocol AsyncAPI, schemas, examples, canonical errors, and conformance tests;
- generic server/client/send/broadcast/publish/list/channels/status/shutdown/kick APIs and CLIs;
- authentication, TLS, transport, config/state resolution, routing, limits, lifecycle;
- core README, architecture, security model, changelog, license, build/check scripts;
- core unit/integration tests and artifact validation.

Core excludes:

- `inter_agent_pi`, `inter_agent_claude`, TypeScript extension, Claude plugin/skill/wrappers;
- root Pi npm shim and Claude marketplace metadata;
- host-specific setup/docs/tests;
- private workflow/plans.

## Distribution contract

- Repository and distribution: `inter-agent-core`.
- Import namespace: `inter_agent`.
- Version starts at the accepted initial release version, expected `0.1.0` unless release audit changes it.
- Preserve generic console scripts:
  - `inter-agent-server`
  - `inter-agent-connect`
  - `inter-agent-send`
  - `inter-agent-list`
  - `inter-agent-status`
  - `inter-agent-shutdown`
  - `inter-agent-kick`
  - `inter-agent-publish`
  - `inter-agent-channels`
- Remove host scripts `inter-agent-pi` and `inter-agent-claude` from core metadata.
- `core.version` protocol capability remains protocol compatibility, not distribution version.

## API compatibility

Host children must consume public typed core APIs. Before removing adapters, verify every imported core surface is intentional. Promote a helper to a documented public core surface only when it is genuinely host-neutral; otherwise refactor the child.

Do not preserve old internal adapter import paths inside core merely as compatibility clutter before the first split release.

## Packaging

- Update `pyproject.toml`, lockfile, manifests, artifact validator, and docs for the clean boundary.
- Package all spec data required at runtime/development and no host assets.
- Validate every generic entry point; the current artifact validator's expected script set is incomplete and must be corrected.
- Use exact supported dependency ranges/pins according to accepted release policy.
- Build reproducible wheel and sdist candidates.
- Ensure package metadata includes classifiers, license, repository/project URLs, changelog/version policy, and Python support.

## Tests and checks

Move core/conformance tests and delete host-only assumptions. Required gate:

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run black --check .
uv run mypy src tests
uv build
uv run python scripts/validate-release-build.py
```

Artifact validation must assert:

- every generic console script;
- core modules and packaged spec assets;
- absence of Pi/Claude source/assets/private docs;
- wheel and sdist metadata name/version;
- clean import in a fresh environment.

## End-to-end acceptance

Using only candidate core artifacts in a clean venv:

1. install wheel and separately sdist;
2. start server and run status/list;
3. connect two generic clients and exchange direct/broadcast/channel traffic;
4. exercise auth failure and TLS generated-certificate flow;
5. stop server cleanly;
6. install candidate Pi and Claude helper distributions against this core candidate and rerun their focused live tests.

## Non-goals

- No publication in this item.
- No host adapter compatibility shims in core.
- No protocol version bump without a demonstrated protocol change and user decision.
- No remote/multi-user threat-model expansion.
- No OpenCode/Codex code.
