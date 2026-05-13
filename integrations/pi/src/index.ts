/**
 * pi-inter-agent
 * Pi extension for connecting to the inter-agent message bus
 *
 * Provides commands and tools to send, broadcast, list sessions, check status,
 * and receive incoming messages as Pi notifications.
 *
 * Installation:
 * ```bash
 * pi install https://github.com/arcanemachine/pi-inter-agent
 * ```
 *
 * Or load directly:
 * ```bash
 * pi -e /path/to/pi-inter-agent/src/index.ts
 * ```
 */

import type {
  ExtensionAPI,
  ExtensionContext,
} from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { spawn, ChildProcess } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// ── Configuration ───────────────────────────────────────────────────────────

interface InterAgentConfig {
  projectPath?: string;
}

interface Settings {
  interAgent?: InterAgentConfig;
}

const DEFAULT_PROJECT_PATH = join(homedir(), ".local", "share", "inter-agent");

function loadConfig(): InterAgentConfig {
  const globalSettingsPath = join(homedir(), ".pi", "agent", "settings.json");
  const projectSettingsPath = join(process.cwd(), ".pi", "settings.json");

  let config: InterAgentConfig = { projectPath: DEFAULT_PROJECT_PATH };

  // Load global settings first
  if (existsSync(globalSettingsPath)) {
    try {
      const parsed: Settings = JSON.parse(
        readFileSync(globalSettingsPath, "utf-8"),
      );
      if (parsed.interAgent) {
        config = { ...config, ...parsed.interAgent };
      }
    } catch {
      // Invalid JSON, ignore
    }
  }

  // Project settings override global
  if (existsSync(projectSettingsPath)) {
    try {
      const parsed: Settings = JSON.parse(
        readFileSync(projectSettingsPath, "utf-8"),
      );
      if (parsed.interAgent) {
        config = { ...config, ...parsed.interAgent };
      }
    } catch {
      // Invalid JSON, ignore
    }
  }

  return config;
}

function getScripts(config: InterAgentConfig) {
  const projectPath = config.projectPath || DEFAULT_PROJECT_PATH;
  const binDir = join(projectPath, ".venv", "bin");
  return {
    pi: join(binDir, "inter-agent-pi"),
    connect: join(binDir, "inter-agent-connect"),
  };
}

// ── Constants ───────────────────────────────────────────────────────────────

const NOTIFY_MAX_LEN = 1000;
const DEFAULT_NAME = "pi";

// ── State ───────────────────────────────────────────────────────────────────

interface ConnectionState {
  name: string;
  label: string | null;
  connected: boolean;
}

let listenerProc: ChildProcess | null = null;
let currentCtx: ExtensionContext | null = null;
let messageBuffer = "";

// ── Helpers ─────────────────────────────────────────────────────────────────

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + " …";
}

const FROM_PREFIX_RE = /^\[from: ([^\]]+)\] ?/;

function formatOutgoing(text: string, name: string): string {
  return `[from: ${name}] ${text}`;
}

function parseIncoming(text: string): { from: string | null; text: string } {
  const match = text.match(FROM_PREFIX_RE);
  if (match) {
    return { from: match[1], text: text.slice(match[0].length) };
  }
  return { from: null, text };
}

function getConnectionState(ctx: ExtensionContext): ConnectionState | null {
  const branch = ctx.sessionManager.getBranch();
  for (let i = branch.length - 1; i >= 0; i--) {
    const entry = branch[i];
    if (entry.type === "custom" && entry.customType === "inter-agent-state") {
      return entry.data as ConnectionState;
    }
  }
  return null;
}

function persistState(pi: ExtensionAPI, state: ConnectionState) {
  pi.appendEntry("inter-agent-state", state);
}

function notify(
  title: string,
  body: string,
  type: "info" | "warning" | "error" = "info",
) {
  currentCtx?.ui.notify(truncate(`${title}: ${body}`, NOTIFY_MAX_LEN), type);
}

function sendToContext(
  pi: ExtensionAPI,
  from: string,
  text: string,
  toInfo: string,
) {
  const replyInstruction =
    toInfo === "broadcast"
      ? "To reply to this broadcast, use the inter_agent_broadcast tool."
      : `To reply to ${from}, use the inter_agent_send tool with to="${from}".`;
  pi.sendMessage(
    {
      customType: "inter-agent-message",
      content: `[inter-agent message from ${from} ${toInfo}]

${text}

${replyInstruction}`,
      display: true,
      details: { from, text, toInfo },
    },
    { triggerTurn: true, deliverAs: "steer" },
  );
}

