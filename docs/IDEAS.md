# Ideas

Purpose: this file preserves future protocol, adapter, packaging, developer-experience, security, and host-integration ideas that should remain visible without becoming active scope.

Status: deferred and exploratory unless a current plan promotes an item.

## How to use this file

1. Read the relevant section when planning work that touches that topic.
2. Do not treat every idea here as required implementation.
3. Promote ideas into `ROADMAP.md` only when the user accepts them as medium- or long-term direction.
4. Copy only the next concrete slice into `.agents/PLAN.md` when work becomes active.
5. Put concrete, actionable follow-ups in `docs/ideas/` as individual items (see `docs/ideas/ideas.sh`) when they are too specific for this idea bank but not active or ordered enough for `ROADMAP.md`.
6. Keep broad, speculative, or exploratory ideas here; keep concrete, trigger-bearing follow-ups as `docs/ideas/*.md` items.
7. When an idea becomes implemented architecture, move the current truth to `docs/ARCHITECTURE.md`.

## Concrete follow-up items

Individual, actionable items live in `docs/ideas/*.md` with YAML frontmatter. List them with `docs/ideas/ideas.sh`; user-prioritized items are queryable via `docs/ideas/ideas.sh --priority user-prioritized`.

## Host adapters

### Claude Code adapter

Claude Code support is a completed host integration. User-facing plugin docs live in `integrations/claude-code/README.md`. Claude Code follow-ups outside that completed scope live in `docs/ideas/`.

### Additional host adapters

Other coding-agent hosts can be added once the adapter boundary is stable. New host directions belong here until the user accepts them as roadmap direction or active work; the concrete follow-up is `docs/ideas/additional-host-adapters.md`.

### Pi extension

The Pi extension (`integrations/pi/`) currently shells out to Python helper entry points. Pi extension follow-ups live in `docs/ideas/`.

## Protocol extensions

Future protocol follow-ups live in `docs/ideas/`. Enumerate them with `docs/ideas/ideas.sh --area protocol`.

## Developer experience

Future tooling follow-ups live in `docs/ideas/`. Enumerate them with `docs/ideas/ideas.sh --area developer-experience`.

## User ideas

User-sourced ideas and suggestions are preserved in `docs/IDEAS.USER.md`. Agents must not modify that file.