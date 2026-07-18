# Repository split first slices

Status: concrete; accepted; detailed by `docs/plans/important-closeout/`

## Purpose

Prepare and execute a clean split before initial package publication. Preserve runtime interoperability and project history without shipping transitional monorepo clutter in first releases.

## Locked topology

```text
inter-agent-meta/                         # private maintainer superproject
└── ecosystem/                            # submodule: public ecosystem

inter-agent/                              # public ecosystem superproject
├── core/                                 # submodule: inter-agent-core
└── extensions/
    ├── pi/                               # submodule: inter-agent-pi
    └── claude-code/                      # submodule: inter-agent-claude-code
```

Every submodule is an independent repository/package boundary. Git records exact submodule commits internally. Public READMEs use relative/canonical repository links and semantic versions, not copied commit hashes as install instructions.

## Locked package boundaries

### Core

- Repository and PyPI distribution: `inter-agent-core`.
- Import namespace: `inter_agent`.
- Owns protocol/spec, server, auth, TLS, routing, config/state, generic clients/CLIs, conformance/core tests, and core docs.
- Does not ship Pi/Claude adapters or host assets.

### Pi

- Repository, npm package, and Python helper distribution: `inter-agent-pi`.
- Python import package: `inter_agent_pi`.
- Preserves `inter-agent-pi` console command.
- Owns TypeScript extension, Python adapter/helper, Pi metadata/docs/tests.

### Claude Code

- Repository and Python helper distribution: `inter-agent-claude-code`.
- Python import package: `inter_agent_claude`.
- Preserves `inter-agent-claude` console command.
- Owns plugin/marketplace metadata, skill/wrappers/bootstrap, Python adapter/helper, Claude docs/tests.

## Sequence

1. Complete reliability, Pi mailbox, and installed TLS acceptance.
2. Pass the user-gated migration checkpoint and freeze a clean tested source commit.
3. Establish private `inter-agent-meta` and move private workflow ownership there.
4. Extract Pi with its TypeScript and Python helper code/tests.
5. Extract Claude Code with its plugin and Python helper code/tests.
6. Extract clean core and rename the distribution.
7. Build the public ecosystem superproject with real submodules.
8. Run candidate cross-repository acceptance.
9. Publish core, then extension helpers/native packages through separate authorization gates.
10. Replace floating bootstrap sources and run released-artifact acceptance.

Detailed requirements and gates:

- `docs/plans/important-closeout/00-execution-guide.md`
- `docs/plans/important-closeout/04-migration-checkpoint-and-meta.md`
- `docs/plans/important-closeout/05-pi-extraction.md`
- `docs/plans/important-closeout/06-claude-code-extraction.md`
- `docs/plans/important-closeout/07-core-extraction.md`
- `docs/plans/important-closeout/08-public-superproject-and-prepublication.md`

## First physical slice

The first physical slice is the migration checkpoint/private-meta scaffold, not an immediate code move. It must confirm remote ownership, visibility, package names, registry ownership, current-public-repo disposition, history mapping, backup/recovery, and authorization.

After that gate, Pi is the first product extraction because its TypeScript package boundary is already distinct. Unlike the older transition plan, Pi's Python adapter/helper moves with Pi rather than remaining in core. This avoids publishing a supposedly clean core that still owns host-specific entry points.

## History and safety

- Perform path filtering in throwaway clones using a reviewed mapping manifest.
- Preserve relevant history for files moving into each child.
- Keep a recoverable freeze ref/backup.
- Stop all editing agents during physical migration.
- Never rewrite the only working checkout.
- Do not create/push remotes or change visibility without explicit authorization.
- Never expose credentials.

## Invariants

- Default endpoint, data/state directory, token discovery, TLS defaults, protocol semantics, and CLI behavior remain stable.
- Different runtime installs continue to share one default bus.
- Child packages depend on public core APIs rather than copied core logic.
- Public artifacts contain no private `.agents/**`, maintainer workflow, credentials, caches, or unrelated host source.
- Public superproject is a thin collector/development orchestrator, not a runtime dependency or aggregate package.

## Acceptance

The split is not complete until all child gates pass, the recursive public superproject works from a clean clone, candidate artifacts interoperate across Pi and Claude over plaintext defaults and explicit TLS, and every child is independently installable from its own root.
