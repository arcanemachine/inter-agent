# Task 2 — Pi user-controlled subscription commands

## Dependency

Task 1 (Python adapter channel commands) must be reviewed and committed first. This packet is otherwise self-contained and assumes its documented CLI contract exists in the repository.

## Goal

Expose channel membership through user-invoked Pi subcommands that match the existing grouped `/inter-agent <subcommand>` syntax, while deliberately withholding subscribe/unsubscribe from LLM-callable tools.

## Allowed files

The executor may read and modify only these files unless the leader approves an expanded packet:

- `integrations/pi/AGENTS.md` (read only)
- `integrations/pi/README.md`
- `integrations/pi/src/index.ts`
- `src/inter_agent/adapters/pi/README.md` (read only)
- `tests/test_pi_extension_static.py`
- `tests/integration/test_pi_adapter_live.py` (read only)

## Non-goals

- Do not register `inter_agent_subscribe` or `inter_agent_unsubscribe` tools.
- Do not add installed Pi publish or channel-list UX in this task.
- Do not add automatic/default subscriptions.
- Do not persist subscriptions across explicit disconnects, Pi listener restarts, or Pi session reloads.
- Do not change protocol, core, or Python adapter behavior established by Task 1.
- Do not add Claude Code installed-plugin channel UX.

## Exact requirements

1. Add grouped, user-facing commands matching the existing Pi style:
   - `/inter-agent subscribe <channel>`
   - `/inter-agent unsubscribe <channel>`
2. Add both subcommands to autocomplete and grouped usage text.
3. Gate both commands on the current Pi listener being ready and connected, using the same user-facing connection guidance as existing send/broadcast commands.
4. Invoke the Python adapter CLI contract from Task 1 and pass the current listener routing name internally. The user must not provide or manage the listener name.
5. Validate that exactly one channel argument is present. On invalid input, show the corresponding grouped command usage.
6. On success, show concise notifications identifying the affected channel. On protocol or local-control failure, use existing script failure formatting and error notification conventions.
7. Do not register model-callable subscription tools or add subscription authority to the injected model instructions.
8. Distinguish inbound channel messages from direct and broadcast messages in notifications and model-visible context. Include the channel name without treating the delivery as direct or broadcast, while preserving existing untrusted-peer guidance, truncation, and display/context separation.
9. Keep direct and broadcast notification/context behavior unchanged.
10. Update the Pi integration README command table, examples, feature description, subscription lifecycle, user-only control boundary, and UAT. State explicitly that there are no automatic subscriptions and that subscriptions must be re-established after listener restart/reload.
11. Extend static coverage for command registration, autocomplete, connection gating, helper invocation with current routing name, absence of subscription tools, distinct channel delivery, and documentation.

## Acceptance criteria

- Pi users can subscribe and unsubscribe through `/inter-agent` without knowing internal listener-control details.
- The LLM has no subscribe/unsubscribe tool surface.
- Channel notifications and context identify the channel distinctly.
- Existing direct/broadcast commands and tools remain unchanged.
- Pi extension checks and the full repository gate pass.

## Checks

```bash
uv run pytest tests/test_pi_extension_static.py
npm --prefix integrations/pi run typecheck
npm --prefix integrations/pi run build
npm --prefix integrations/pi run format
./run-checks.sh
```

After formatting, verify only intended files changed.

## User acceptance test

1. Load the Pi extension and run `/inter-agent connect pi-channel-test`.
2. Run `/inter-agent subscribe updates` and confirm the success notification names `updates`.
3. Publish to `updates` from another connected adapter and confirm Pi displays a channel-specific notification and context entry.
4. Run `/inter-agent unsubscribe updates` and confirm success.
5. Publish again and confirm Pi receives no channel message.
6. Confirm the tool list does not contain subscribe or unsubscribe tools.
