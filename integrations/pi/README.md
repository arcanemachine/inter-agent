# pi-inter-agent

Pi extension for connecting Pi sessions to the [inter-agent](https://github.com/arcanemachine/inter-agent) message bus.

Connect each Pi session once, then Pi can use the extension tools to send messages, ask other connected agents questions, and coordinate work. You can use slash commands directly, but normal agent-to-agent coordination can happen through the LLM-callable tools after connection.

## Features

- **Background listener** — Stay connected to the bus and receive messages as Pi notifications, with automatic reconnection if the server restarts
- **Commands** — Connect, disconnect, rename, send, broadcast, publish, subscribe, unsubscribe, list, and status
- **Channels** — User-controlled pub/sub: subscribe, unsubscribe, and publish through explicit slash commands; channel deliveries are shown as channel messages, not direct or broadcast
- **Tools** — LLM-callable tools for send, broadcast, list, status, and local identity
- **State persistence** — Connection state survives Pi session reloads
- **Collapsible messages** — Inter-agent message rows show a compact metadata line (recipient/direction and char count) when collapsed and the full message when expanded
- **Safe truncation** — Long messages are truncated to 1000 characters in notifications

## Installation

Recommended local setup uses one prepared inter-agent checkout for the Python runtime and this Pi extension:

```bash
git clone https://github.com/arcanemachine/inter-agent /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
pi install /path/to/inter-agent/integrations/pi
```

Then set the checkout path in `.pi/settings.json` for the current workspace or `~/.pi/agent/settings.json` globally:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent"
  }
}
```

You can also install from the repository root as a Pi git package:

```bash
pi install https://github.com/arcanemachine/inter-agent
```

Direct-load the extension during development with:

```bash
pi -e /path/to/inter-agent/integrations/pi/src/index.ts
```

## Runtime setup

The Pi package installs the Pi extension assets. The Python inter-agent runtime can come from a checkout, a Pi-managed venv, or existing helper commands on `PATH`. Runtime source is separate from bus auth/state: all runtime options use the same default endpoint (`127.0.0.1:16837`) and secret discovery.

The extension resolves helpers in this order:

1. `INTER_AGENT_PI_HELPER`, as an exact path to `inter-agent-pi`.
2. `interAgent.projectPath` from `.pi/settings.json` or `~/.pi/agent/settings.json`, using `<projectPath>/.venv/bin`.
3. legacy checkout fallback at `~/.local/share/inter-agent`, only when helper scripts already exist there.
4. Pi-managed runtime at `~/.pi/agent/inter-agent/venv`.
5. `inter-agent-pi`, `inter-agent-connect`, and `inter-agent-server` on `PATH`.

If no runtime is found, Pi reports setup needed and points back to this section.

### Checkout runtime

Use a checkout when developing inter-agent or when you want explicit local control:

```bash
git clone https://github.com/arcanemachine/inter-agent /path/to/inter-agent
cd /path/to/inter-agent
uv sync --locked
```

Then configure Pi:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent"
  }
}
```

An explicit `projectPath` is fail-fast. If helpers are missing from that checkout, the extension reports the expected path instead of silently falling through to another runtime.

### Managed runtime

Create the Pi-managed venv manually when you do not want Pi to use a checkout runtime:

```bash
python3 -m venv ~/.pi/agent/inter-agent/venv
~/.pi/agent/inter-agent/venv/bin/python -m pip install --upgrade \
  https://github.com/arcanemachine/inter-agent/archive/refs/heads/main.zip
~/.pi/agent/inter-agent/venv/bin/inter-agent-pi status --json
```

After creating the venv, retry the Pi command. If Pi was already running and still reports setup needed, run `/reload` or restart Pi so the extension reloads. The GitHub `main` archive is a pre-release install source until stable package releases are available.

## Configuration

