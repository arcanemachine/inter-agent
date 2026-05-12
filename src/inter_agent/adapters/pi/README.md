# Pi Adapter

Pi-facing command UX built on top of the universal core protocol. Pi users should run `inter-agent-pi` commands rather than the lower-level core protocol commands.

## Commands

Run Pi adapter commands through the installed package entry point:

- `uv run inter-agent-pi connect <name> [--label <label>]`
- `uv run inter-agent-pi send <to> <text>`
- `uv run inter-agent-pi broadcast <text>`
- `uv run inter-agent-pi list [--json]`
- `uv run inter-agent-pi status [--json]`

Start the server in another terminal before connecting sessions:

- `uv run inter-agent-server`

## Example workflow

1. Connect two Pi sessions in separate terminals:
   - `uv run inter-agent-pi connect agent-a --label "Agent A"`
   - `uv run inter-agent-pi connect agent-b --label "Agent B"`

2. Send a direct message to a routing name:
   - `uv run inter-agent-pi send agent-b "run tests"`

3. Broadcast to all connected agent sessions:
   - `uv run inter-agent-pi broadcast "build is green"`

4. Inspect sessions and server state:
   - `uv run inter-agent-pi list --json`
   - `uv run inter-agent-pi status --json`

`label` is optional display metadata; routing still uses `name`. `list` is core-supported and adapter-exposed.

## Output and failures

Pi command output is JSON-oriented. `connect`, `send`, `broadcast`, and `list` print core protocol envelopes as JSON lines. `status` prints a JSON status object with `state`, `host`, `port`, `server_reachable`, `identity_verified`, `message`, `core_list_supported`, and `adapter_list_exposed` fields. `state` is one of `available`, `unavailable`, or `identity_check_failed`; `status` returns exit code 0 so host tooling can inspect the state field.

Pi commands perform the core localhost server identity check before sending the shared token; unavailable identity returns a non-zero exit code for message and list operations. Protocol error envelopes returned to `send` or `broadcast`, such as `UNKNOWN_TARGET`, are printed and return a non-zero exit code.

## Development helper

`start.sh` is a local development/demo helper that delegates to these package entry points. For a bounded smoke check, run `./start.sh status --json` from the repository root.
