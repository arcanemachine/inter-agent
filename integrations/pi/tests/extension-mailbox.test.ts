import { test } from "node:test";
import assert from "node:assert/strict";
import EventEmitter from "node:events";
import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import ext, { _setSpawnForTest } from "../src/index.js";

// ── Fake Pi runtime ─────────────────────────────────────────────────────────

type Handler = (...args: unknown[]) => unknown;

interface RecordedMessage {
  message: { customType: string; content: string; details: unknown };
  options: { triggerTurn?: boolean; deliverAs?: string };
}

interface BranchEntry {
  type: string;
  customType: string;
  data: unknown;
}

/** Minimal stand-in for a Pi ChildProcess driven by the test. */
class FakeChildProcess extends EventEmitter {
  readonly stdout = new EventEmitter();
  readonly stderr = new EventEmitter();
  pid = 12345;
  exitCode: number | null = null;
  signalCode: NodeJS.Signals | null = null;
  // The extension sets this to mark an expected (disconnect) stop.
  [key: string]: unknown;

  emitStdout(line: string): void {
    this.stdout.emit("data", Buffer.from(line));
  }

  emitStderr(line: string): void {
    this.stderr.emit("data", Buffer.from(line));
  }

  kill(signal: NodeJS.Signals = "SIGTERM"): boolean {
    if (this.exitCode !== null || this.signalCode !== null) return false;
    this.signalCode = signal;
    this.emit("exit", null, signal);
    this.emit("close", null, signal);
    return true;
  }

  /** Mark a clean exit (for status/exec scripts). */
  exit(code: number): void {
    this.exitCode = code;
    this.emit("exit", code, null);
    this.emit("close", code, null);
  }

  unref(): void {
    // No-op for the fake.
  }
}

class FakeCtx {
  readonly sessionManager: { getBranch(): BranchEntry[] };
  readonly ui: {
    notify: (m: string, t?: string) => void;
    setStatus: (k: string, t: string | undefined) => void;
  };
  cwd: string;
  idle = true;
  pendingMessages = false;

  constructor(
    branch: BranchEntry[],
    notifyLog: { message: string; type: string }[],
  ) {
    this.sessionManager = {
      getBranch: () => branch,
    };
    this.ui = {
      notify: (message, type = "info") => notifyLog.push({ message, type }),
      setStatus: () => {},
    };
    this.cwd = process.cwd();
  }

  isIdle(): boolean {
    return this.idle;
  }

  hasPendingMessages(): boolean {
    return this.pendingMessages;
  }
}

class FakePi {
  readonly commands = new Map<
    string,
    { handler: Handler; description?: string }
  >();
  readonly tools = new Map<string, { execute: Handler }>();
  readonly renderers = new Map<string, unknown>();
  readonly flags = new Map<string, unknown>();
  readonly handlers = new Map<string, Handler[]>();
  readonly messages: RecordedMessage[] = [];
  readonly branch: BranchEntry[] = [];
  readonly notifyLog: { message: string; type: string }[] = [];
  readonly ctx: FakeCtx;
  #flagValue: unknown = undefined;

  constructor() {
    this.ctx = new FakeCtx(this.branch, this.notifyLog);
  }

  on(event: string, handler: Handler): void {
    const list = this.handlers.get(event) ?? [];
    list.push(handler);
    this.handlers.set(event, list);
  }

  registerCommand(
    name: string,
    options: { handler: Handler; description?: string },
  ): void {
    this.commands.set(name, {
      handler: options.handler,
      description: options.description,
    });
  }

  registerTool(tool: { name: string; execute: Handler }): void {
    this.tools.set(tool.name, tool);
  }

  registerMessageRenderer(customType: string, renderer: unknown): void {
    this.renderers.set(customType, renderer);
  }

  registerFlag(name: string, options: unknown): void {
    this.flags.set(name, options);
  }

  getFlag(_name: string): unknown {
    return this.#flagValue;
  }

  setFlagValue(value: unknown): void {
    this.#flagValue = value;
  }

  sendMessage(
    message: { customType: string; content: string; details: unknown },
    options: { triggerTurn?: boolean; deliverAs?: string },
  ): void {
    this.messages.push({ message, options });
  }

  appendEntry(customType: string, data: unknown): void {
    this.branch.push({ type: "custom", customType, data });
  }
}

// ── Environment + spawn fakes ───────────────────────────────────────────────

