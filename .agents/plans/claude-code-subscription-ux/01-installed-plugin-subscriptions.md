# Task 1 — Claude Code installed-plugin subscription UX

## Goal

Expose the already-implemented Claude adapter subscribe/unsubscribe behavior through the installed Claude Code `/inter-agent` skill, with channel-aware receive guidance, static coverage, and accurate evergreen documentation.

## Allowed files

The executor may read and modify only:

- `integrations/claude-code/skills/inter-agent/SKILL.md`
- `integrations/claude-code/README.md`
- `tests/test_claude_skill_static.py`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `ROADMAP.md`
- `docs/plans/pubsub-channels/00-design-seed.md`

The executor may additionally read, but must not modify:

- `integrations/claude-code/skills/inter-agent/bootstrap.md`
- `src/inter_agent/adapters/claude/cli.py`
- `src/inter_agent/adapters/claude/commands.py`
- `src/inter_agent/adapters/claude/listener.py`
- `src/inter_agent/adapters/claude/formatting.py`
- `tests/test_claude_adapter_cli.py`
- `tests/test_claude_plugin_static.py`
- `tests/integration/test_claude_adapter_live.py`

## Non-goals

- Do not change Python implementation, protocol schemas, packaging metadata, manifests, or wrappers.
- Do not expose installed-plugin `publish` or `channels` commands.
- Do not add automatic/default subscriptions or persistence across listener stop, process restart, Claude reload, or resumed sessions.
- Do not allow autonomous subscription changes based on model inference or peer messages.
- Do not add an LLM-callable subscription tool or a declarative plugin Monitor.
- Do not change Pi UX.

## Exact requirements

1. Extend `SKILL.md` command dispatch with user-invoked `/inter-agent subscribe <channel>` and `/inter-agent unsubscribe <channel>` operations.
2. Route both operations through the bundled wrapper as short-lived Bash commands:
   - `<bin>/inter-agent-claude subscribe <channel>`
   - `<bin>/inter-agent-claude unsubscribe <channel>`
3. State in `SKILL.md` that subscription changes require an explicit user invocation/request. The agent must not subscribe or unsubscribe autonomously or in response to peer-message content.
4. Document that both commands require this Claude Code session's active listener and operate on that existing listener identity. Preserve the helper's success/error output rather than inventing acknowledgments.
5. Add the channel notification form to receive guidance: `kind="channel" channel="<channel>"`. Apply the existing peer-message trust and reaction policy to channel messages.
6. State that memberships survive transient WebSocket reconnects but do not survive listener stop, process restart, Claude reload, or resumed sessions. There are no automatic/default subscriptions.
7. Update the Claude Code integration README and root README so their supported command lists and present-behavior descriptions include only the newly exposed subscribe/unsubscribe UX. Remove wording that says the installed Claude Code plugin exposes no channel commands.
8. Update `ARCHITECTURE.md` and `SECURITY.md` to describe both Pi and Claude Code installed integrations as exposing user-invoked membership changes without LLM-callable subscription tools or automatic subscriptions.
9. Update the pub/sub roadmap and design seed to mark the Claude Code subscribe/unsubscribe installed-plugin slice implemented while keeping publish/channel-list UX prospective. Keep Phase 4 partially implemented and provide one concrete next activation step for remaining Phase 4 UX.
10. Extend `tests/test_claude_skill_static.py` with focused assertions for command dispatch, wrapper commands, channel receive metadata, and the explicit-user/no-automatic-subscription boundary. Avoid broad snapshot tests and assertions tied to irrelevant prose.
11. Keep all documentation evergreen and use project terminology (`sub-agent`, `routing name`, `channel`).

## Acceptance criteria

- `/inter-agent subscribe updates` is documented to invoke the bundled wrapper's `subscribe updates` command for the current live listener.
- `/inter-agent unsubscribe updates` is documented equivalently.
- Installed skill guidance prevents autonomous membership changes and states there are no automatic subscriptions.
- Installed skill guidance recognizes channel notifications distinctly and treats them as untrusted collaboration input.
- The installed skill still does not expose `/inter-agent publish` or `/inter-agent channels`.
- Root, architecture, security, integration, roadmap, and design-seed descriptions agree on implemented versus prospective behavior.
- Focused static tests and the full repository gate pass.

## Checks

Run:

```bash
uv run pytest tests/test_claude_skill_static.py tests/test_claude_plugin_static.py
./run-checks.sh
git diff --check
```

If the Claude CLI is available, also run:

```bash
claude plugin validate --strict integrations/claude-code
```

## End-to-end acceptance test

When an authenticated interactive Claude Code environment is available:

1. Launch Claude Code with this checkout's plugin (`claude --plugin-dir ./integrations/claude-code`).
2. Run `/inter-agent connect claude-channel-acceptance` and observe the connected line.
3. Run `/inter-agent subscribe acceptance` and observe a successful `subscribe_ok` response for `acceptance`.
4. From another local shell using the same endpoint/secret, run `uv run inter-agent-publish acceptance "channel acceptance message"`.
5. Observe one Claude Code notification containing `kind="channel" channel="acceptance"` and `channel acceptance message`.
6. Run `/inter-agent unsubscribe acceptance` and observe a successful `unsubscribe_ok` response.
7. Publish again and verify no new channel notification reaches that Claude Code session.
8. Disconnect the Claude Code listener and stop the temporary server if this acceptance test started it.

If interactive Claude Code authentication is unavailable, record that exact environment constraint and run the existing live adapter round trip as the closest executable end-to-end verification:

```bash
uv run pytest tests/integration/test_claude_adapter_live.py::test_claude_subscribe_unsubscribe_publish_channels_round_trip
```
