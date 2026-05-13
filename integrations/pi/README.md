# pi-inter-agent

Pi extension for connecting to the [inter-agent](https://github.com/arcanemachine/inter-agent) message bus.

## Features

- **Background listener** — Stay connected to the bus and receive messages as Pi notifications
- **Commands** — Connect, disconnect, send, broadcast, list, status, shutdown
- **Tools** — LLM-callable tools for send, broadcast, list, and status
- **State persistence** — Connection state survives Pi session reloads
- **Safe truncation** — Long messages are truncated to 1000 characters in notifications

## Installation

### 1. Install the inter-agent server

The extension needs the inter-agent server running locally. Clone it to the default path:

```bash
git clone https://github.com/arcanemachine/inter-agent ~/.local/share/inter-agent
cd ~/.local/share/inter-agent
uv sync
```

Then start the server (keep this terminal open):

```bash
uv run inter-agent-server
```

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

The inter-agent server must be running on your machine:

```bash
cd /path/to/inter-agent
uv run inter-agent-server
```

The extension calls the `inter-agent-pi` and `inter-agent-connect` scripts directly from the project's virtual environment. It resolves the project path in this order:

1. `interAgent.projectPath` from `.pi/settings.json` or `~/.pi/agent/settings.json`
2. `~/.local/share/inter-agent` (default fallback)

If neither location works, the extension will error and you must set `interAgent.projectPath`.

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

| Command                   | Usage                                 | Description                  |
| ------------------------- | ------------------------------------- | ---------------------------- |
| `/inter-agent-connect`    | `/inter-agent-connect <name> [label]` | Connect to the bus as `name` |
| `/inter-agent-disconnect` | `/inter-agent-disconnect`             | Disconnect from the bus      |
| `/inter-agent-send`       | `/inter-agent-send <to> <text>`       | Send a direct message        |
| `/inter-agent-broadcast`  | `/inter-agent-broadcast <text>`       | Broadcast to all agents      |
| `/inter-agent-list`       | `/inter-agent-list`                   | List connected sessions      |
| `/inter-agent-status`     | `/inter-agent-status`                 | Check server status          |
| `/inter-agent-shutdown`   | `/inter-agent-shutdown`               | Stop the server              |

## Tools

| Tool                    | Description                             |
| ----------------------- | --------------------------------------- |
| `inter_agent_send`      | Send a direct message to a routing name |
| `inter_agent_broadcast` | Broadcast a message to all agents       |
| `inter_agent_list`      | List connected agent sessions           |
| `inter_agent_status`    | Check server availability and identity  |

## Example Workflow

1. Start the server in another terminal:

   ```bash
   cd ~/.local/share/inter-agent
   uv run inter-agent-server
   ```

2. In Pi, connect to the bus:

   ```
   /inter-agent-connect my-pi-session --label "Pi Agent"
   ```

3. Send a message to another agent:

   ```
   /inter-agent-send agent-b "run tests"
   ```

4. Or broadcast to everyone:

   ```
   /inter-agent-broadcast "build is green"
   ```

5. Check who's connected:
   ```
   /inter-agent-list
   ```

## Finishing Up

When you're done using the inter-agent bus, you have two choices depending on whether others are still using it.

### Disconnect yourself (server keeps running)

This stops your listener and removes you from the bus, but leaves the server running for other agents:

```
/inter-agent-disconnect
```

### Shut down the server entirely

This stops the server and disconnects **all** agents. Use this only when you're the last one, or when you want to clean up:

```
/inter-agent-shutdown
```

**Recommended order:**

1. Disconnect yourself first (`/inter-agent-disconnect`)
2. If you started the server and no one else needs it, shut it down (`/inter-agent-shutdown`)
3. Stop the server terminal process if it's still running — go to the terminal where you ran `uv run inter-agent-server` and press **Ctrl+C**

## User Acceptance Test

To verify the extension works end-to-end:

1. **Install the server** (one time):

   ```bash
   git clone https://github.com/arcanemachine/inter-agent ~/.local/share/inter-agent
   cd ~/.local/share/inter-agent
   uv sync
   ```

2. **Install the extension** (one time):

   ```bash
   pi install https://github.com/arcanemachine/pi-inter-agent
   ```

3. **Start the inter-agent server** (in a separate terminal):

   ```bash
   cd ~/.local/share/inter-agent
   uv run inter-agent-server
   ```

4. **Start Pi with the extension**:

   ```bash
   pi -e /path/to/pi-inter-agent/src/index.ts
   ```

5. **Run these commands in Pi** and confirm each works:
   - `/inter-agent-status` → should show "State: available"
   - `/inter-agent-connect test-agent` → should show "connected"
   - `/inter-agent-list` → should show "no agents connected" (or your own session)
   - `/inter-agent-send test-agent "hello self"` → should show "sent"
   - `/inter-agent-broadcast "test broadcast"` → should show "sent"
   - `/inter-agent-disconnect` → should show "disconnected"
   - `/inter-agent-shutdown` → should show "server stopped" (and other sessions disconnect)

6. **Verify incoming messages**: In another terminal, connect a second agent and send a message to `test-agent`. You should see a Pi notification.

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