function tick(ms = 0): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setupEnv(opts: {
  global?: Record<string, unknown>;
  project?: Record<string, unknown>;
}): { pi: FakePi; home: string; cwd: string } {
  const home = mkdtempSync(join(tmpdir(), "ia-home-"));
  const cwd = mkdtempSync(join(tmpdir(), "ia-cwd-"));
  mkdirSync(join(cwd, ".venv", "bin"), { recursive: true });
  for (const name of [
    "inter-agent-pi",
    "inter-agent-connect",
    "inter-agent-server",
  ]) {
    writeFileSync(join(cwd, ".venv", "bin", name), "#!/bin/sh\nexit 0\n");
    chmodSync(join(cwd, ".venv", "bin", name), 0o755);
  }
  mkdirSync(join(home, ".pi", "agent"), { recursive: true });
  if (opts.global) {
    writeFileSync(
      join(home, ".pi", "agent", "settings.json"),
      JSON.stringify({ interAgent: opts.global }),
    );
  }
  // Project settings always anchor getScripts at the temp .venv/bin stubs so
  // the faked connect/status flow resolves without a real inter-agent install.
  mkdirSync(join(cwd, ".pi"), { recursive: true });
  writeFileSync(
    join(cwd, ".pi", "settings.json"),
    JSON.stringify({
      interAgent: { ...(opts.project ?? {}), projectPath: cwd },
    }),
  );
  return { pi: new FakePi(), home, cwd };
}

function withEnv(
  opts: { global?: Record<string, unknown>; project?: Record<string, unknown> },
  fn: (api: { pi: FakePi; listeners: FakeChildProcess[] }) => Promise<void>,
): Promise<void> {
  return (async () => {
    const env = setupEnv(opts);
    const oldHome = process.env.HOME;
    const oldCwd = process.cwd();
    process.env.HOME = env.home;
    process.chdir(env.cwd);
    // spawn is fully faked; getScripts resolves the project .venv/bin stubs so
    // the connect/status flow proceeds without a real inter-agent install.
    const listeners: FakeChildProcess[] = [];
    _setSpawnForTest(((
      _cmd: string,
      args: string[],
      _options: unknown,
    ): FakeChildProcess => {
      if (args[0] === "status") {
        const proc = new FakeChildProcess();
        queueMicrotask(() => {
          proc.emitStdout(
            JSON.stringify({
              state: "available",
              message: "available",
              server_reachable: true,
            }) + "\n",
          );
          proc.exit(0);
        });
        return proc;
      }
      if (args[0] === "connect") {
        const proc = new FakeChildProcess();
        listeners.push(proc);
        return proc;
      }
      const proc = new FakeChildProcess();
      queueMicrotask(() => proc.exit(0));
      return proc;
    }) as never);

    try {
      ext(env.pi as never);
      // Establish session context (no flag, no saved state) so currentCtx is
      // bound before commands run.
      await runHandler(env.pi, "session_start", {}, env.pi.ctx);
      await fn({ pi: env.pi, listeners });
    } finally {
      await runHandler(env.pi, "session_shutdown");
      process.env.HOME = oldHome;
      _setSpawnForTest(null);
      process.chdir(oldCwd);
      rmSync(env.home, { recursive: true, force: true });
      rmSync(env.cwd, { recursive: true, force: true });
    }
  })();
}

async function runHandler(
  pi: FakePi,
  event: string,
  ...args: unknown[]
): Promise<void> {
  const list = pi.handlers.get(event);
  if (!list) return;
  for (const handler of list) {
    await handler(...args);
  }
}

function interAgentCommand(pi: FakePi): { handler: Handler } {
  const cmd = pi.commands.get("inter-agent");
  if (!cmd) throw new Error("inter-agent command not registered");
  return cmd;
}

function readTool(pi: FakePi): { execute: Handler } {
  const tool = pi.tools.get("inter_agent_read_messages");
  if (!tool) throw new Error("inter_agent_read_messages tool not registered");
  return tool;
}

const MARKER = "SECRET-MARKER-extension-body";

/** Emit a welcome then a queued direct msg frame on the current listener. */
function emitDirectMsg(
  listener: FakeChildProcess,
  name: string,
  body = MARKER,
): void {
  listener.emitStdout(JSON.stringify({ op: "welcome" }) + "\n");
  listener.emitStdout(
    JSON.stringify({
      op: "msg",
      msg_id: "m1",
      from_name: "alice",
      text: body,
      to: name,
    }) + "\n",
  );
}

// ── Tests ───────────────────────────────────────────────────────────────────

