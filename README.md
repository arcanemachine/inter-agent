# inter-agent

`inter-agent` is a lightweight localhost messaging bus for AI coding sessions.

It provides a framework-agnostic protocol for direct and broadcast messaging between running sessions, plus host adapters that expose that protocol in specific tooling.

## Core behavior

- WebSocket protocol over localhost.
- First-class direct (`A -> B`) and broadcast messaging.
- Extension envelope via `op: "custom"` with pass-through routing.
- Basic shared-token authentication and local identity checks.

## Layout

- `core/` universal protocol server/client bits
- `adapters/pi/` Pi-specific UX adapter
- `spec/` AsyncAPI + schemas + examples
- `tests/` conformance and validation tests
- `docs/` supporting notes

## Quickstart

1. Create environment and install dependencies:
   - `uv venv`
   - `.venv/bin/pip install -e .`
   - `.venv/bin/pip install pytest==9.0.3 pytest-asyncio==1.3.0 ruff==0.15.12 black==26.3.1 mypy==1.20.2 jsonschema==4.26.0 pyyaml==6.0.3`

2. Start server:
   - `./start.sh server`

3. Connect two sessions (in separate terminals):
   - `./start.sh connect agent-a`
   - `./start.sh connect agent-b`

4. Send and broadcast:
   - `./start.sh send agent-b "run tests"`
   - `./start.sh broadcast "build is green"`

5. List sessions / status:
   - `./start.sh list`
   - `./start.sh status`

## Development checks

- `.venv/bin/pytest`
- `.venv/bin/ruff check .`
- `.venv/bin/black --check .`
- `.venv/bin/mypy core adapters tests`

## Additional docs

- `ARCHITECTURE.md`
- `SECURITY.md`
- `AGENTS.md`
