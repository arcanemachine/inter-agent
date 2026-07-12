# Follow-ups

Concrete non-active follow-ups live as individual item files in this directory.

Use `docs/ideas/ideas.sh` first to list and filter item metadata without loading full item bodies. Then read only the item files relevant to the current planning or closure task.

## When to create a follow-up item

- The follow-up is concrete enough to describe as an action or decision.
- The follow-up is foreseeable from current evidence, not broad speculation.
- The follow-up has a clear promotion trigger.

## When not to create a follow-up item

- If the work is active or required now, put it in `.agents/PLAN.md`.
- If the work belongs in ordered project direction, promote it to `docs/ROADMAP.md`.
- If the thought is broad, speculative, or exploratory, put it in `docs/IDEAS.md`.
- If the thought lacks a promotion trigger, do not add it.

## Creating an item

Copy `docs/ideas/_template.md` to a concise kebab-case filename based on the item title, then fill in the frontmatter. Use one item per file.

Reference items by project-root-relative path. In prose, include the title after the path when helpful.

Example reference format:

```text
`docs/ideas/example-follow-up-item.md` — Example follow-up item title
```

Item format:

```yaml
---
title: Short actionable title
description: One-sentence summary
area: protocol | core | adapters | pi-extension | claude-code | packaging | developer-experience | security | other
priority: user-prioritized | next-candidate | normal | deferred
trigger: What would justify promoting this into active scope
source: Phase or origin context
---
```

Required fields: `title`, `description`. All other fields are optional. Priority defaults to `normal` when omitted. Run `docs/ideas/ideas.sh --check` after adding or editing items.

Items are open by existence and closed by removal. Delete items when they are resolved, promoted, stale, duplicated, or too vague. Do not archive removed items; git history is enough.

Promotion still requires user decision. `docs/ROADMAP.md` and `.agents/PLAN.md` remain authoritative for roadmap and active state.
