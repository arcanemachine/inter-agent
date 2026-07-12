# Task A — publish core API and CLI

## Goal

Add the Phase 2 typed publish command API and its user-facing core CLI surface.

## Allowed files

Read and modify only:

- `src/inter_agent/core/publish.py` (new)
- `src/inter_agent/core/send.py`
- `pyproject.toml`
- `inter-agent`
- `README.md`
- `tests/test_core_command_api.py`
- `tests/test_console_entry_points.py`
- `tests/test_inter_agent_wrapper.py`

Read only as needed:

- `src/inter_agent/core/client.py`
- `src/inter_agent/core/kick.py`
- `src/inter_agent/core/shared.py`
- `src/inter_agent/core/transport.py`
- `tests/conformance/helpers.py`

## Requirements

1. Provide `publish_to_channel(host, port, channel, text, from_name=None, *, tls=False, data_dir=None, tls_cert_path=None)`.
2. Connect as a control session, authenticate using the existing helpers, and send `{"op":"publish","channel":...,"text":...}` with optional `from_name`.
3. Return the existing `SendResult` type, including a protocol error received within the existing short response timeout. A successful publish has no acknowledgment.
4. Add `inter-agent-publish` with positional `<channel> <text>`, optional `--from`, endpoint/TLS flags matching `inter-agent-send`, stdout reserved for normal command output, and exit status 0/1 matching `inter-agent-send`.
5. Add `./inter-agent publish <channel> <text>` forwarding to `uv run inter-agent-publish`.
6. Update user documentation to describe this implemented core CLI command without claiming adapter channel support.
7. Test typed API success and a protocol error, CLI help/entry-point declaration, and wrapper delegation.

## Non-goals

- Do not change server routing, protocol schemas, or adapters.
- Do not implement subscribe/unsubscribe agent-session support.
- Do not implement channel diagnostics.

## Acceptance

- A control publish reaches subscribed agents and reports `UNKNOWN_CHANNEL` as a structured `SendResult.error`.
- Endpoint and TLS options propagate as in other core commands.
- Focused tests and `./run-checks.sh` pass.

## Parallel-work rule

Task B is running concurrently. Do not modify files outside this packet. Report completion and changed files to the leader; do not make unrelated changes.
