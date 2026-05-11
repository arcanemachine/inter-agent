# Server Identity Hardening

Phase: 5 — Security and Operational Hardening

## Purpose

Strengthen client-side server identity verification within the single-user localhost threat model.

## Scope

- Reduce stale metadata and PID-reuse risk.
- Keep the system lightweight and local.
- Avoid remote trust, PKI, or multi-user assumptions.

## Work

1. Extend server identity metadata with an instance nonce and process start marker where portable.
2. Write identity metadata atomically with restrictive permissions.
3. Verify host, port, PID liveness, and the additional identity marker before clients send tokens.
4. Handle platforms where process start markers are unavailable by using documented fallback behavior.
5. Add tests for matching metadata, missing metadata, stale metadata, and mismatched host/port.
6. Update `SECURITY.md` with the exact identity checks and limitations.

## Acceptance criteria

- Clients reject stale or mismatched identity metadata before sending the token.
- Identity metadata remains local and permission-restricted.
- The documented threat model remains single-user localhost.
- Tests cover successful and failed verification paths.

## Files likely to change

- `src/inter_agent/core/shared.py`
- `src/inter_agent/core/client.py`
- `src/inter_agent/core/send.py`
- `src/inter_agent/core/list.py`
- `tests/`
- `SECURITY.md`

## Checks

- `uv run pytest`
- `uv run mypy src tests`
