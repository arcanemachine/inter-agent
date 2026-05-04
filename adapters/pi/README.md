# Pi Adapter (MVP)

Pi-facing command UX built on top of the universal core protocol.

Commands (recommended via `./start.sh`):

- `./start.sh connect <name>`
- `./start.sh send <to> <text>`
- `./start.sh broadcast <text>`
- `./start.sh list`
- `./start.sh status`

Equivalent direct CLI (via `python -m adapters.pi.cli`):

- `connect <name>`
- `send <to> <text>`
- `broadcast <text>`
- `list`
- `status`

`list` is core-supported and adapter-exposed in this MVP.
