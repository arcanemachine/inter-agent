# Task B — channel diagnostics core API and CLI

## Goal

Add the Phase 2 typed channel-diagnostics API and its user-facing core CLI surface.

## Allowed files

Read and modify only:

- `src/inter_agent/core/channels.py` (new)
- `pyproject.toml`
- `inter-agent`
- `README.md`
- `tests/test_core_command_api.py`
- `tests/test_console_entry_points.py`
- `tests/test_inter_agent_wrapper.py`

Read only as needed:

- `src/inter_agent/core/list.py`
- `src/inter_agent/core/kick.py`
- `src/inter_agent/core/shared.py`
- `src/inter_agent/core/transport.py`
- `tests/conformance/helpers.py`

## Requirements

1. Add immutable `ChannelInfo(name: str, subscribers: tuple[str, ...])` and `ChannelsResult(raw_response: str, response: dict[str, object], channels: tuple[ChannelInfo, ...])` types.
2. Provide `list_channels(host, port, *, tls=False, data_dir=None, tls_cert_path=None)`.
3. Connect as a control session, authenticate with existing helpers, send `{"op":"channels"}`, parse the raw object response, and return structured channel entries.
4. Add `inter-agent-channels` with endpoint/TLS flags matching `inter-agent-list`; print the raw protocol response to stdout and return 0 for `channels_ok`, 1 for an error response.
5. Add `./inter-agent channels` forwarding to `uv run inter-agent-channels`.
6. Update user documentation to describe this implemented core CLI command without claiming adapter channel support.
7. Test typed API structure and error response handling, CLI help/entry-point declaration, and wrapper delegation.

## Non-goals

- Do not change server routing, protocol schemas, or adapters.
- Do not implement publish.
- Do not implement subscribe/unsubscribe agent-session support.

## Acceptance

- A control diagnostic returns sorted channel/subscriber data as `ChannelsResult`.
- Agent-role or other protocol errors are returned as a structured result/CLI failure, not silently parsed as channels.
- Endpoint and TLS options propagate as in other core commands.
- Focused tests and `./run-checks.sh` pass.

## Parallel-work rule

Task A is running concurrently. Do not modify files outside this packet. Report completion and changed files to the leader; do not make unrelated changes.
