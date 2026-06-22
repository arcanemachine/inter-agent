/**
 * pi-inter-agent
 * Pi extension for connecting to the inter-agent message bus
 *
 * Provides commands and tools to send, broadcast, list sessions, check status,
 * inspect local identity, and receive incoming messages as Pi notifications.
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
import type { AutocompleteItem } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";
import { spawn, ChildProcess } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, resolve } from "node:path";

// ── Configuration ───────────────────────────────────────────────────────────

interface InterAgentConfig {
  projectPath?: string;
  host?: string;
  port?: number | string;
  dataDir?: string;
}

interface Settings {
  interAgent?: InterAgentConfig;
}

const DEFAULT_PROJECT_PATH = join(homedir(), ".local", "share", "inter-agent");

function expandHome(path: string): string {
  if (path === "~") return homedir();
  if (path.startsWith("~/")) return join(homedir(), path.slice(2));
  return path;
}

function resolvePathOption(path: string | undefined, baseDir: string) {
  if (!path) return path;
  const expanded = expandHome(path);
  return isAbsolute(expanded) ? expanded : resolve(baseDir, expanded);
}

function resolveConfigPaths(
  config: InterAgentConfig,
  settingsPath: string,
): InterAgentConfig {
  const baseDir = dirname(settingsPath);
  return {
    ...config,
    projectPath: resolvePathOption(config.projectPath, baseDir),
    dataDir: resolvePathOption(config.dataDir, baseDir),
  };
}

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
        config = {
          ...config,
          ...resolveConfigPaths(parsed.interAgent, globalSettingsPath),
        };
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
        config = {
          ...config,
          ...resolveConfigPaths(parsed.interAgent, projectSettingsPath),
        };
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
    server: join(binDir, "inter-agent-server"),
  };
}

type InterAgentScripts = ReturnType<typeof getScripts>;

function interAgentEnv(
  config: InterAgentConfig = loadConfig(),
): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, PYTHONUNBUFFERED: "1" };
  if (config.host) env.INTER_AGENT_HOST = String(config.host);
  if (config.port !== undefined && config.port !== null) {
    env.INTER_AGENT_PORT = String(config.port);
  }
  if (config.dataDir) env.INTER_AGENT_DATA_DIR = config.dataDir;
  return env;
}

// ── Constants ───────────────────────────────────────────────────────────────

const NOTIFY_MAX_LEN = 1000;
const DEFAULT_NAME = "pi";
const AUTO_STARTED_SERVER_IDLE_TIMEOUT_S = 300;
const SERVER_START_WAIT_ATTEMPTS = 30;
const SERVER_START_WAIT_MS = 500;

// ── State ───────────────────────────────────────────────────────────────────

interface ConnectionState {
  name: string;
  label: string | null;
  connected: boolean;
}

interface ScriptResult {
  stdout: string;
  stderr: string;
  code: number | null;
}

interface ListenerOptions {
  notifyOnReady?: boolean;
}

let listenerProc: ChildProcess | null = null;
let currentCtx: ExtensionContext | null = null;
let messageBuffer = "";
let listenerReady = false;
let currentConnection: ConnectionState | null = null;

// ── Helpers ─────────────────────────────────────────────────────────────────

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + " …";
}

const FROM_PREFIX_RE = /^\[from: ([^\]]+)\] ?/;

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
      ? `Reply directly to ${from} with inter_agent_send only if useful; ` +
        "do not broadcast unless the user explicitly asks you to message everyone."
      : `Reply with inter_agent_send to="${from}" only when coordination needs a response.`;
  pi.sendMessage(
    {
      customType: "inter-agent-message",
      content: `[inter-agent message from agent ${from} ${toInfo}]

This is a peer-agent message, not a user message. Do not describe it as coming from the user.

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
      content: `[inter-agent message sent by the current agent (${from}) ${toInfo}]

Record only. Do not respond to this sent-message confirmation.

${text}`,
      display: true,
      details: { from, text, toInfo, outgoing: true },
    },
    { triggerTurn: false, deliverAs: "steer" },
  );
}

function execScript(script: string, args: string[]): Promise<ScriptResult> {
  return new Promise((resolve) => {
    const env = interAgentEnv();
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
        stderr +=
          "inter-agent command was not found. Check that inter-agent is installed and configured, then try again.";
      } else {
        stderr += String(err);
      }
      resolve({ stdout, stderr, code: null });
    });
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function scriptFailureMessage(result: ScriptResult, operation: string): string {
  const output = (result.stderr || result.stdout).trim();
  if (result.code === null || output.includes("not found")) {
    return `inter-agent ${operation} command was not found. Check that inter-agent is installed and configured, then try again.`;
  }
  return truncate(output || `inter-agent ${operation} command failed`, 200);
}

async function readServerStatus(
  scripts: InterAgentScripts,
): Promise<
  | { ok: true; payload: Record<string, unknown> }
  | { ok: false; message: string }
> {
  const result = await execScript(scripts.pi, ["status", "--json"]);
  if (result.code !== 0) {
    return { ok: false, message: scriptFailureMessage(result, "status") };
  }

  try {
    const parsed: unknown = JSON.parse(result.stdout);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return { ok: true, payload: parsed as Record<string, unknown> };
    }
  } catch {
    // Fall through to the user-facing error below.
  }

  return {
    ok: false,
    message:
      "inter-agent status returned an invalid response. Try /inter-agent status; if this continues, check the inter-agent installation.",
  };
}

function statusState(payload: Record<string, unknown>): string {
  return typeof payload.state === "string" ? payload.state : "unknown";
}

function statusMessage(payload: Record<string, unknown>): string {
  return typeof payload.message === "string"
    ? payload.message
    : statusState(payload);
}

function shouldAutoStartServer(payload: Record<string, unknown>): boolean {
  return (
    statusState(payload) === "unavailable" && payload.identity_verified !== true
  );
}

function statusFailureGuidance(payload: Record<string, unknown>): string {
  const message = statusMessage(payload);
  switch (statusState(payload)) {
    case "identity_check_failed":
      return `${message}. Try restarting the inter-agent server, then run /inter-agent status if this continues.`;
    case "auth_failed":
      return `${message}. Try restarting the inter-agent server so clients share the same token.`;
    case "protocol_mismatch":
      return `${message}. Another process may be using the inter-agent port; try /inter-agent status or restart the server.`;
    case "unavailable":
      return `${message}. Try /inter-agent status, or start inter-agent-server manually.`;
    default:
      return message;
  }
}

function startServerProcess(
  scripts: InterAgentScripts,
): Promise<{ ok: true; pid?: number } | { ok: false; message: string }> {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (
      result: { ok: true; pid?: number } | { ok: false; message: string },
    ) => {
      if (!settled) {
        settled = true;
        resolve(result);
      }
    };

    const proc = spawn(
      scripts.server,
      ["--idle-timeout", String(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S)],
      {
        stdio: "ignore",
        shell: false,
        detached: true,
        env: interAgentEnv(loadConfig()),
      },
    );

    proc.once("spawn", () => {
      proc.unref();
      finish({ ok: true, pid: proc.pid });
    });

    proc.once("error", (err) => {
      const nodeErr = err as NodeJS.ErrnoException;
      if (nodeErr.code === "ENOENT") {
        finish({
          ok: false,
          message:
            "inter-agent server command was not found. Check that inter-agent is installed and configured, then try again.",
        });
      } else {
        finish({
          ok: false,
          message: `could not start inter-agent server: ${String(err)}`,
        });
      }
    });

    proc.once("exit", (code, signal) => {
      finish({
        ok: false,
        message: `inter-agent server exited before it was ready (code ${code ?? "none"}, signal ${signal ?? "none"}). Try /inter-agent status or start inter-agent-server manually.`,
      });
    });
  });
}

async function waitForServerAvailable(
  scripts: InterAgentScripts,
): Promise<{ ok: true } | { ok: false; message: string }> {
  let lastMessage = "server unavailable";
  for (let i = 0; i < SERVER_START_WAIT_ATTEMPTS; i++) {
    const status = await readServerStatus(scripts);
    if (status.ok === false) {
      lastMessage = status.message;
    } else if (statusState(status.payload) === "available") {
      return { ok: true };
    } else {
      lastMessage = statusFailureGuidance(status.payload);
    }
    await sleep(SERVER_START_WAIT_MS);
  }

  return {
    ok: false,
    message: `Started the inter-agent server, but it did not become available. ${lastMessage}`,
  };
}

async function ensureServerAvailable(
  scripts: InterAgentScripts,
): Promise<boolean> {
  const initial = await readServerStatus(scripts);
  if (initial.ok === false) {
    notify("[inter-agent] connect failed", initial.message, "error");
    return false;
  }

  if (statusState(initial.payload) === "available") {
    notify("[inter-agent] server detected", "connecting now");
    return true;
  }

  if (!shouldAutoStartServer(initial.payload)) {
    notify(
      "[inter-agent] connect failed",
      statusFailureGuidance(initial.payload),
      "error",
    );
    return false;
  }

  notify("[inter-agent] server not detected", "starting now");
  const started = await startServerProcess(scripts);
  if (started.ok === false) {
    notify("[inter-agent] connect failed", started.message, "error");
    return false;
  }

  const ready = await waitForServerAvailable(scripts);
  if (ready.ok === false) {
    notify("[inter-agent] connect failed", ready.message, "error");
    return false;
  }

  notify("[inter-agent] server ready", "connecting now");
  return true;
}

function splitCommandArgs(input: string): string[] {
  const matches = input.match(/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\S+/g) || [];
  return matches.map((part) => {
    if (
      (part.startsWith('"') && part.endsWith('"')) ||
      (part.startsWith("'") && part.endsWith("'"))
    ) {
      return part.slice(1, -1).replace(/\\(["'\\])/g, "$1");
    }
    return part;
  });
}

function parseConnectArgs(
  args: string,
):
  | { ok: true; name: string; label: string | null }
  | { ok: false; message: string } {
  const parts = splitCommandArgs(args.trim());
  let name = DEFAULT_NAME;
  let label: string | null = null;
  let index = 0;

  if (parts[0] && parts[0] !== "--label") {
    name = parts[0];
    index = 1;
  }

  while (index < parts.length) {
    const part = parts[index];
    if (part === "--label") {
      const value = parts[index + 1];
      if (!value) {
        return {
          ok: false,
          message: "usage: /inter-agent connect <name> [--label <label>]",
        };
      }
      label = value;
      index += 2;
      continue;
    }
    if (label === null) {
      label = part;
      index += 1;
      continue;
    }
    return {
      ok: false,
      message: "usage: /inter-agent connect <name> [--label <label>]",
    };
  }

  return { ok: true, name, label };
}

function parseRenameArgs(
  args: string,
):
  | { ok: true; name: string; label: string | null }
  | { ok: false; message: string } {
  const trimmed = args.trim();
  if (!trimmed) {
    return {
      ok: false,
      message: "usage: /inter-agent rename <name> [--label <label>]",
    };
  }
  const parsed = parseConnectArgs(trimmed);
  if (parsed.ok === false) return parsed;
  if (parsed.name === DEFAULT_NAME && trimmed.startsWith("--label")) {
    return {
      ok: false,
      message: "usage: /inter-agent rename <name> [--label <label>]",
    };
  }
  return parsed;
}

function formatConnectError(code: string, text: string): string {
  switch (code) {
    case "NAME_TAKEN":
      return `${code}: ${text}. Choose a different name, or disconnect the existing session and try again.`;
    case "BAD_NAME":
      return `${code}: ${text}. Use lowercase letters, numbers, and hyphens; start with a letter or number; max 40 characters.`;
    case "AUTH_FAILED":
      return `${code}: ${text}. Restart the inter-agent server and reconnect clients if tokens changed.`;
    case "TOO_MANY_CONNECTIONS":
      return `${code}: ${text}. Disconnect another session, then try again.`;
    default:
      return `${code}: ${text}`;
  }
}

// ── Listener Management ─────────────────────────────────────────────────────

function startListener(
  pi: ExtensionAPI,
  ctx: ExtensionContext,
  config: InterAgentConfig,
  name: string,
  label: string | null,
  options: ListenerOptions = {},
) {
  stopListener();

  const scripts = getScripts(config);
  const args = [name];
  if (label) args.push("--label", label);

  const proc = spawn(scripts.connect, args, {
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
    env: interAgentEnv(config),
  });

  listenerProc = proc;
  messageBuffer = "";
  listenerReady = false;
  currentConnection = null;

  proc.stdout?.on("data", (data: Buffer) => {
    messageBuffer += data.toString();
    const lines = messageBuffer.split("\n");
    messageBuffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.op === "welcome") {
          const state: ConnectionState = { name, label, connected: true };
          listenerReady = true;
          currentConnection = state;
          persistState(pi, state);
          updateStatus(ctx, state);
          if (options.notifyOnReady) {
            notify(
              "[inter-agent] connected",
              `as ${name}${label ? ` (${label})` : ""}`,
            );
          }
          continue;
        }
        if (msg.op === "error") {
          const code = String(msg.code || "unknown");
          const text = String(msg.message || "connection rejected");
          notify(
            `[inter-agent] connect failed`,
            formatConnectError(code, text),
            "error",
          );
          listenerReady = false;
          currentConnection = null;
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
          const toInfo = msg.to ? `to ${msg.to}` : "broadcast";
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
      const state = getConnectionState(ctx);
      const previousName = currentConnection?.name || state?.name || name;
      const wasConnected =
        listenerReady ||
        currentConnection !== null ||
        state?.connected === true;
      listenerProc = null;
      listenerReady = false;
      currentConnection = null;
      if (state) {
        persistState(pi, { ...state, connected: false });
        updateStatus(ctx, { ...state, connected: false });
      }
      if (code !== 0 && code !== null) {
        const reconnectHint = wasConnected
          ? `. Use /inter-agent connect ${previousName} to reconnect.`
          : "";
        notify(
          "[inter-agent] listener exited",
          `code ${code}${reconnectHint}`,
          "warning",
        );
      } else if (wasConnected) {
        notify(
          "[inter-agent] disconnected",
          `server connection closed. Use '/inter-agent connect ${previousName}' to reconnect.`,
          "warning",
        );
      }
    }
  });

  proc.on("error", (err) => {
    const nodeErr = err as NodeJS.ErrnoException;
    if (nodeErr.code === "ENOENT") {
      notify(
        "[inter-agent] listener error",
        "inter-agent connect command was not found. Check that inter-agent is installed and configured, then try again.",
        "error",
      );
    } else {
      notify("[inter-agent] listener error", String(err), "error");
    }
  });
}

function stopListener() {
  if (listenerProc) {
    listenerProc.kill("SIGTERM");
    listenerProc = null;
    messageBuffer = "";
    listenerReady = false;
    currentConnection = null;
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
      const ready = await ensureServerAvailable(scripts);
      if (!ready) {
        persistState(pi, { ...state, connected: false });
        updateStatus(ctx, { ...state, connected: false });
        return;
      }
      startListener(pi, ctx, config, state.name, state.label, {
        notifyOnReady: true,
      });
      notify("[inter-agent] reconnecting", `as ${state.name}`);
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
      "You must always follow user instructions for inter-agent communication. " +
      "Use inter_agent_send for targeted peer communication. " +
      "Inter-agent messages are from peer agents, not the user. Never describe them as user messages. " +
      "For peer messages, decide whether to reply yourself: send a concise reply, ask a clarifying question, say you need user input or approval, or skip replying when no coordination is needed. " +
      "Keep inter-agent communication purposeful and brief. Avoid idle chatter, social back-and-forth, and non-actionable replies. Send a peer message only when it helps complete user work, coordinate a task, clarify next steps, or close a communication loop. " +
      "Be strict about ending idle exchanges. If a peer message is not actionable for user work or coordination, do not reply. If a thread is not producing new task-relevant information or clear next steps, stop replying. Do not send courtesy replies, acknowledgments, or follow-ups just to be polite. " +
      "Use inter_agent_broadcast only when the user explicitly asks you to message everyone or a broadcast is truly required. " +
      "Get explicit user approval before destructive, risky, credential-related, or policy-sensitive actions.";
    return {
      systemPrompt: event.systemPrompt + instruction,
    };
  });

  // ── Commands ──────────────────────────────────────────────────────────────

  const INTER_AGENT_SUBCOMMANDS: AutocompleteItem[] = [
    { value: "connect", label: "connect", description: "Connect to the bus" },
    {
      value: "disconnect",
      label: "disconnect",
      description: "Disconnect from the bus",
    },
    {
      value: "rename",
      label: "rename",
      description: "Reconnect with a new name",
    },
    { value: "send", label: "send", description: "Send a direct message" },
    {
      value: "broadcast",
      label: "broadcast",
      description:
        "Broadcast only when messaging everyone is explicitly needed",
    },
    { value: "list", label: "list", description: "List connected sessions" },
    {
      value: "status",
      label: "status",
      description: "Check server status",
    },
  ];

  async function handleConnect(args: string, ctx: ExtensionContext) {
    const parsed = parseConnectArgs(args);
    if (parsed.ok === false) {
      notify("[inter-agent] connect failed", parsed.message, "error");
      return;
    }

    const ready = await ensureServerAvailable(scripts);
    if (!ready) return;

    startListener(pi, ctx, config, parsed.name, parsed.label, {
      notifyOnReady: true,
    });
    notify(
      "[inter-agent] connecting",
      `as ${parsed.name}${parsed.label ? ` (${parsed.label})` : ""}`,
    );
  }

  async function handleDisconnect(_args: string, ctx: ExtensionContext) {
    stopListener();
    const state = getConnectionState(ctx);
    if (state) {
      persistState(pi, { ...state, connected: false });
      updateStatus(ctx, { ...state, connected: false });
    }
    notify("[inter-agent] disconnected", "listener stopped");
  }

  async function handleRename(args: string, ctx: ExtensionContext) {
    if (!listenerReady || !currentConnection) {
      notify(
        "[inter-agent] rename failed",
        "Not connected to the inter-agent bus. Use /inter-agent connect first.",
        "error",
      );
      return;
    }
    const parsed = parseRenameArgs(args);
    if (parsed.ok === false) {
      notify("[inter-agent] rename failed", parsed.message, "error");
      return;
    }

    const oldName = currentConnection.name;
    const label = parsed.label ?? currentConnection.label;
    const ready = await ensureServerAvailable(scripts);
    if (!ready) return;

    startListener(pi, ctx, config, parsed.name, label, { notifyOnReady: true });
    notify(
      "[inter-agent] renaming",
      `${oldName} -> ${parsed.name}${label ? ` (${label})` : ""}`,
    );
  }

  async function handleSend(args: string, _ctx: ExtensionContext) {
    const match = args.trim().match(/^(\S+)\s+(.+)$/s);
    if (!match) {
      notify(
        "[inter-agent] send failed",
        "usage: /inter-agent send <to> <text>",
        "error",
      );
      return;
    }
    const [, to, text] = match;
    if (!listenerReady || !currentConnection) {
      notify(
        "[inter-agent] send failed",
        "Not connected to the inter-agent bus. Use /inter-agent connect first.",
        "error",
      );
      return;
    }
    const name = currentConnection.name;
    const result = await execScript(scripts.pi, [
      "send",
      to,
      text,
      "--from",
      name,
    ]);
    if (result.code !== 0) {
      notify(
        "[inter-agent] send failed",
        scriptFailureMessage(result, "send"),
        "error",
      );
      return;
    }
    notify("[inter-agent] sent", `to ${to}`);
    showOutgoingInContext(pi, name, text, `to ${to}`);
  }

  async function handleBroadcast(args: string, _ctx: ExtensionContext) {
    const text = args.trim();
    if (!text) {
      notify("[inter-agent] broadcast failed", "message required", "error");
      return;
    }
    if (!listenerReady || !currentConnection) {
      notify(
        "[inter-agent] broadcast failed",
        "Not connected to the inter-agent bus. Use /inter-agent connect first.",
        "error",
      );
      return;
    }
    const name = currentConnection.name;
    const result = await execScript(scripts.pi, [
      "broadcast",
      text,
      "--from",
      name,
    ]);
    if (result.code !== 0) {
      notify(
        "[inter-agent] broadcast failed",
        scriptFailureMessage(result, "broadcast"),
        "error",
      );
      return;
    }
    notify("[inter-agent] broadcast", "sent");
    showOutgoingInContext(pi, name, text, "broadcast");
  }

  async function handleList(_args: string, _ctx: ExtensionContext) {
    const result = await execScript(scripts.pi, ["list", "--json"]);
    if (result.code !== 0) {
      notify(
        "[inter-agent] list failed",
        scriptFailureMessage(result, "list"),
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
  }

  async function handleStatus(_args: string, _ctx: ExtensionContext) {
    const result = await execScript(scripts.pi, ["status", "--json"]);
    if (result.code !== 0) {
      notify(
        "[inter-agent] status failed",
        scriptFailureMessage(result, "status"),
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
  }

  function showInterAgentUsage() {
    notify(
      "[inter-agent] usage",
      "usage: /inter-agent <connect|disconnect|rename|send|broadcast|list|status> [args]",
      "warning",
    );
  }

  pi.registerCommand("inter-agent", {
    description: "Inter-agent bus commands",
    getArgumentCompletions: (prefix: string): AutocompleteItem[] | null => {
      const filtered = INTER_AGENT_SUBCOMMANDS.filter((s) =>
        s.value.startsWith(prefix),
      );
      return filtered.length > 0 ? filtered : null;
    },
    handler: async (args, ctx) => {
      const trimmed = args.trim();
      if (!trimmed) {
        showInterAgentUsage();
        return;
      }
      const subcommand = trimmed.split(/\s+/, 1)[0];
      const rest = trimmed.slice(subcommand.length).trimStart();
      switch (subcommand) {
        case "connect":
          await handleConnect(rest, ctx);
          break;
        case "disconnect":
          await handleDisconnect(rest, ctx);
          break;
        case "rename":
          await handleRename(rest, ctx);
          break;
        case "send":
          await handleSend(rest, ctx);
          break;
        case "broadcast":
          await handleBroadcast(rest, ctx);
          break;
        case "list":
          await handleList(rest, ctx);
          break;
        case "status":
          await handleStatus(rest, ctx);
          break;
        default:
          showInterAgentUsage();
      }
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
      if (!listenerReady || !currentConnection) {
        throw new Error(
          "Not connected to the inter-agent bus. Use /inter-agent connect first.",
        );
      }
      const name = currentConnection.name;
      const result = await execScript(scripts.pi, [
        "send",
        to,
        text,
        "--from",
        name,
      ]);
      if (result.code !== 0) {
        throw new Error(`Send failed: ${scriptFailureMessage(result, "send")}`);
      }
      showOutgoingInContext(pi, name, text, `to ${to}`);
      return {
        content: [
          {
            type: "text" as const,
            text: `Message sent from the current agent to ${to}`,
          },
        ],
        details: { to, text },
      };
    },
  });

  pi.registerTool({
    name: "inter_agent_broadcast",
    label: "Broadcast inter-agent message",
    description:
      "Broadcast to all agents only when the user explicitly asks to message " +
      "everyone; prefer inter_agent_send for replies.",
    parameters: Type.Object({
      text: Type.String({ description: "Message text for all agents" }),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const { text } = params as { text: string };
      if (!listenerReady || !currentConnection) {
        throw new Error(
          "Not connected to the inter-agent bus. Use /inter-agent connect first.",
        );
      }
      const name = currentConnection.name;
      const result = await execScript(scripts.pi, [
        "broadcast",
        text,
        "--from",
        name,
      ]);
      if (result.code !== 0) {
        throw new Error(
          `Broadcast failed: ${scriptFailureMessage(result, "broadcast")}`,
        );
      }
      showOutgoingInContext(pi, name, text, "broadcast");
      return {
        content: [
          { type: "text" as const, text: "Broadcast sent to all other agents" },
        ],
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
        throw new Error(`List failed: ${scriptFailureMessage(result, "list")}`);
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
    name: "inter_agent_whoami",
    label: "Inter-agent local identity",
    description:
      "Report this Pi session's local inter-agent connection identity",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
      const state = getConnectionState(ctx);
      const listenerRunning = listenerProc !== null;
      const connected =
        listenerReady && listenerRunning && currentConnection !== null;
      const name = connected ? currentConnection.name : null;
      const label = connected ? currentConnection.label : null;
      const lines = connected
        ? [
            "Connected: true",
            `Name: ${name}`,
            ...(label ? [`Label: ${label}`] : []),
          ]
        : [
            "Connected: false",
            ...(state?.name ? [`Last name: ${state.name}`] : []),
          ];
      return {
        content: [{ type: "text" as const, text: lines.join("\n") }],
        details: {
          connected,
          name,
          label,
          listener_running: listenerRunning,
          saved_name: state?.name ?? null,
          saved_connected: state?.connected ?? false,
        },
      };
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
          `Status check failed: ${scriptFailureMessage(result, "status")}`,
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
