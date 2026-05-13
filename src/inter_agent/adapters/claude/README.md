# Claude Code Adapter

Claude Code adapter for the inter-agent message bus.

## Commands

Run Claude adapter commands through the installed package entry point:

- `uv run inter-agent-claude listen --name <name> [--label <label>]`
- `uv run inter-agent-claude send <to> <text>`
- `uv run inter-agent-claude broadcast <text>`
- `uv run inter-agent-claude list [--json]`
- `uv run inter-agent-claude status [--json]`
- `uv run inter-agent-claude shutdown`
- `uv run inter-agent-claude disconnect`

Start the server in another terminal before connecting sessions:

- `uv run inter-agent-server`

## Example workflow

1. Connect two Claude Code sessions using the Monitor listener:
   ```
   /inter-agent connect agent-a
   ```

2. Send a direct message to a routing name:
   ```
   /inter-agent send agent-b "run tests"
   ```

3. Broadcast to all connected agent sessions:
   ```
   /inter-agent broadcast "build is green"
   ```

4. Inspect sessions and server state:
   ```
   /inter-agent list
   /inter-agent status
   ```

5. Disconnect from the bus:
   ```
   /inter-agent disconnect
   ```

6. Stop the local server:
   ```
   /inter-agent shutdown
   ```

## Output and failures

Command output is JSON-oriented. Stdout is reserved for protocol or status payloads. Stderr is reserved for local diagnostics.

`status` prints a JSON status object with `state`, `host`, `port`, `server_reachable`, `identity_verified`, `message`, `core_list_supported`, and `adapter_list_exposed` fields.

## Development helper

`start.sh` is a local development/demo helper that delegates to the package entry points.
