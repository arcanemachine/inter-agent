# Claude Code Adapter

Claude Code adapter for the inter-agent message bus.

## Commands

Run Claude adapter commands through the installed package entry point:

- `uv run inter-agent-claude listen --name <name> [--label <label>]`
- `uv run inter-agent-claude send <to> <text>`
- `uv run inter-agent-claude broadcast <text>`
- `uv run inter-agent-claude subscribe <channel>`
- `uv run inter-agent-claude unsubscribe <channel>`
- `uv run inter-agent-claude publish <channel> <text>`
- `uv run inter-agent-claude channels [--json]`
- `uv run inter-agent-claude list [--json]`
- `uv run inter-agent-claude status [--json]`
- `uv run inter-agent-claude messages <msg_id> [--json]`
- `uv run inter-agent-claude shutdown`
- `uv run inter-agent-claude disconnect`

`send`, `broadcast`, `subscribe`, `unsubscribe`, and `publish` require an active listener for the current Claude Code session. The adapter uses that listener's connected routing name as the sender name. Use `send` for normal replies and targeted coordination. Use `broadcast` only when the user explicitly asks to message everyone or the information is genuinely for every connected session.

`send` and `broadcast` suppress identical repeated invocations within a short window (a few seconds) so that an agent loop re-firing the same command does not produce duplicate deliveries. A later re-send of the same text after the window passes is delivered normally.

`messages <msg_id>` reads the full text of a truncated inbound message from the bounded local continuation cache by message ID, so the agent does not have to grep or tail the log file directly. The cache defaults to 5 MiB and can be adjusted for manual testing with `INTER_AGENT_CLAUDE_MESSAGES_LOG_MAX_BYTES`.

## Channels (pub/sub)

`subscribe` and `unsubscribe` operate on the matched live listener for the current session, not on a new connection. They are delivered through a private local Unix-domain control socket and print the raw protocol acknowledgment JSON (`subscribe_ok` / `unsubscribe_ok`) on success. Protocol errors print an adapter-prefixed diagnostic to stderr and return a non-zero exit code. A missing, stale, or reconnecting listener fails cleanly without a traceback.

`publish <channel> <text>` publishes to a channel. Claude publish requires the active listener identity and ignores any caller-supplied sender; it applies short-window duplicate suppression keyed by sender, channel, and text so an agent loop re-firing the same command does not produce duplicate deliveries. Claude publish success is silent (stdout stays empty); protocol errors such as `UNKNOWN_CHANNEL` are reported on stderr with a non-zero exit code.

`channels [--json]` lists channels and their subscribers as the raw `channels_ok` protocol JSON.

Inbound channel messages are rendered distinctly as `kind="channel" channel="<channel>"`; direct and broadcast notifications keep their existing `kind="direct"` and `kind="broadcast"` output. Channel messages retain truncation, continuation lookup, receive deduplication, and sanitization behavior.

Subscriptions are retained across transient listener reconnects: the listener re-applies the desired subscription set after reconnecting and before reporting readiness. Subscriptions are not persisted across an explicit listener stop or process restart; there are no automatic or default subscriptions.

## Server auto-start and idle timeout

The `listen` command auto-starts the server if it is not already running. Listener-started servers use an explicit 300-second idle timeout and shut down after that period with no connected sessions. You do not need to start the server manually before using the listener; if you do start `inter-agent-server` manually, it runs until explicit shutdown unless you pass `--idle-timeout <seconds>`.

## Example workflow

1. Connect two Claude Code sessions using the Monitor listener:
   ```
   /inter-agent connect agent-a
   ```

2. Send a direct message to a routing name:
   ```
   /inter-agent send agent-b "run tests"
   ```

3. Broadcast only when every connected session needs the message:
   ```
   /inter-agent broadcast "build is green for everyone"
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

`status` prints a JSON status object with `state`, `host`, `port`, `server_reachable`, `message`, `core_list_supported`, `adapter_list_exposed`, `connected`, and `connected_name` fields. `connected` is true when a live listener is registered for the current Claude Code session; `connected_name` is the routing name that listener uses (or null when not connected).

## Permanent errors

The listener exits without reconnecting on permanent errors: `AUTH_FAILED`, `BAD_ROLE`, `BAD_NAME`, `BAD_SESSION`, `SESSION_TAKEN`, `BAD_LABEL`, `TOO_MANY_CONNECTIONS`. On `NAME_TAKEN`, the Claude listener retries once with a `-2` suffix and exits only if that retry is also taken. Transient errors trigger reconnection with bounded backoff.

## Development helper

`./start` is a local development/demo helper that delegates to the package entry points.
