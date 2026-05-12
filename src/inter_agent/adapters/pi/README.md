# Pi Adapter

Pi-facing command UX built on top of the universal core protocol.

Run Pi adapter commands through the installed package entry point:

- `uv run inter-agent-pi connect <name> [--label <label>]`
- `uv run inter-agent-pi send <to> <text>`
- `uv run inter-agent-pi broadcast <text>`
- `uv run inter-agent-pi list`
- `uv run inter-agent-pi status`

Start the server in another terminal before connecting sessions:

- `uv run inter-agent-server`

`label` is optional display metadata; routing still uses `name`. `list` is core-supported and adapter-exposed. `start.sh` is a local development/demo helper that delegates to these package entry points.
