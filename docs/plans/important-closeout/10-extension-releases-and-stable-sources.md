# Extension releases and stable runtime sources

Status: concrete; each external publication is separately user/credential gated; queued after core PyPI acceptance

## Goal

Publish independently installable Pi and Claude Code integrations from their child repositories, publish their Python helpers, and replace all floating default-branch bootstrap/install sources with stable versions.

## Release order

1. Publish `inter-agent-pi` Python helper distribution, depending on the accepted `inter-agent-core` range.
2. Publish `inter-agent-claude-code` Python helper distribution with the same core compatibility policy.
3. Publish `inter-agent-pi` npm package and tagged Git release.
4. Publish/tag the standalone Claude Code marketplace/plugin repository.
5. Update Pi and Claude managed-runtime/bootstrap documentation and scripts to install their versioned helper distributions from PyPI.
6. Update public superproject submodules and compatibility table only after released-artifact tests pass.

Each upload/tag/marketplace action receives its own explicit authorization. One authorization does not imply all later publications.

## Version policy

- Initial coordinated target is `0.1.0` if available and still appropriate.
- Child versions become independent after initial release.
- Each helper declares a tested core version range; do not use an unbounded dependency.
- npm package, Pi repo tag, Pi helper, Claude repo tag/plugin metadata, and Claude helper versions are documented explicitly; they need not remain equal forever.
- Protocol `core.version` is independent.

## Pi publication

Required metadata/content:

- npm name `inter-agent-pi`;
- `pi-package` keyword and correct `pi.extensions` root path;
- runtime dependencies in `dependencies`, Pi packages in documented peer dependencies;
- correct `files` allowlist including actual `LICENSE.md`, source, README, and required metadata only;
- repository/homepage/bugs/license/version fields;
- no dev dependencies required at runtime;
- npm pack inspection and clean `pi install npm:inter-agent-pi@<version>` acceptance;
- tagged Git install acceptance for users preferring source distribution;
- package-gallery discoverability check through Pi's documented `pi-package` mechanism.

Recheck npm name ownership immediately before publication.

## Claude publication

Required behavior:

- standalone repository validates as the documented plugin/marketplace source;
- root metadata versions/authors align;
- no declarative Monitor;
- skill and executable wrappers ship;
- tagged repository install exposes `/inter-agent`;
- managed bootstrap installs `inter-agent-claude-code==<version>` from PyPI (or an explicitly accepted stable release source), which resolves compatible core;
- local project-path/exact-helper development overrides remain;
- default endpoint/state remains shared.

If Claude provides no central registry beyond marketplace repositories, the tagged public repository and valid marketplace metadata are the publication channel. Do not invent an unsupported registry claim.

## Stable source replacement

Remove default references to:

```text
https://github.com/arcanemachine/inter-agent/archive/refs/heads/main.zip
```

Replace with versioned helper installs. Bootstrap output shown before approval must name destination, package/source, and version. Support an explicit development override without making it the default.

Search all child/public-superproject code, docs, tests, and package metadata for floating branch archives and old monorepo paths. Static tests must prevent regression.

## Credential and publication gate

For each registry/release:

- show exact package/repo/version/artifacts and passed checks;
- obtain explicit authorization;
- use maintainer credentials without exposing them;
- never publish from a dirty checkout;
- never reuse a partially published version;
- query the registry after upload and install the public artifact.

## Clean-install acceptance

With a clean HOME and no source checkout on PATH:

- `pip/uv` install both helper packages from PyPI;
- `pi install npm:inter-agent-pi@<version>` loads the extension;
- Claude installs from its tagged marketplace repo and approved bootstrap creates a working managed venv;
- both helpers resolve the released core;
- both hosts share the default bus and exchange messages;
- update/remove/reinstall paths are documented and observed.

## Checks

Run every child gate, artifact validator, `npm pack --dry-run`, strict Claude validation, public registry metadata queries, and released-artifact integration tests. Update changelogs and the ecosystem compatibility table only with observed versions.

## Non-goals

- No silent bootstrap or credential handling in model context.
- No publication of the private meta repository.
- No OpenCode/Codex packages.