test("invalid config keys warn exactly once after UI context is available", async () => {
  await withEnv(
    {
      global: { deliveryMode: "bogus", mailboxNoticeDebounceMs: 99999 },
    },
    async ({ pi }) => {
      // First session_start fires both warnings once.
      await runHandler(pi, "session_start", {}, pi.ctx);
      const modeWarnings = pi.notifyLog.filter((n) =>
        n.message.includes("interAgent.deliveryMode"),
      );
      const debounceWarnings = pi.notifyLog.filter((n) =>
        n.message.includes("interAgent.mailboxNoticeDebounceMs"),
      );
      assert.equal(modeWarnings.length, 1);
      assert.equal(debounceWarnings.length, 1);

      // A second session_start must not repeat them.
      const before = pi.notifyLog.length;
      await runHandler(pi, "session_start", {}, pi.ctx);
      const newMode = pi.notifyLog
        .slice(before)
        .filter((n) => n.message.includes("interAgent.deliveryMode"));
      const newDebounce = pi.notifyLog
        .slice(before)
        .filter((n) =>
          n.message.includes("interAgent.mailboxNoticeDebounceMs"),
        );
      assert.equal(newMode.length, 0);
      assert.equal(newDebounce.length, 0);
    },
  );
});

test("delivery command overrides the session mode for future arrivals only", async () => {
  await withEnv(
    { project: { projectPath: process.cwd(), deliveryMode: "queued" } },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler(`connect rx`, pi.ctx);
      const listener = listeners[listeners.length - 1];
      // Default queued: body is hidden behind a metadata-only mailbox notice.
      emitDirectMsg(listener, "rx");
      await tick();
      assert.ok(
        pi.messages.some((m) => m.message.customType === "inter-agent-mailbox"),
      );
      assert.ok(
        !pi.messages.some(
          (m) => m.message.customType === "inter-agent-message",
        ),
      );
      const queuedNotice = pi.messages.find(
        (m) => m.message.customType === "inter-agent-mailbox",
      );
      assert.ok(queuedNotice);
      assert.ok(
        !JSON.stringify(queuedNotice!.message.details).includes(MARKER),
      );

      // Switch to immediate for future arrivals only; the queued body stays unread.
      await cmd.handler("delivery immediate", pi.ctx);
      const overrideNotify = pi.notifyLog
        .slice()
        .reverse()
        .find((n) =>
          n.message.includes("future arrivals will be delivered immediately"),
        );
      assert.ok(overrideNotify, "immediate override notify not shown");
      assert.ok(
        overrideNotify!.message.includes("unread message(s) already queued"),
      );

      // Read the previously queued body via the read tool to prove it was retained.
      const result = (await readTool(pi).execute(
        "c",
        {},
        undefined,
        undefined,
        pi.ctx,
      )) as {
        details: { read: { body: string }[] };
      };
      assert.equal(result.details.read.length, 1);
      assert.equal(result.details.read[0].body, MARKER);
    },
  );
});

test("project settings override global settings for delivery mode precedence", async () => {
  // Global says immediate; project overrides to queued. Project wins.
  await withEnv(
    {
      global: { deliveryMode: "immediate" },
      project: { projectPath: process.cwd(), deliveryMode: "queued" },
    },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      emitDirectMsg(listeners[listeners.length - 1], "rx");
      await tick();
      assert.ok(
        pi.messages.some((m) => m.message.customType === "inter-agent-mailbox"),
      );
      assert.ok(
        !pi.messages.some(
          (m) => m.message.customType === "inter-agent-message",
        ),
      );
    },
  );

  // With no project override, global immediate wins.
  await withEnv(
    {
      global: { deliveryMode: "immediate" },
      project: { projectPath: process.cwd() },
    },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      emitDirectMsg(listeners[listeners.length - 1], "rx");
      await tick();
      assert.ok(
        pi.messages.some((m) => m.message.customType === "inter-agent-message"),
      );
      // Immediate delivery never enters the mailbox.
      const read = (await readTool(pi).execute(
        "c",
        {},
        undefined,
        undefined,
        pi.ctx,
      )) as {
        details: { read: unknown[] };
      };
      assert.equal(read.details.read.length, 0);
    },
  );
});

test("queued user notification is metadata-only while immediate shows the bounded body", async () => {
  // Immediate mode: the user notification carries the bounded body, matching the
  // original behavior; queued mode notifies metadata only.
  await withEnv(
    {
      global: { deliveryMode: "immediate" },
      project: { projectPath: process.cwd() },
    },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      emitDirectMsg(listeners[listeners.length - 1], "rx");
      await tick();
      const immediateNotify = pi.notifyLog.find((n) =>
        n.message.includes("[inter-agent] alice"),
      );
      assert.ok(immediateNotify, "immediate inbound notify not shown");
      assert.ok(immediateNotify!.message.includes(MARKER));
    },
  );

  await withEnv(
    { project: { projectPath: process.cwd(), deliveryMode: "queued" } },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      emitDirectMsg(listeners[listeners.length - 1], "rx");
      await tick();
      const queuedNotify = pi.notifyLog.find((n) =>
        n.message.includes("[inter-agent] alice"),
      );
      assert.ok(queuedNotify, "queued inbound notify not shown");
      assert.ok(!queuedNotify!.message.includes(MARKER));
      assert.ok(queuedNotify!.message.includes("queued in mailbox"));
    },
  );
});