function showOutgoingInContext(
  pi: ExtensionAPI,
  from: string,
  text: string,
  toInfo: string,
) {
  pi.sendMessage(
    {
      customType: "inter-agent-message",
      content: `[inter-agent message sent by you (${from}) ${toInfo}]

${text}`,
      display: true,
      details: { from, text, toInfo, outgoing: true },
    },
    { triggerTurn: false, deliverAs: "steer" },
  );
}

function execScript(
  script: string,
  args: string[],
): Promise<{ stdout: string; stderr: string; code: number | null }> {
  return new Promise((resolve) => {
    const env = { ...process.env, PYTHONUNBUFFERED: "1" };
    const proc = spawn(script, args, {
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
      env,
    });
    let stdout = "";
    let stderr = "";
    proc.stdout?.on("data", (d: Buffer) => {
      stdout += d.toString();
    });
    proc.stderr?.on("data", (d: Buffer) => {
      stderr += d.toString();
    });
    proc.on("close", (code) => {
      resolve({ stdout, stderr, code });
    });
    proc.on("error", (err) => {
      const nodeErr = err as NodeJS.ErrnoException;
      if (nodeErr.code === "ENOENT") {
        stderr += `inter-agent not found at ${script}. Ensure the server is installed and available at the expected path. See Configuration in the README.`;
      } else {
        stderr += String(err);
      }
      resolve({ stdout, stderr, code: null });
    });
  });
}

// ── Listener Management ─────────────────────────────────────────────────────

function startListener(
  pi: ExtensionAPI,
  ctx: ExtensionContext,
  config: InterAgentConfig,
  name: string,
  label: string | null,
) {
  stopListener();

  const scripts = getScripts(config);
  const args = [name];
  if (label) args.push("--label", label);

  const proc = spawn(scripts.connect, args, {
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });

  listenerProc = proc;
  messageBuffer = "";

  proc.stdout?.on("data", (data: Buffer) => {
    messageBuffer += data.toString();
    const lines = messageBuffer.split("\n");
    messageBuffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.op === "welcome") {
          continue;
        }
        if (msg.op === "error") {
          const code = String(msg.code || "unknown");
          const text = String(msg.message || "connection rejected");
          notify(`[inter-agent] connect failed`, `${code}: ${text}`, "error");
          stopListener();
          const state = getConnectionState(ctx);
          if (state) {
            persistState(pi, { ...state, connected: false });
            updateStatus(ctx, { ...state, connected: false });
          }
          continue;
        }
        if (msg.op === "msg") {
          const fromRaw = msg.from_name || msg.from || "unknown";
          const textRaw = msg.text || "";
          const toInfo = msg.to ? `→ ${msg.to}` : "broadcast";
          const parsed = parseIncoming(textRaw);
          const from = parsed.from || fromRaw;
          const text = parsed.text;
          notify(`[inter-agent] ${from} ${toInfo}`, text);
          sendToContext(pi, from, text, toInfo);
        }
      } catch {
        // Ignore non-JSON lines
      }
    }
  });

  proc.stderr?.on("data", (data: Buffer) => {
    const text = data.toString().trim();
    if (text) {
      notify("[inter-agent] listener stderr", text, "warning");
    }
  });

  proc.on("exit", (code) => {
    if (listenerProc === proc) {
      listenerProc = null;
      if (code !== 0 && code !== null) {
        notify("[inter-agent] listener exited", `code ${code}`, "warning");
      }
    }
  });

  proc.on("error", (err) => {
    const nodeErr = err as NodeJS.ErrnoException;
    if (nodeErr.code === "ENOENT") {
      notify(
        "[inter-agent] listener error",
        `inter-agent-connect not found at ${scripts.connect}. Ensure the server is installed and available at the expected path. See Configuration in the README.`,
        "error",
      );
    } else {
      notify("[inter-agent] listener error", String(err), "error");
    }
  });

  const state: ConnectionState = { name, label, connected: true };
  persistState(pi, state);
  updateStatus(ctx, state);
}

function stopListener() {
  if (listenerProc) {
    listenerProc.kill("SIGTERM");
    listenerProc = null;
    messageBuffer = "";
  }
}

function updateStatus(ctx: ExtensionContext, state: ConnectionState | null) {
  if (state?.connected) {
    ctx.ui.setStatus("inter-agent", `Inter-agent name: ${state.name} 🌐 `);
  } else {
    ctx.ui.setStatus("inter-agent", undefined);
  }
}