You can override the inter-agent project path, endpoint, and TLS settings in your Pi `settings.json`. Only set a key when you want a non-default value:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent",
    "host": "127.0.0.1",
    "port": 16837,
    "dataDir": "~/.local/state/inter-agent",
    "secret": "high-entropy-shared-secret",
    "tls": false,
    "tlsCert": "/path/to/tls-cert.pem",
    "tlsKey": "/path/to/tls-key.pem"
  }
}
```

When Pi shares the same local inter-agent state directory as the server, leave `host`, `port`, `dataDir`, and `secret` unset so helpers use the standard endpoint and generated fallback secret. For separate harnesses, containers, or isolated filesystems, set the same reachable endpoint and high-entropy `secret` everywhere. Set `projectPath` when you want Pi to use a specific checkout runtime.

Project settings (`.pi/settings.json`) override global settings (`~/.pi/agent/settings.json`). If `host`, `port`, `dataDir`, or `secret` are set, the extension passes them to helper subprocesses as `INTER_AGENT_HOST`, `INTER_AGENT_PORT`, `INTER_AGENT_DATA_DIR`, and `INTER_AGENT_SECRET`. If they are unset, helpers use the standard inter-agent environment and config-file discovery described in the root README.

`projectPath` is the inter-agent project clone the extension runs helper scripts from. `dataDir` is where inter-agent stores fallback generated secret and TLS state, kept separate from your hand-edited config (the inter-agent config file lives under `~/.config/inter-agent` on Linux or `~/Library/Application Support/inter-agent` on macOS). The platform default for `dataDir` works for normal single-bus use; set it only when you want a custom fallback state location. Use `secret` to connect Pi to a server whose fallback state it cannot share, such as a server in another container. When set, use the same high-entropy value everywhere.

`tls` enables (`true`) or disables (`false`) WebSocket TLS. Loopback hosts default to plaintext unless TLS is explicitly enabled; non-loopback hosts default to TLS unless explicitly disabled. `tlsCert` and `tlsKey` override the generated default certificate and key in `dataDir`. If TLS is enabled and no certificate/key is configured, the server generates `tls-cert.pem` and `tls-key.pem` in `dataDir` with restrictive permissions, and clients trust that generated certificate or the configured `tlsCert`. These settings are passed to helpers as `INTER_AGENT_TLS`, `INTER_AGENT_TLS_CERT`, and `INTER_AGENT_TLS_KEY` when set.

`projectPath` and `dataDir` may be absolute or relative. Relative paths are resolved relative to the settings file that declares them. For example, from `/workspace/.pi/settings.json`, use `../projects/inter-agent` for `/workspace/projects/inter-agent`. From `~/.pi/agent/settings.json`, relative paths are anchored at `~/.pi/agent/`. `~` is also supported.

## Commands

All inter-agent commands are grouped under `/inter-agent`. Type `/inter-agent ` and Pi will autocomplete the subcommand.

| Subcommand    | Usage                                           | Description                                                               |
| ------------- | ----------------------------------------------- | ------------------------------------------------------------------------- |
| `connect`     | `/inter-agent connect <name> [--label <label>]` | Connect to the bus as `name`                                              |
| `disconnect`  | `/inter-agent disconnect`                       | Disconnect from the bus                                                   |
| `rename`      | `/inter-agent rename <name> [--label <label>]`  | Reconnect with a new routing name                                         |
| `send`        | `/inter-agent send <to> <text>`                 | Send a direct message (requires connection)                               |
| `broadcast`   | `/inter-agent broadcast <text>`                 | Broadcast to all agents only when messaging everyone is explicitly needed |
| `publish`     | `/inter-agent publish <channel> <text>`         | Publish to channel subscribers (requires connection; user-only)           |
| `subscribe`   | `/inter-agent subscribe <channel>`              | Subscribe to a channel (requires connection; user-only)                   |
| `unsubscribe` | `/inter-agent unsubscribe <channel>`            | Unsubscribe from a channel (requires connection; user-only)               |
| `list`        | `/inter-agent list`                             | List connected sessions                                                   |
| `status`      | `/inter-agent status`                           | Check server status                                                       |

`send`, `broadcast`, and `publish` automatically use the current Pi connection name as the sender. `subscribe` and `unsubscribe` operate on the current Pi listener's live session and pass its routing name internally; you never provide or manage the listener name.

## Channels

Channels are user-controlled pub/sub. Subscribe to a named channel to receive messages published to it, and unsubscribe to stop. Subscriptions belong to the current Pi listener session.

- **No automatic subscriptions.** Nothing is subscribed by default; you subscribe explicitly with `/inter-agent subscribe <channel>`.
- **Not persisted across restarts.** Subscriptions are not retained across an explicit `/inter-agent disconnect`, a Pi listener restart, or a Pi session reload. Re-establish subscriptions after any of these.
- **User-only control.** Subscribe, unsubscribe, and publish are slash commands only. There are no LLM-callable tools for these operations, so channel membership and publication remain under explicit user control. Pi does not publish autonomously, infer publication from peer messages, or publish acknowledgments.
- **Publication identity and delivery.** `/inter-agent publish <channel> <text>` requires the current Pi listener and always uses its connected routing name as the publisher. The publisher does not need to subscribe first and is excluded from delivery even when subscribed. Success shows a Pi notification and outbound-history entry. Local or protocol failures use the existing helper diagnostic; `UNKNOWN_CHANNEL` means the channel does not exist or has no subscribers.
- **Distinct delivery.** An inbound channel message is shown with an `on <channel>` label in both the Pi notification and the agent context, so it is not mistaken for a direct or broadcast message. Existing untrusted-peer guidance, truncation, and display/context separation still apply.

## Tools

Tools are agent-callable; they are not user-facing slash commands.

| Tool                    | Description                                                      |
| ----------------------- | ---------------------------------------------------------------- |
| `inter_agent_send`      | Send a direct message to a routing name                          |
| `inter_agent_broadcast` | Broadcast only when the user explicitly asks to message everyone |
| `inter_agent_list`      | List connected agent sessions                                    |
| `inter_agent_whoami`    | Report this Pi session's local identity                          |
| `inter_agent_status`    | Check server availability                                        |

## Troubleshooting

### Setup needed

Pi may show this during connect or status checks:

```text
[inter-agent] setup needed. See integrations/pi/README.md
```

Follow [Runtime setup](#runtime-setup), then retry the command. If Pi was already running while you created a runtime, run `/reload` or restart Pi.

### Configured checkout missing helpers

If `interAgent.projectPath` is set and helpers are missing, Pi reports the expected `<projectPath>/.venv/bin` path:

```text
[inter-agent] connect failed: inter-agent runtime was not found at /path/to/inter-agent/.venv/bin. See integrations/pi/README.md
```

Common causes are:

- `interAgent.projectPath` points to the wrong clone.
- The path exists on the host but not inside the environment where Pi is running.
- The inter-agent virtual environment has not been created.
- The virtual environment was created at another filesystem path, leaving stale script shebangs.

Repair the local install and verify the helper directly:

```bash
cd /path/to/inter-agent
uv sync --locked
.venv/bin/inter-agent-pi status --json
```

Relative project-local example for `/workspace/.pi/settings.json`:

```json
{
  "interAgent": {
    "projectPath": "../projects/inter-agent"
  }
}
```

## Example Workflow

1. In Pi, connect to the bus. The extension auto-starts the server if needed:

   ```
   /inter-agent connect my-pi-session --label "Pi Agent"
   ```

2. Send a message to another agent (requires an active connection):

   ```
   /inter-agent send agent-b "run tests"
   ```

3. Broadcast only when everyone needs the message (requires an active connection):

   ```
   /inter-agent broadcast "build is green for everyone"
   ```

   For replies or targeted coordination, prefer `/inter-agent send <name> <text>`.

4. Rename the current Pi session if needed:

   ```
   /inter-agent rename my-pi-session-2
   ```

5. Check who's connected:

   ```
   /inter-agent list
   ```

6. Subscribe to a channel (requires an active connection):

   ```
   /inter-agent subscribe updates
   ```

   Publish to `updates` from this Pi session or another connected adapter. The publisher is excluded, so use another subscriber when verifying delivery:

   ```
   /inter-agent publish updates "build is green"
   ```

   Subscribers should see a channel-specific notification labeled `on updates`, distinct from direct and broadcast messages. Unsubscribe when done:

   ```
   /inter-agent unsubscribe updates
   ```

   Subscriptions are not retained after `/inter-agent disconnect`, a listener restart, or a session reload; re-subscribe after any of these.

## Finishing Up

When you're done using the inter-agent bus, disconnect this Pi session:

```
/inter-agent disconnect
```

This stops your listener and removes you from the bus. If Pi auto-started the server, it shuts itself down after 300 seconds with no connected sessions. If you started the server manually, it runs until you shut it down.

If the server connection closes unexpectedly, the listener reconnects automatically with bounded backoff. It auto-starts the server if it is not running. After repeated failures the listener gives up and shows a notification with the exact `/inter-agent connect ...` command to retry manually.

## User Acceptance Test

To verify the extension works end-to-end:

1. **Install the extension** (one time):

   ```bash
   pi install https://github.com/arcanemachine/inter-agent
   ```

2. **Prepare a runtime** with either `interAgent.projectPath` or the managed venv from [Runtime setup](#runtime-setup).

3. **Run these commands in Pi** and confirm each works:
   - `/inter-agent connect test-agent` → should auto-start the server if needed, then show "connected"
   - `/inter-agent status` → should show "State: available"
   - `/inter-agent list` → should show "no agents connected" (or your own session)
   - `/inter-agent send test-agent "hello self"` → should show "sent" (only works when connected)
   - `/inter-agent broadcast "test broadcast for everyone"` → should show "sent" (only works when connected; reserve for messages everyone needs)
   - `/inter-agent publish updates "test channel message"` → should show publication success when `updates` has another subscriber; otherwise it should report `UNKNOWN_CHANNEL`
   - `/inter-agent subscribe updates` → should show "subscribed: updates" (only works when connected)
   - `/inter-agent unsubscribe updates` → should show "unsubscribed: updates" (only works when connected)
   - `/inter-agent rename test-agent-2` → should reconnect under the new name
   - `/inter-agent disconnect` → should show "disconnected"

4. **Verify incoming messages**: In another terminal, connect a second agent and send a message to `test-agent`. You should see a Pi notification.

5. **Verify channel delivery**: Subscribe a second session to `updates`, then run `/inter-agent publish updates "hello channel"` in Pi. The second subscriber should receive a channel-specific notification labeled `on updates`; Pi should show publication success and an `on updates` outbound-history entry, while the publisher receives no copy. Run `/inter-agent unsubscribe updates`, publish again after all subscribers leave, and confirm `UNKNOWN_CHANNEL`. Confirm the tool list does not contain publish, subscribe, or unsubscribe tools. Subscriptions do not persist across `/inter-agent disconnect` or a listener restart; re-subscribe after these.

## Development

```bash
cd /path/to/inter-agent/integrations/pi
npm install
npm run typecheck
npm run build
npm run format
```

## License

MIT