test("listener disconnect and reconnect preserve unread mailbox state", async () => {
  await withEnv(
    { project: { projectPath: process.cwd(), deliveryMode: "queued" } },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      const listener1 = listeners[listeners.length - 1];
      emitDirectMsg(listener1, "rx");
      await tick();

      // Disconnect, then reconnect within the same extension runtime.
      await cmd.handler("disconnect", pi.ctx);
      await cmd.handler("connect rx", pi.ctx);
      const listener2 = listeners[listeners.length - 1];
      listener2.emitStdout(JSON.stringify({ op: "welcome" }) + "\n");
      await tick();

      // The mailbox was not cleared by stop/start: m1 remains unread until the
      // explicit read tool consumes it after reconnect.
      const read = (await readTool(pi).execute(
        "c",
        {},
        undefined,
        undefined,
        pi.ctx,
      )) as {
        details: { read: { id: string; body: string }[] };
      };
      assert.equal(read.details.read.length, 1);
      assert.equal(read.details.read[0].id, "m1");
      assert.equal(read.details.read[0].body, MARKER);
    },
  );
});

test("malformed frame followed by a valid frame both handle correctly", async () => {
  await withEnv(
    { project: { projectPath: process.cwd(), deliveryMode: "queued" } },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      const listener = listeners[listeners.length - 1];
      listener.emitStdout(JSON.stringify({ op: "welcome" }) + "\n");
      // A malformed frame (no msg_id) then a valid frame in the same chunk.
      listener.emitStdout(
        Buffer.concat([
          Buffer.from(
            JSON.stringify({ op: "msg", from_name: "x", text: "bad" }) + "\n",
          ),
          Buffer.from(
            JSON.stringify({
              op: "msg",
              msg_id: "good",
              from_name: "alice",
              text: MARKER,
            }) + "\n",
          ),
        ]).toString(),
      );
      await tick();

      const droppedNotify = pi.notifyLog.find((n) =>
        n.message.includes("without a valid msg_id"),
      );
      assert.ok(droppedNotify, "malformed frame did not warn");
      const read = (await readTool(pi).execute(
        "c",
        {},
        undefined,
        undefined,
        pi.ctx,
      )) as {
        details: { read: { id: string }[] };
      };
      assert.equal(read.details.read.length, 1);
      assert.equal(read.details.read[0].id, "good");
    },
  );
});

test("pending settlement before shutdown never flushes", async () => {
  await withEnv(
    { project: { projectPath: process.cwd(), deliveryMode: "queued" } },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      const listener = listeners[listeners.length - 1];
      listener.emitStdout(JSON.stringify({ op: "welcome" }) + "\n");
      // Hold a notice pending while active, then shut down before terminal
      // settlement can flush it.
      pi.ctx.idle = false;
      pi.ctx.pendingMessages = true;
      listener.emitStdout(
        JSON.stringify({
          op: "msg",
          msg_id: "m1",
          from_name: "alice",
          text: MARKER,
        }) + "\n",
      );
      await tick();
      await runHandler(pi, "agent_settled");
      // session_shutdown (in finally) runs after this; flush must not happen.
      await runHandler(pi, "session_shutdown");
      await tick(50);
      assert.ok(
        !pi.messages.some(
          (m) => m.message.customType === "inter-agent-mailbox",
        ),
      );
    },
  );
});

test("agent_settled flushes a pending queued notice at most once", async () => {
  await withEnv(
    { project: { projectPath: process.cwd(), deliveryMode: "queued" } },
    async ({ pi, listeners }) => {
      const cmd = interAgentCommand(pi);
      await cmd.handler("connect rx", pi.ctx);
      const listener = listeners[listeners.length - 1];
      listener.emitStdout(JSON.stringify({ op: "welcome" }) + "\n");
      // Hold a notice pending while the agent is active.
      pi.ctx.idle = false;
      pi.ctx.pendingMessages = true;
      listener.emitStdout(
        JSON.stringify({
          op: "msg",
          msg_id: "m1",
          from_name: "alice",
          text: MARKER,
        }) + "\n",
      );
      await tick();
      assert.ok(
        !pi.messages.some(
          (m) => m.message.customType === "inter-agent-mailbox",
        ),
      );

      // Once fully settled, the handler flushes exactly one notice.
      pi.ctx.idle = true;
      pi.ctx.pendingMessages = false;
      await runHandler(pi, "agent_settled");
      await tick();
      const notices = pi.messages.filter(
        (m) => m.message.customType === "inter-agent-mailbox",
      );
      assert.equal(notices.length, 1);
      assert.ok(!JSON.stringify(notices[0].message.details).includes(MARKER));
      assert.equal(notices[0].options.triggerTurn, true);
    },
  );
});