// ── Extension Export ────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  const config = loadConfig();
  const scripts = getScripts(config);

  // ── Session Lifecycle ─────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    currentCtx = ctx;
    const state = getConnectionState(ctx);
    if (state?.connected) {
      startListener(pi, ctx, config, state.name, state.label);
      notify("[inter-agent] reconnected", `as ${state.name}`);
    }
  });

  pi.on("session_shutdown", async () => {
    stopListener();
    currentCtx = null;
  });

  pi.on("before_agent_start", async (event, ctx) => {
    const state = getConnectionState(ctx);
    if (!state?.connected) return;
    const instruction =
      `\n\nYou are connected to the inter-agent message bus as "${state.name}". ` +
      "To reply to an inter-agent message, use the inter_agent_send or inter_agent_broadcast tool. " +
      "Avoid unnecessary replies. Only update the user when they genuinely need to know something.";
    return {
      systemPrompt: event.systemPrompt + instruction,
    };
  });

  // ── Commands ──────────────────────────────────────────────────────────────

  pi.registerCommand("inter-agent-connect", {
    description:
      "Connect to the inter-agent bus (usage: /inter-agent-connect <name> [--label <label>])",
    handler: async (args, ctx) => {
      const parts = args.trim().split(/\s+/);
      const name = parts[0] || DEFAULT_NAME;
      const label = parts[1] || null;

      // Check if server is running
      const status = await execScript(scripts.pi, ["status", "--json"]);
      if (status.code !== 0) {
        notify("[inter-agent] connect failed", "server not reachable", "error");
        return;
      }

      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse(status.stdout);
      } catch {
        notify(
          "[inter-agent] connect failed",
          "invalid status response",
          "error",
        );
        return;
      }

      if (payload.state !== "available") {
        notify(
          "[inter-agent] connect failed",
          String(payload.message || "server unavailable"),
          "error",
        );
        return;
      }

      startListener(pi, ctx, config, name, label);
      notify(
        "[inter-agent] connected",
        `as ${name}${label ? ` (${label})` : ""}`,
      );
    },
  });

  pi.registerCommand("inter-agent-disconnect", {
    description: "Disconnect from the inter-agent bus",
    handler: async (_args, ctx) => {
      stopListener();
      const state = getConnectionState(ctx);
      if (state) {
        persistState(pi, { ...state, connected: false });
        updateStatus(ctx, { ...state, connected: false });
      }
      notify("[inter-agent] disconnected", "listener stopped");
    },
  });

  pi.registerCommand("inter-agent-send", {
    description: "Send a direct message (usage: /inter-agent-send <to> <text>)",
    handler: async (args, ctx) => {
      const match = args.trim().match(/^(\S+)\s+(.+)$/s);
      if (!match) {
        notify(
          "[inter-agent] send failed",
          "usage: /inter-agent-send <to> <text>",
          "error",
        );
        return;
      }
      const [, to, text] = match;
      const state = getConnectionState(ctx);
      const name = state?.name || DEFAULT_NAME;
      const formattedText = formatOutgoing(text, name);
      const result = await execScript(scripts.pi, ["send", to, formattedText]);
      if (result.code !== 0) {
        notify(
          "[inter-agent] send failed",
          truncate(result.stderr || result.stdout, 200),
          "error",
        );
        return;
      }
      notify("[inter-agent] sent", `to ${to}`);
      showOutgoingInContext(pi, name, text, `→ ${to}`);
    },
  });

  pi.registerCommand("inter-agent-broadcast", {
    description: "Broadcast a message (usage: /inter-agent-broadcast <text>)",
    handler: async (args, ctx) => {
      const text = args.trim();
      if (!text) {
        notify("[inter-agent] broadcast failed", "message required", "error");
        return;
      }
      const state = getConnectionState(ctx);
      const name = state?.name || DEFAULT_NAME;
      const formattedText = formatOutgoing(text, name);
      const result = await execScript(scripts.pi, ["broadcast", formattedText]);
      if (result.code !== 0) {
        notify(
          "[inter-agent] broadcast failed",
          truncate(result.stderr || result.stdout, 200),
          "error",
        );
        return;
      }
      notify("[inter-agent] broadcast", "sent");
      showOutgoingInContext(pi, name, text, "broadcast");
    },
  });

  pi.registerCommand("inter-agent-list", {
    description: "List connected agent sessions",
    handler: async (_args, _ctx) => {
      const result = await execScript(scripts.pi, ["list", "--json"]);
      if (result.code !== 0) {
        notify(
          "[inter-agent] list failed",
          truncate(result.stderr || result.stdout, 200),
          "error",
        );
        return;
      }
      try {
        const payload = JSON.parse(result.stdout);
        const sessions =
          (payload.sessions as Array<{
            name: string;
            label?: string | null;
          }>) || [];
        const lines = sessions.map(
          (s) => `• ${s.name}${s.label ? ` (${s.label})` : ""}`,
        );
        if (lines.length === 0) {
          notify("[inter-agent] list", "no agents connected");
        } else {
          notify("[inter-agent] list", lines.join(", "));
        }
      } catch {
        notify("[inter-agent] list failed", "invalid response", "error");
      }
    },
  });

  pi.registerCommand("inter-agent-status", {
    description: "Check inter-agent server status",
    handler: async (_args, _ctx) => {
      const result = await execScript(scripts.pi, ["status", "--json"]);
      if (result.code !== 0) {
        notify(
          "[inter-agent] status failed",
          truncate(result.stderr || result.stdout, 200),
          "error",
        );
        return;
      }
      try {
        const payload = JSON.parse(result.stdout);
        const state = String(payload.state || "unknown");
        const msg = String(payload.message || state);
        notify(
          "[inter-agent] status",
          msg,
          state === "available" ? "info" : "warning",
        );
      } catch {
        notify("[inter-agent] status failed", "invalid response", "error");
      }
    },
  });

  pi.registerCommand("inter-agent-shutdown", {
    description: "Shut down the inter-agent server",
    handler: async (_args, ctx) => {
      const result = await execScript(scripts.pi, ["shutdown"]);
      if (result.code !== 0) {
        notify(
          "[inter-agent] shutdown failed",
          truncate(result.stderr || result.stdout, 200),
          "error",
        );
        return;
      }
      stopListener();
      const state = getConnectionState(ctx);
      if (state) {
        persistState(pi, { ...state, connected: false });
        updateStatus(ctx, { ...state, connected: false });
      }
      notify("[inter-agent] shutdown", "server stopped");
    },
  });

  // ── Tools ─────────────────────────────────────────────────────────────────

  pi.registerTool({
    name: "inter_agent_send",
    label: "Send inter-agent message",
    description:
      "Send a direct message to another agent on the inter-agent bus",
    parameters: Type.Object({
      to: Type.String({ description: "Target agent routing name" }),
      text: Type.String({ description: "Message text" }),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const { to, text } = params as { to: string; text: string };
      const state = getConnectionState(ctx);
      const name = state?.name || DEFAULT_NAME;
      const formattedText = formatOutgoing(text, name);
      const result = await execScript(scripts.pi, ["send", to, formattedText]);
      if (result.code !== 0) {
        throw new Error(`Send failed: ${result.stderr || result.stdout}`);
      }
      showOutgoingInContext(pi, name, text, `→ ${to}`);
      return {
        content: [{ type: "text" as const, text: `Message sent to ${to}` }],
        details: { to, text },
      };
    },
  });

  pi.registerTool({
    name: "inter_agent_broadcast",
    label: "Broadcast inter-agent message",
    description: "Broadcast a message to all agents on the inter-agent bus",
    parameters: Type.Object({
      text: Type.String({ description: "Message text" }),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const { text } = params as { text: string };
      const state = getConnectionState(ctx);
      const name = state?.name || DEFAULT_NAME;
      const formattedText = formatOutgoing(text, name);
      const result = await execScript(scripts.pi, ["broadcast", formattedText]);
      if (result.code !== 0) {
        throw new Error(`Broadcast failed: ${result.stderr || result.stdout}`);
      }
      showOutgoingInContext(pi, name, text, "broadcast");
      return {
        content: [{ type: "text" as const, text: "Broadcast sent" }],
        details: { text },
      };
    },
  });

  pi.registerTool({
    name: "inter_agent_list",
    label: "List inter-agent sessions",
    description: "List all connected agent sessions on the inter-agent bus",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, _signal, _onUpdate, _ctx) {
      const result = await execScript(scripts.pi, ["list", "--json"]);
      if (result.code !== 0) {
        throw new Error(`List failed: ${result.stderr || result.stdout}`);
      }
      try {
        const payload = JSON.parse(result.stdout);
        const sessions =
          (payload.sessions as Array<{
            name: string;
            label?: string | null;
          }>) || [];
        const lines = sessions.map(
          (s) => `• ${s.name}${s.label ? ` (${s.label})` : ""}`,
        );
        return {
          content: [
            {
              type: "text" as const,
              text: lines.join("\n") || "No agents connected",
            },
          ],
          details: { sessions },
        };
      } catch {
        throw new Error("Invalid list response");
      }
    },
  });

  pi.registerTool({
    name: "inter_agent_status",
    label: "Inter-agent server status",
    description: "Check the status of the inter-agent server",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, _signal, _onUpdate, _ctx) {
      const result = await execScript(scripts.pi, ["status", "--json"]);
      if (result.code !== 0) {
        throw new Error(
          `Status check failed: ${result.stderr || result.stdout}`,
        );
      }
      try {
        const payload = JSON.parse(result.stdout);
        const text = `State: ${payload.state}\nMessage: ${payload.message}\nReachable: ${payload.server_reachable}`;
        return {
          content: [{ type: "text" as const, text }],
          details: payload,
        };
      } catch {
        throw new Error("Invalid status response");
      }
    },
  });
}
