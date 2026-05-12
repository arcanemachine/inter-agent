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

`label` is optional display metadata; routing still uses `name`. `list` is core-supported and adapter-exposed.

Pi commands perform the core localhost server identity check before sending the shared token; unavailable identity returns a non-zero exit code. Protocol error envelopes returned to `send` or `broadcast`, such as `UNKNOWN_TARGET`, are printed and return a non-zero exit code.

`start.sh` is a local development/demo helper that delegates to these package entry points.
