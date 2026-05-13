# Agent Instructions

## Workflow

Commit when a task is completed.

When changing tool behavior, update README examples and config docs in the same task.

## Sanity checks (recommended)

```bash
npm run typecheck
npm run build
npm run format
```

## Commit Style

Use [Conventional Commits](https://www.conventionalcommits.org/) style: `type: description` (e.g., `feat: add outgoing message echo`, `fix: resolve TypeScript scope error`).

Match existing commits:
- `feat: add initial extension implementation`
- `docs: update README with configuration examples`
- `style: format code with Prettier`

## Dependencies and packaging

Keep test/tooling dependencies in `devDependencies` unless runtime is truly required.

Keep the published package minimal via the `files` allowlist in `package.json`.

## Documentation

Use proper formatting when writing documentation, but do not go overboard with the formatting. The content should speak for itself.
