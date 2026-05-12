# Connection and Payload Limits

Phase: 5 — Security and Operational Hardening

## Purpose

Constrain local resource usage from accidental client loops or oversized extension payloads.

## Scope

- Add configurable connection limits.
- Tighten custom message validation enough to protect receivers and the bus.
- Keep defaults suitable for local coding-agent sessions.
- Custom payloads are currently bounded by `INTER_AGENT_FRAME_MAX` only; define any separate custom payload limit here.

## Work

1. Add a configurable maximum active connection count.
2. Reject connections beyond the limit with a canonical error or close reason.
3. Validate `custom_type` as a bounded string.
4. Define payload size or encoded-frame constraints for custom messages.
5. Consider simple JSON depth/type checks if payload nesting can harm receivers.
6. Add tests for connection limit, custom type validation, and custom payload limits.
7. Document environment variables and defaults.

## Acceptance criteria

- Active connections are bounded by a documented default and environment override.
- Custom messages cannot bypass all application-level size checks.
- Limit failures use canonical error behavior.
- Tests cover limit success and failure paths.

## Files likely to change

- `src/inter_agent/core/shared.py`
- `src/inter_agent/core/server.py`
- `spec/schemas/custom.json`
- `tests/conformance/`
- `SECURITY.md`
- `ERROR_CODES.md`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest tests/test_spec_validation.py`
- `uv run mypy src tests`
