# Core PyPI release

Status: concrete; publication is explicitly user/credential gated; queued after pre-publication acceptance

## Goal

Audit, publish, and clean-install the first uncluttered `inter-agent-core` release from the independent core repository.

## Release-source audit

Before publication verify:

- PyPI distribution name availability/ownership for `inter-agent-core` at execution time;
- version and changelog entry;
- supported Python versions and classifiers;
- project/repository/documentation/security URLs;
- license metadata and included license;
- dependency declarations and lockfile;
- all generic entry points;
- wheel/sdist contents and absence of host/private files;
- artifact validator covers the current entry-point/spec set;
- core tests and candidate cross-repository acceptance pass;
- no existing incompatible release/version collision.

Do not infer registry availability from the planning-time 404.

## Candidate validation

Build once from a clean checkout and validate the exact artifacts intended for upload:

```bash
uv sync --locked
./run-checks.sh
uv build
uv run python scripts/validate-release-build.py
```

Use an accepted metadata checker such as `twine check` in an isolated tool environment if it is not a project dependency. Record artifact filenames and SHA-256 digests in the private release record, not as permanent README install pins.

Install both wheel and sdist into separate clean venvs and run server/status/list/direct/channel/TLS smoke tests.

## Publication gate

Uploading is external and credential-sensitive. Immediately before upload:

1. present package name, version, target registry, artifact list, and validation results;
2. obtain explicit user authorization for that exact release;
3. do not request or expose a token in chat/tool output;
4. use maintainer-owned authenticated tooling or give the maintainer an exact upload command when credentials are unavailable to the agent;
5. never commit `.pypirc`, tokens, shell history, or credential-bearing logs.

TestPyPI is optional and also requires explicit authorization/credentials. It does not replace final PyPI clean-install acceptance.

## Post-publication verification

- Query PyPI metadata and confirm name/version/artifact hashes.
- Install with `pip`/`uv` using only the public index in a new environment.
- Verify `import inter_agent` and every generic console script.
- Start a TLS server, connect clients, exchange direct/channel traffic, and shut down.
- Confirm host helper candidate packages can depend on the public core version.
- Tag the exact released source and push the tag after authorization according to repository policy.
- Update core changelog/release notes and ecosystem compatibility documentation.

## Failure handling

If upload partially succeeds, never overwrite/reuse the published version. Assess PyPI state, fix metadata/code, increment version, rebuild from a clean checkout, and repeat the full gate. If package ownership is unavailable, stop for a naming decision rather than using a near-match silently.

## Acceptance criteria

- Public PyPI install succeeds without source checkout or host assets.
- Artifact metadata/content matches reviewed candidates.
- Generic CLI, auth, TLS, routing, and channels smoke tests pass.
- Public docs use `inter-agent-core==<released-version>` where a pinned example is appropriate and otherwise document supported version ranges.
- No credentials entered repository/context.

## Non-goals

- No Pi npm or Claude marketplace publication in this item.
- No extension helper publication before core install acceptance.
- No aggregate `inter-agent` distribution.
