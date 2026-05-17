# pi-inter-agent

Pi extension for connecting to the [inter-agent](https://github.com/arcanemachine/inter-agent) message bus.

## Features

- **Background listener** — Stay connected to the bus and receive messages as Pi notifications
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

You do not need to keep a server terminal open for normal Pi usage. `/inter-agent-connect` auto-starts the server when no healthy server is available.

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

If neither location works, the extension reports a generic setup message and you must set `interAgent.projectPath`.

## Configuration

You can override the default inter-agent project path in your Pi `settings.json`:

```json
{
  "interAgent": {
    "projectPath": "/path/to/inter-agent"
  }
}
```

Project settings (`.pi/settings.json`) override global settings (`~/.pi/agent/settings.json`).

If you do not set a project path, the extension falls back to `~/.local/share/inter-agent`.

## Commands

| Command                   | Usage                                           | Description                  |
| ------------------------- | ----------------------------------------------- | ---------------------------- |
| `/inter-agent-connect`    | `/inter-agent-connect <name> [--label <label>]` | Connect to the bus as `name` |
| `/inter-agent-disconnect` | `/inter-agent-disconnect`                       | Disconnect from the bus      |
| `/inter-agent-send`       | `/inter-agent-send <to> <text>`                 | Send a direct message        |
| `/inter-agent-broadcast`  | `/inter-agent-broadcast <text>`                 | Broadcast to all agents      |
| `/inter-agent-list`       | `/inter-agent-list`                             | List connected sessions      |
| `/inter-agent-status`     | `/inter-agent-status`                           | Check server status          |

## Tools

Tools are agent-callable; they are not user-facing slash commands.

| Tool                    | Description                             |
| ----------------------- | --------------------------------------- |
| `inter_agent_send`      | Send a direct message to a routing name |
| `inter_agent_broadcast` | Broadcast a message to all agents       |
| `inter_agent_list`      | List connected agent sessions           |
| `inter_agent_whoami`    | Report this Pi session's local identity |
| `inter_agent_status`    | Check server availability and identity  |

## Example Workflow

1. In Pi, connect to the bus. If no healthy server is available, the extension starts one and then connects:

   ```
   /inter-agent-connect my-pi-session --label "Pi Agent"
   ```

2. Send a message to another agent:

   ```
   /inter-agent-send agent-b "run tests"
   ```

3. Or broadcast to everyone:

   ```
   /inter-agent-broadcast "build is green"
   ```

4. Check who's connected:
   ```
   /inter-agent-list
   ```

## Finishing Up

When you're done using the inter-agent bus, disconnect this Pi session:

```
/inter-agent-disconnect
```

This stops your listener and removes you from the bus, but leaves the server running for other agents. If the server connection closes unexpectedly, Pi shows a user-facing disconnected notification with the exact `/inter-agent-connect ...` command the user can run to reconnect. The agent does not reconnect itself automatically. If Pi auto-started the server, it shuts itself down after 300 seconds with no connected sessions. If you started the server manually, it runs until you shut it down.

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
   - `/inter-agent-connect test-agent` → should start the server if needed, then show "connected"
   - `/inter-agent-status` → should show "State: available"
   - `/inter-agent-list` → should show "no agents connected" (or your own session)
   - `/inter-agent-send test-agent "hello self"` → should show "sent"
   - `/inter-agent-broadcast "test broadcast"` → should show "sent"
   - `/inter-agent-disconnect` → should show "disconnected"

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
