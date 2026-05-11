# Pi Command Status and Errors

Phase: 3 — Adapter Integration and Command UX

## Purpose

Make Pi adapter output predictable for both humans and host tooling.

## Scope

- Define command success and failure output shapes.
- Improve status reporting.
- Surface protocol errors without leaking internal tracebacks during normal operation.

## Work

1. Define output conventions for Pi commands: human-readable text, JSON output, or a documented mix.
2. Expand `status` beyond static capability flags so it reflects server reachability and identity verification.
3. Map core protocol errors to clear adapter messages and non-zero exit codes.
4. Add parser options for JSON output if host tooling needs structured data.
5. Test output for success and failure paths.
6. Update adapter docs with examples.

## Acceptance criteria

- `status` distinguishes available, unavailable, and identity-check-failed states.
- Protocol errors are visible to the user and reflected in exit codes.
- Output format is documented and tested.
- Host tooling can parse stable output for status/list if needed.

## Files likely to change

- `src/inter_agent/adapters/pi/cli.py`
- `src/inter_agent/adapters/pi/commands.py`
- `src/inter_agent/core/`
- `tests/`
- `adapters/pi/README.md` or namespaced equivalent
- `ERROR_CODES.md`

## Checks

- `uv run pytest tests/test_pi_adapter_cli.py`
- `uv run pytest tests/integration`
- `uv run mypy src tests`
