# Item 10A — Local freeze preflight

Status: ready for dispatch
Assigned executor: none

## Goal

Create a private, local preflight record for the current monorepo source state and rerun the required repository, Pi, and Claude validation gates. This slice gathers facts only. It does not select the final freeze ref, make ownership decisions, create repositories or remotes, use credentials, contact registries, rewrite history, move files, or begin extraction.

## Context

Roadmap item 10 is intentionally divided into shallow slices:

- 10A: local freeze preflight — this packet;
- 10B: maintainer decisions — leader/user gate, not an executor task;
- 10C: local extraction mapping manifest — later packet;
- 10D: private meta and recovery scaffold — later packet, only after explicit physical-migration authorization.

The locked future topology is a private `inter-agent-meta`, a public `inter-agent/inter-agent` ecosystem superproject, and public child repositories `inter-agent-core`, `inter-agent-pi`, and `inter-agent-claude-code`. Do not implement or externally validate that topology in this slice.

## Required onboarding and reads

Follow the repository onboarding order. After `AGENTS.md`, your executor role document, and this packet, read only these task references:

- `/workspace/.agents/languages/python.md`
- `/workspace/.agents/languages/nodejs.md`
- `pyproject.toml`
- `package.json`
- `.claude-plugin/marketplace.json`
- `integrations/pi/AGENTS.md` before other files under `integrations/pi/`
- `integrations/pi/package.json`
- `integrations/claude-code/.claude-plugin/plugin.json`

You may execute `run-checks.sh` and package scripts without broadening the read set. Do not read product source, tests, roadmap/future-plan files, archived plans, security documentation, or unrelated integration files for this factual preflight.

Keep command output bounded to preserve context. Redirect validation output to a mode-`0700` namespaced directory under `/tmp/`, emit only concise pass/fail summaries, inspect at most the last 40 lines of a failed log, and delete the temporary logs before reporting.

## Allowed modification

Create only:

- `.agents/migration/10a-local-freeze-preflight.md`

Do not modify any tracked or untracked file outside that path. Build outputs created by validation must be removed before reporting.

## Preflight record requirements

Write a concise Markdown record containing only non-secret local facts and command outcomes:

1. **Git baseline**
   - starting branch and exact starting `HEAD`;
   - whether the worktree was clean before the report file was created;
   - existing local tag names, or `none`;
   - configured remote names;
   - each fetch/push URL only when it contains no userinfo, embedded credential, token-like query, or token-like fragment;
   - capture raw URL values without emitting them to terminal/tool output, sanitize before writing, and if any URL might contain sensitive material record only `redacted: potentially credential-bearing URL`; do not copy or print the raw value;
   - whether a remote default branch can be resolved locally, without fetching;
   - whether `git filter-repo` is available locally.
2. **Package identity baseline**
   - root Python project/distribution name and version;
   - root npm/Pi package name and version;
   - nested Pi package name and version;
   - Claude plugin name/version and marketplace plugin name/version;
   - report disagreements exactly, but do not fix them.
3. **Validation results**
   - each required command below, pass/fail, and bounded numeric summary where available;
   - installed Pi, Claude, Python, uv, Node, npm, and Git versions when the commands are available;
   - do not paste full command logs.
4. **Unresolved maintainer gate**
   - explicitly mark all of these as unresolved unless already provable from local non-secret Git/metadata state: hosting owner/organization and exact intended URLs; private/public visibility; authorization to create and push; default branch and protection policy; registry ownership/availability; disposition of the current public remote; maintenance window; final freeze ref/tag/version.
5. **Safety and cleanup**
   - confirm no tag/ref, repository, remote, submodule, registry state, history, source path, credential/config file, or product file was changed;
   - confirm generated Pi build outputs were removed;
   - record final worktree state, which must contain only the new preflight record as an uncommitted change.

Do not include environment dumps, credential status, auth scopes, tokens, secrets, private-key material, full process listings, message bodies, or caches. Do not run `gh auth status`, credential-helper inspection, authenticated registry commands, remote fetch/push, or commands that could reveal credentials.

## Required checks

Run from the repository root with the configured asdf toolchain:

```bash
export PATH="$HOME/.asdf/shims:$HOME/.asdf/bin:$PATH"
./run-checks.sh
npm --prefix integrations/pi test
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
(
  cd integrations/pi
  npx --no-install prettier --check src/index.ts src/mailbox.ts 'tests/**/*.ts' README.md package.json tsconfig.json tsconfig.test.json
)
claude plugin validate --strict .
claude plugin validate --strict integrations/claude-code
git diff --check
```

If a validation fails, record the bounded failure and stop without fixing product or configuration files. Remove ignored `integrations/pi/dist/` and `integrations/pi/dist-tests/` after the relevant checks only after confirming they are ignored build outputs.

## Acceptance criteria

- Only `.agents/migration/10a-local-freeze-preflight.md` is changed.
- The record identifies the exact tested local baseline without claiming it is the final freeze ref.
- Every required gate passes, or a bounded blocker is recorded without scope expansion.
- Package identity and safe local Git facts are complete and internally consistent with their source metadata.
- Every mandatory user decision remains explicit rather than assumed.
- No external or destructive action occurs and no sensitive value is exposed.
- Generated outputs are removed and `git diff --check` passes.

## Leader acceptance

The leader will inspect the record against local Git and package metadata, independently rerun focused safe checks and `git diff --check`, confirm the changed-file boundary, and use the accepted facts to conduct slice 10B directly with the user. The leader will not activate slice 10C or 10D until the preceding gate is resolved.

## Completion report

Report:

- the single changed file;
- a short factual summary without remote URLs or other potentially sensitive values;
- exact pass/fail results for every required check;
- cleanup confirmation;
- blockers or unresolved local ambiguities;
- confirmation that you did not commit.
