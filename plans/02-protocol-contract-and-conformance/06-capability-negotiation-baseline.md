# Capability Negotiation Baseline

Phase: 2 — Protocol Contract and Conformance

## Purpose

Define what `capabilities` means before adding extension capabilities, so existing clients have stable expectations.

## Repurposed backlog item

- Add capability negotiation tests and docs for future channel/rate-limit extensions.

## Scope

- Document the existing capability exchange.
- Test tolerance for unknown client capabilities.
- Keep channel and policy features outside completion scope unless promoted from `IDEAS.md`.

## Work

1. Define capability object semantics in `ARCHITECTURE.md` and spec notes.
2. State that the server returns supported capabilities and may ignore unknown client capability keys.
3. Add tests that unknown client capability keys do not break handshake.
4. Add tests for the baseline server capability response.
5. Ensure schemas allow extension keys while preserving required handshake fields.
6. Avoid implementing channel or rate-limit behavior in this plan.

## Acceptance criteria

- Capability behavior is documented without implying unimplemented features.
- Handshake tests cover known and unknown capability keys.
- Server response remains stable for core capability values.
- Future extension ideas are referenced through `IDEAS.md`, not as completion requirements.

## Files likely to change

- `ARCHITECTURE.md`
- `spec/asyncapi.yaml`
- `spec/schemas/hello.json`
- `spec/schemas/welcome.json`
- `tests/conformance/`
- `IDEAS.md`

## Checks

- `uv run pytest tests/conformance`
- `uv run pytest tests/test_spec_validation.py`
