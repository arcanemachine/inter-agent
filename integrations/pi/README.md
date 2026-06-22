# pi-inter-agent

Pi extension for connecting to the [inter-agent](https://github.com/arcanemachine/inter-agent) message bus.

## Features

- **Background listener** — Stay connected to the bus and receive messages as Pi notifications, with automatic reconnection if the server restarts
- **Commands** — Connect, disconnect, send, broadcast, list, and status
- **Tools** — LLM-callable tools for send, broadcast, list, status, and local identity
- **State persistence** — Connection state survives Pi session reloads
- **Safe truncation** — Long messages are truncated to 1000 characters in notifications

## Installation

### 1. Install inter-agent

The extension needs the inter-agent package installed locally. Clone it to the default path:

```bash
git clone https://github.com/arcanemachine/inter-agent ~/.local/share/inter-agent
cd ~/.local/share/inter-agent
uv sync
```

If you clone to a different location, set `interAgent.projectPath` in your Pi settings (see Configuration below).

### 2. Install the Pi extension

```bash
pi install https://github.com/arcanemachine/pi-inter-agent
```

Or from a local clone:

```bash
git clone https://github.com/arcanemachine/pi-inter-agent
cd pi-inter-agent
pi install /path/to/pi-inter-agent
```

### Direct Load (Development)

```bash
pi -e /path/to/pi-inter-agent/src/index.ts
```

## Prerequisites

The inter-agent package must be installed on your machine. The extension calls the `inter-agent-pi`, `inter-agent-connect`, and `inter-agent-server` scripts directly from the project's virtual environment. It resolves the project path in this order:

1. `interAgent.projectPath` from `.pi/settings.json` or `~/.pi/agent/settings.json`
2. `~/.local/share/inter-agent` (default fallback)

If you cloned inter-agent to a location other than `~/.local/share/inter-agent`, you must set `interAgent.projectPath` in your Pi settings. Otherwise the extension will fail with a generic setup message.

## Configuration

You can override the inter-agent project path and endpoint in your Pi `settings.json`:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent",
    "host": "127.0.0.1",
    "port": 16837,
    "dataDir": "/path/to/inter-agent-state"
  }
}
```

Project settings (`.pi/settings.json`) override global settings (`~/.pi/agent/settings.json`). If `host`, `port`, or `dataDir` are set, the extension passes them to helper subprocesses as `INTER_AGENT_HOST`, `INTER_AGENT_PORT`, and `INTER_AGENT_DATA_DIR`. If they are unset, helpers use the standard inter-agent environment and config-file discovery described in the root README.

`projectPath` and `dataDir` may be absolute or relative. Relative paths are resolved relative to the settings file that declares them. For example, from `/workspace/.pi/settings.json`, use `../projects/inter-agent` for `/workspace/projects/inter-agent`. From `~/.pi/agent/settings.json`, relative paths are anchored at `~/.pi/agent/`. `~` is also supported.

If you do not set a project path, the extension falls back to `~/.local/share/inter-agent`.

## Commands

All inter-agent commands are grouped under `/inter-agent`. Type `/inter-agent ` and Pi will autocomplete the subcommand.

| Subcommand   | Usage                                           | Description                                                               |
| ------------ | ----------------------------------------------- | ------------------------------------------------------------------------- |
| `connect`    | `/inter-agent connect <name> [--label <label>]` | Connect to the bus as `name`                                              |
| `disconnect` | `/inter-agent disconnect`                       | Disconnect from the bus                                                   |
| `rename`     | `/inter-agent rename <name> [--label <label>]`  | Reconnect with a new routing name                                         |
| `send`       | `/inter-agent send <to> <text>`                 | Send a direct message (requires connection)                               |
| `broadcast`  | `/inter-agent broadcast <text>`                 | Broadcast to all agents only when messaging everyone is explicitly needed |
| `list`       | `/inter-agent list`                             | List connected sessions                                                   |
| `status`     | `/inter-agent status`                           | Check server status                                                       |

## Tools

Tools are agent-callable; they are not user-facing slash commands.

| Tool                    | Description                                                      |
| ----------------------- | ---------------------------------------------------------------- |
| `inter_agent_send`      | Send a direct message to a routing name                          |
| `inter_agent_broadcast` | Broadcast only when the user explicitly asks to message everyone |
| `inter_agent_list`      | List connected agent sessions                                    |
| `inter_agent_whoami`    | Report this Pi session's local identity                          |
| `inter_agent_status`    | Check server availability and identity                           |

## Troubleshooting

### `inter-agent status command was not found`

Pi may show this during connect or status checks:

```text
[inter-agent] connect failed: inter-agent status command was not found. Check that inter-agent is installed and configured, then try again.
```

or:

```text
[inter-agent] status failed: inter-agent status command was not found. Check that inter-agent is installed and configured, then try again.
```

The extension runs helper scripts from `<interAgent.projectPath>/.venv/bin`. This error means Pi could not run the helper script. Common causes are:

- `interAgent.projectPath` points to the wrong clone.
- The inter-agent virtual environment has not been created.
- The virtual environment was created at another filesystem path, leaving stale script shebangs.

Repair the local install and verify the helper directly:

```bash
cd /path/to/inter-agent
uv sync --locked
.venv/bin/inter-agent-pi status --json
```

If you use a non-default clone location, make sure Pi settings contain the matching path:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent"
  }
}
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

## Finishing Up

When you're done using the inter-agent bus, disconnect this Pi session:

```
/inter-agent disconnect
```

This stops your listener and removes you from the bus. If Pi auto-started the server, it shuts itself down after 300 seconds with no connected sessions. If you started the server manually, it runs until you shut it down.

If the server connection closes unexpectedly, the listener reconnects automatically with bounded backoff. It auto-starts the server if it is not running. After repeated failures the listener gives up and shows a notification with the exact `/inter-agent connect ...` command to retry manually.

## User Acceptance Test

To verify the extension works end-to-end:

1. **Install inter-agent** (one time):

   ```bash
   git clone https://github.com/arcanemachine/inter-agent ~/.local/share/inter-agent
   cd ~/.local/share/inter-agent
   uv sync
   ```

2. **Install the extension** (one time):

   ```bash
   pi install https://github.com/arcanemachine/pi-inter-agent
   ```

3. **Start Pi with the extension**:

   ```bash
   pi -e /path/to/pi-inter-agent/src/index.ts
   ```

4. **Run these commands in Pi** and confirm each works:
   - `/inter-agent connect test-agent` → should auto-start the server if needed, then show "connected"
   - `/inter-agent status` → should show "State: available"
   - `/inter-agent list` → should show "no agents connected" (or your own session)
   - `/inter-agent send test-agent "hello self"` → should show "sent" (only works when connected)
   - `/inter-agent broadcast "test broadcast for everyone"` → should show "sent" (only works when connected; reserve for messages everyone needs)
   - `/inter-agent rename test-agent-2` → should reconnect under the new name
   - `/inter-agent disconnect` → should show "disconnected"

5. **Verify incoming messages**: In another terminal, connect a second agent and send a message to `test-agent`. You should see a Pi notification.

## Development

```bash
cd /path/to/pi/pi-inter-agent
npm install
npm run typecheck
npm run build
npm run format
```

## License

MIT
