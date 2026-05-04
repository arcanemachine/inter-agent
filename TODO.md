This is a list of incomplete items. As items are completed, remove them from this list. Do not mark them as completed.

Chronological (confirmed)

- Add package entry points so users can run core and adapter commands without file paths.
- Add integration test coverage for adapter commands against a live server.
- Add CI workflow to run formatting, linting, typing, tests, and spec validation.
- Tighten protocol error semantics and document the canonical error-code set.

Optional / not yet confirmed

High priority

- Add target resolution beyond exact name (e.g., unique prefix rules) and corresponding conformance tests.
- Add graceful server lifecycle helpers (PID file handling and safe shutdown command).

Medium priority

- Add capability negotiation tests and docs for future channel/rate-limit extensions.
- Add message size-boundary tests for direct and broadcast paths.

Low priority

- Add optional channel/pub-sub extension behind explicit capability flags.
- Add optional policy middleware examples (rate-limit or allowlist).
