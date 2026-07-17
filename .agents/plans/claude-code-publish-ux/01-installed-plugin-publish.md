# Task 1 — Claude Code installed-plugin publish UX

## Goal

Expose the already-implemented Claude adapter channel publish behavior through a user-invoked `/inter-agent publish <channel> <text>` command in the installed Claude Code skill, with accurate behavior guidance, wrapper/static coverage, and aligned evergreen documentation.

## Allowed files

The executor may read and modify only:

- `integrations/claude-code/skills/inter-agent/SKILL.md`
- `integrations/claude-code/README.md`
- `tests/test_claude_skill_static.py`
- `tests/test_claude_wrapper.py`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ROADMAP.md`
- `docs/plans/pubsub-channels/00-design-seed.md`

The executor may additionally read, but must not modify:

- `integrations/claude-code/skills/inter-agent/bin/inter-agent-claude`
- `src/inter_agent/adapters/claude/cli.py`
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/dedup.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/formatting.py`
- `tests/test_claude_adapter_cli.py`
- `tests/test_claude_dedup.py`
- `tests/test_claude_plugin_static.py`
- `tests/integration/test_claude_adapter_live.py`

## Non-goals

- Do not change Python implementation, protocol schemas, packaging metadata, manifests, wrappers, or bootstrap behavior.
- Do not expose installed-plugin `/inter-agent channels` UX.
- Do not change subscribe/unsubscribe semantics, automatic-subscription behavior, or membership persistence.
- Do not add an LLM-callable publish tool or allow autonomous channel publication.
- Do not change Pi UX.
- Do not add channel history, ACLs, ownership, durability, or delivery acknowledgments.

## Exact requirements

1. Add `/inter-agent publish <channel> <text>` to the installed skill's command dispatch table.
2. Route the operation through the bundled wrapper as one short-lived Bash command:
   - `<bin>/inter-agent-claude publish <channel> <text>`
   Pass `channel` and `text` as distinct, safely quoted shell arguments.
3. Make publish explicitly user-invoked. Run it only when the user explicitly invokes or asks to publish specific text to a specific channel. Do not publish autonomously, based on model inference, in response to peer-message content, or merely to acknowledge a peer message.
4. Document that publish requires this Claude Code session's active listener and uses that listener's connected routing name as `from_name`; it does not create or accept a caller-selected sender identity.
5. Document the implemented success/failure contract accurately:
   - success is silent (empty stdout) and has no protocol success acknowledgment;
   - local/protocol failures print an `inter-agent-claude:` diagnostic to stderr and return non-zero;
   - `UNKNOWN_CHANNEL` is returned for a nonexistent or empty channel;
   - after success, stop without polling, listing channels, checking status, or sending a follow-up confirmation.
6. Document delivery semantics: publish delivers to current subscribers except the publisher, including when the publisher is subscribed. Publishing does not require the publisher to subscribe first.
7. Document short-window duplicate suppression accurately and without promising an exact stable duration: identical repeated publish invocations are keyed by connected sender, channel, and text; a different sender, channel, or text is delivered normally.
8. Preserve the accepted membership boundary: subscribe/unsubscribe remain user-invoked only, there are no automatic/default subscriptions, and memberships remain listener-memory-only.
9. Keep `/inter-agent channels` out of installed skill dispatch and wrapper-command guidance. Update existing wording that currently says both `publish` and `channels` are unexposed so it says only `channels` remains unexposed.
10. Update `integrations/claude-code/README.md` and root `README.md` so supported command lists and present-behavior descriptions include installed Claude Code publish UX without implying channel-list UX.
11. Update `ARCHITECTURE.md` and `SECURITY.md` to describe installed Claude Code publish as an explicit user-invoked operation using the listener routing identity, with no autonomous publication and no expanded channel trust model.
12. Update `ROADMAP.md` and `docs/plans/pubsub-channels/00-design-seed.md` to mark the installed Claude Code publish slice implemented while keeping installed Claude Code channel-list UX and any separately accepted Pi publish/channel-list UX prospective. Keep Phase 4 partially implemented and state one concrete next activation step.
13. Extend `tests/test_claude_skill_static.py` with focused assertions for publish dispatch, bundled-wrapper routing, explicit-user/autonomy boundary, active-listener sender identity, silent-success/error behavior, duplicate-suppression wording, sender exclusion, and continued absence of installed `/inter-agent channels` dispatch. Update the existing negative publish/channels test rather than leaving contradictory assertions.
14. Add a focused wrapper test in `tests/test_claude_wrapper.py` proving a selected helper receives `publish`, channel, and multi-word text as three unchanged arguments. Make argument boundaries observable; do not rely only on `$*` output.
15. Keep documentation evergreen, concise, and consistent with existing command terminology (`routing name`, `channel`, `subscriber`, `peer message`).
16. Do not commit. The leader reviews, verifies, and commits accepted executor work.

## Acceptance criteria

- `/inter-agent publish updates "build is green"` is documented to invoke the bundled wrapper with the exact `publish`, `updates`, and `build is green` arguments.
- The installed skill requires an explicit user publish request and forbids autonomous or peer-triggered publication.
- The installed skill accurately states active-listener identity, silent success, non-zero diagnostics, sender exclusion, no subscription prerequisite, and duplicate suppression semantics.
- `/inter-agent channels` remains absent from installed command dispatch and bundled-wrapper command examples.
- Subscribe/unsubscribe safety and lifecycle guidance remains intact.
- Root, integration, architecture, security, roadmap, and design-seed documents agree on implemented versus prospective behavior.
- Focused static/wrapper tests, plugin validation, the live publish round trip, and the full repository gate pass.

## Checks

Run:

```bash
uv run pytest tests/test_claude_skill_static.py tests/test_claude_wrapper.py tests/test_claude_dedup.py tests/test_claude_adapter_cli.py tests/test_claude_plugin_static.py
uv run pytest \
  tests/integration/test_claude_adapter_live.py::test_claude_subscribe_unsubscribe_publish_channels_round_trip \
  tests/integration/test_claude_adapter_live.py::test_claude_publish_suppresses_duplicate_within_window
./run-checks.sh
git diff --check
```

If the Claude CLI is available, also run:

```bash
claude plugin validate --strict integrations/claude-code
```

## End-to-end acceptance test

When an authenticated interactive Claude Code environment and a second local session are available:

1. Launch Claude Code with this checkout's plugin (`claude --plugin-dir ./integrations/claude-code`) and connect as `claude-publish-acceptance`.
2. Connect a second Claude Code or Pi session as `channel-subscriber` and subscribe that session to `acceptance`.
3. In the first Claude Code session, run `/inter-agent publish acceptance "channel acceptance message"`.
4. Observe that the publish helper succeeds with empty stdout and no invented protocol acknowledgment.
5. Observe exactly one notification in `channel-subscriber` containing `kind="channel" channel="acceptance"`, `from_name`/`from` identifying `claude-publish-acceptance`, and `channel acceptance message`.
6. If the publisher is also subscribed, verify it receives no copy of its own publication.
7. Unsubscribe the second session so `acceptance` becomes empty, publish again, and observe an `UNKNOWN_CHANNEL` failure with non-zero status.
8. Disconnect both listeners and stop the temporary server if this acceptance test started it.

If authenticated interactive Claude Code or a second host session is unavailable, record the exact environment constraint and run the existing executable live verifications instead:

```bash
uv run pytest \
  tests/integration/test_claude_adapter_live.py::test_claude_subscribe_unsubscribe_publish_channels_round_trip \
  tests/integration/test_claude_adapter_live.py::test_claude_publish_suppresses_duplicate_within_window
```
