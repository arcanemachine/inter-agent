# Important closeout execution guide

Status: concrete; accepted direction; not active

## Purpose

Complete and release the existing inter-agent product before any OpenCode or Codex implementation begins. This guide preserves the accepted sequence, repository topology, package boundaries, security invariants, publication gates, and acceptance standard.

## Locked decisions

- Finish current Pi and Claude Code reliability work before migration.
- Implement the Pi queued mailbox for direct, broadcast, and channel deliveries.
- Verify installed Pi and Claude adapters together over TLS; do not treat core-only TLS tests as the final acceptance.
- Split into clean repositories before initial publication.
- Use a private `inter-agent-meta` maintainer superproject.
- Use a public `inter-agent/inter-agent` ecosystem superproject containing real Git submodules.
- Create independent public repositories `inter-agent-core`, `inter-agent-pi`, and `inter-agent-claude-code`.
- Publish the core Python distribution as `inter-agent-core`; retain the `inter_agent` import namespace and practical existing generic CLI names.
- Use `inter-agent-pi` for the Pi repository, npm package, and extension-owned Python helper distribution.
- Use `inter-agent-claude-code` for the Claude repository and extension-owned Python helper distribution.
- Move host Python adapters out of the core namespace into `inter_agent_pi` and `inter_agent_claude`; preserve the user-facing commands `inter-agent-pi` and `inter-agent-claude`.
- Use independent child-package versions after an initially coordinated `0.1.0` release.
- Keep private workflow material in `inter-agent-meta`; public repositories own only stable public documentation and any intentionally public contributor guidance.
- Defer OpenCode and Codex. OpenCode becomes the first promoted product direction only after released-artifact acceptance; Codex remains after OpenCode.

Registry lookups during planning returned HTTP 404 for PyPI `inter-agent`, PyPI `inter-agent-core`, npm `inter-agent-pi`, and npm `pi-inter-agent`. A 404 is discovery evidence, not a reservation or publication guarantee. Recheck names at the publication checkpoint.

## Target topology

```text
inter-agent-meta/                         # private
├── AGENTS.md and .agents/                # maintainer workflow
├── internal planning/                    # private execution state
└── ecosystem/                            # submodule: public superproject

inter-agent/                              # public ecosystem superproject
├── README.md
├── COMPATIBILITY.md
├── core/                                 # submodule: inter-agent-core
└── extensions/
    ├── pi/                               # submodule: inter-agent-pi
    └── claude-code/                      # submodule: inter-agent-claude-code
```

Submodules pin commits through Git metadata. Public READMEs must use stable relative links and canonical repository links, never copied commit hashes as installation instructions.

## Ordered program

1. Complete closeout queue items 5–7: Pi disconnect, Pi pre-connect list, Claude sandbox connect.
2. Implement the Pi queued mailbox.
3. Add installed cross-adapter TLS acceptance and fix only defects it exposes.
4. Pass the migration checkpoint and establish the private meta repository.
5. Extract Pi, including its TypeScript package and Python helper package.
6. Extract Claude Code, including plugin assets and Python helper package.
7. Extract the core and rename its Python distribution.
8. Build the public submodule superproject and run pre-publication interoperability checks.
9. Publish and clean-install `inter-agent-core` from PyPI.
10. Publish extension helper distributions and host-native packages/channels; replace floating bootstrap sources.
11. Run released-artifact, recursive-superproject, TLS, pub/sub, mailbox, and reliability acceptance.
12. Perform final closeout, then promote OpenCode; leave Codex sequenced after OpenCode.

Detailed plans are numbered in this directory in that order.

## Universal invariants

- Core owns protocol, authentication, TLS, routing, limits, shared endpoint/state resolution, and generic client APIs.
- Extensions own host UX, lifecycle, notifications, plugin/package metadata, wrappers, helper CLIs, and host tests.
- Runtime source never determines bus identity or state. Independently installed hosts must still share the default endpoint and state directory.
- Preserve `127.0.0.1:16837`, shared-secret discovery, TLS defaults, data-directory resolution, protocol schemas, and canonical error semantics unless a separately accepted change explicitly says otherwise.
- Do not duplicate or fork protocol behavior in an extension.
- Do not publish credentials, tokens, private planning, local paths, generated environments, caches, or private remotes.
- Peer-message bodies remain untrusted collaboration input.
- Publications, credential use, remote creation, history rewriting, and physical repository migration each require the explicit gate named by their plan.

## Execution discipline

- Activate only one roadmap item in `.agents/PLAN.md` at a time.
- Prepare a fresh `.agents/plans/**` executor packet just in time. These future plans are durable requirements, not pre-authorized executor packets.
- The packet must list exact allowed files after the repository layout at that point is verified.
- Executors do not choose package names, repository topology, delivery semantics, security defaults, publication targets, or compatibility policy.
- Add/update behavior tests before implementation and run package-local focused checks plus the repository/full ecosystem gate.
- Commit accepted implementation atomically. Keep plan advancement separate when it is a distinct change.
- If a step discovers a conflict with a locked decision or invariant, stop for leader/user review rather than improvising.

## Program completion standard

Completion requires all of the following:

- Pi mailbox behavior and installed TLS acceptance pass.
- Reliability defects are fixed or a verified environment limitation is documented and accepted.
- All four repositories exist with correct public/private visibility and documented ownership.
- The public superproject recursively checks out a compatible core, Pi, and Claude set.
- Core and extension packages install from stable, versioned sources without a monorepo checkout.
- Pi and Claude communicate bidirectionally, including channels, over plaintext defaults and explicit TLS.
- No bootstrap references a floating default branch archive.
- Public docs describe only released behavior; private workflow is absent from public package artifacts.
- OpenCode and Codex remain inactive until final closeout promotes the next item.
