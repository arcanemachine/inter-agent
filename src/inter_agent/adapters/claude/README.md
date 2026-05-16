# Claude Code Adapter

Claude Code adapter for the inter-agent message bus.

## Commands

Run Claude adapter commands through the installed package entry point:

- `uv run inter-agent-claude listen --name <name> [--label <label>]`
- `uv run inter-agent-claude send <to> <text> [--from <name>]`
- `uv run inter-agent-claude broadcast <text> [--from <name>]`
- `uv run inter-agent-claude list [--json]`
- `uv run inter-agent-claude status [--json]`
- `uv run inter-agent-claude shutdown`
- `uv run inter-agent-claude disconnect`

When sending on behalf of a connected agent, pass `--from <name>` so recipients see the correct sender name instead of "control".

## Server auto-start and idle timeout

The `listen` command auto-starts the server if it is not already running. The server shuts down automatically after 300 seconds with no connected sessions (configurable via `--idle-timeout` with `inter-agent-server`, or `--idle-timeout 0` to disable). You do not need to start the server manually before using the listener.

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

## Permanent errors

The listener exits without reconnecting on permanent errors: `AUTH_FAILED`, `BAD_ROLE`, `BAD_NAME`, `BAD_SESSION`, `NAME_TAKEN`, `SESSION_TAKEN`, `BAD_LABEL`, `TOO_MANY_CONNECTIONS`. Transient errors trigger reconnection with bounded backoff.

## Development helper

`./start` is a local development/demo helper that delegates to the package entry points.
