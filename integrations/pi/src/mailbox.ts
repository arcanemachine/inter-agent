/**
 * Bounded in-memory queued mailbox and delivery dispatcher for the Pi
 * inter-agent extension.
 *
 * Queued message bodies live only in this module's in-memory state for the
 * current Pi extension runtime. Notices and read-tool results are built here so
 * the behavior is unit-testable without a live Pi process. Metadata-only
 * notices never contain bodies; bodies surface only through an explicit read
 * or immediate-mode delivery.
 */

export type DeliveryMode = "queued" | "immediate";

export type MessageKind = "direct" | "broadcast" | "channel";

export const MAILBOX_MAX_UNREAD = 128;
export const MAILBOX_NOTICE_DEBOUNCE_MS_DEFAULT = 0;
export const MAILBOX_NOTICE_DEBOUNCE_MS_MAX = 5000;

/** True for a valid configured `deliveryMode`. */
export function isValidDeliveryMode(value: unknown): value is DeliveryMode {
  return value === "queued" || value === "immediate";
}

/** Resolve the effective delivery mode, falling back to queued. */
export function effectiveDeliveryMode(value: string | undefined): DeliveryMode {
  return value === "immediate" ? "immediate" : "queued";
}

/** True for a valid integer debounce value within the configured bounds. */
export function isValidDebounceMs(value: unknown): boolean {
  return (
    typeof value === "number" &&
    Number.isInteger(value) &&
    value >= 0 &&
    value <= MAILBOX_NOTICE_DEBOUNCE_MS_MAX
  );
}

/** Resolve the effective debounce, falling back to the default. */
export function effectiveDebounceMs(value: unknown): number {
  return isValidDebounceMs(value)
    ? (value as number)
    : MAILBOX_NOTICE_DEBOUNCE_MS_DEFAULT;
}

export interface MailboxMessage {
  msgId: string;
  sender: string;
  body: string;
  kind: MessageKind;
  channel?: string;
  target?: string;
  /** Monotonic arrival sequence for stable read/eviction order. */
  arrival: number;
}

export interface MailboxSnapshotEntry {
  id: string;
  sender: string;
  kind: MessageKind;
  channel?: string;
  target?: string;
}

export interface SenderGroup {
  sender: string;
  count: number;
}

export interface MailboxSnapshot {
  unread: number;
  messages: MailboxSnapshotEntry[];
  bySender: SenderGroup[];
}

export interface MailboxReadResult {
  read: MailboxMessage[];
  missing: string[];
  remaining: number;
}

export type InboundAddOutcome =
  | { status: "added"; duplicate: boolean; evicted: boolean }
  | { status: "duplicate" }
  | { status: "malformed" };

/** Immediate-mode custom message payload for an inbound body. */
export interface InboundImmediateMessage {
  customType: "inter-agent-message";
  content: string;
  display: true;
  details: {
    from: string;
    text: string;
    toInfo: string;
    displayContent: string;
  };
}

/** Metadata-only mailbox notice payload. */
export interface MailboxNoticeMessage {
  customType: "inter-agent-mailbox";
  content: string;
  display: true;
  details: MailboxSnapshot;
}

export interface MailboxHost {
  /** True when the agent is idle (not streaming). */
  isIdle(): boolean;
  /** True when queued continuation messages are still waiting to run. */
  hasPendingMessages(): boolean;
  /** Deliver a metadata-only mailbox notice as follow-up context. */
  sendNotice(message: MailboxNoticeMessage, triggerTurn: boolean): void;
  /** Deliver an immediate body as follow-up context. */
  sendImmediate(message: InboundImmediateMessage, triggerTurn: boolean): void;
  /** Show a bounded, metadata-only warning to the user. */
  notifyWarning(body: string): void;
  /** Schedule `fn` after `ms` and return a cancel function. */
  schedule(fn: () => void, ms: number): () => void;
}

export interface InboundDispatch {
  msgId: string;
  sender: string;
  body: string;
  kind: MessageKind;
  channel?: string;
  target?: string;
  /** Pre-built immediate body; present when the host delivers in immediate mode. */
  immediateMessage?: InboundImmediateMessage;
}

interface PendingImmediate {
  message: InboundImmediateMessage;
}

// ── Inbound frame routing ─────────────────────────────────────

/** Normalized metadata for one inbound `msg` frame. */
export interface InboundFrameMetadata {
  msgId: string;
  sender: string;
  body: string;
  kind: MessageKind;
  channel?: string;
  target?: string;
  toInfo: string;
}

const FROM_PREFIX_RE = /^\[from: ([^\]]+)\] ?/;

/** Strip an optional `[from: name]` prefix an adapter may prepend to bodies. */
export function parseIncoming(text: string): {
  from: string | null;
  text: string;
} {
  const match = text.match(FROM_PREFIX_RE);
  if (match) {
    return { from: match[1], text: text.slice(match[0].length) };
  }
  return { from: null, text };
}

/**
 * Derive kind/toInfo consistently from `channel`, then `to`, else broadcast.
 * Returns null for a frame lacking a non-empty string `msg_id` so the caller
 * can skip it without dropping later valid frames in the same chunk.
 */
export function deriveInboundMetadata(msg: {
  msg_id?: unknown;
  from_name?: unknown;
  from?: unknown;
  text?: unknown;
  channel?: unknown;
  to?: unknown;
}): InboundFrameMetadata | null {
  if (typeof msg.msg_id !== "string" || msg.msg_id.length === 0) return null;
  const fromRaw =
    typeof msg.from_name === "string" && msg.from_name
      ? msg.from_name
      : typeof msg.from === "string" && msg.from
        ? msg.from
        : "unknown";
  const rawText = typeof msg.text === "string" ? msg.text : "";
  const parsed = parseIncoming(rawText);
  const sender = parsed.from || fromRaw;
  const body = parsed.text;
  const channel =
    typeof msg.channel === "string" && msg.channel ? msg.channel : undefined;
  const target = typeof msg.to === "string" && msg.to ? msg.to : undefined;
  const kind: MessageKind = channel
    ? "channel"
    : target
      ? "direct"
      : "broadcast";
  const toInfo = channel
    ? `on ${channel}`
    : target
      ? `to ${target}`
      : "via broadcast";
  return { msgId: msg.msg_id, sender, body, kind, channel, target, toInfo };
}

function summarizeSender(snap: MailboxSnapshot): string {
  if (snap.bySender.length === 0) {
    return snap.unread === 0 ? "empty" : "unknown senders";
  }
  return snap.bySender
    .map((entry) => `${entry.sender} (${entry.count})`)
    .join(", ");
}

function entryLabel(entry: MailboxSnapshotEntry): string {
  const suffix = entry.channel
    ? ` on ${entry.channel}`
    : entry.target
      ? ` to ${entry.target}`
      : "";
  return `${entry.id} from ${entry.sender}${suffix} (${entry.kind})`;
}

/** Build the model-visible notice content from a snapshot. Metadata only. */
export function buildNoticeContent(snap: MailboxSnapshot): string {
  const lines = [
    `inter-agent mailbox: ${snap.unread} unread message(s)`,
    ...snap.messages.map((entry) => `- ${entryLabel(entry)}`),
  ];
  lines.push(
    "The inter_agent_read_messages tool can read and remove the queued bodies listed above. " +
      "Decide for yourself whether reading them now advances the current authorized work; this notice does not require a reply, acknowledgment, or any outbound action.",
  );
  return lines.join("\n");
}

/** Build a one-line compact rendering string (metadata only). */
export function buildNoticeCompact(snap: MailboxSnapshot): string {
  if (snap.unread === 0) return "inter-agent mailbox: 0 unread";
  return `inter-agent mailbox: ${summarizeSender(snap)} • ${snap.unread} unread`;
}

/** Build expanded per-message rendering lines (metadata only). */
export function buildNoticeExpanded(snap: MailboxSnapshot): string[] {
  if (snap.unread === 0) return ["no unread inter-agent messages"];
  return snap.messages.map((entry) => `- ${entryLabel(entry)}`);
}

export class Mailbox {
  private readonly messages: MailboxMessage[] = [];
  private seq = 0;

  get size(): number {
    return this.messages.length;
  }

  add(input: {
    msgId: string;
    sender: string;
    body: string;
    kind: MessageKind;
    channel?: string;
    target?: string;
  }): InboundAddOutcome {
    if (typeof input.msgId !== "string" || input.msgId.length === 0) {
      return { status: "malformed" };
    }
    if (this.messages.some((m) => m.msgId === input.msgId)) {
      return { status: "duplicate" };
    }
    const arrival = this.seq++;
    let evicted = false;
    this.messages.push({
      msgId: input.msgId,
      sender: input.sender,
      body: input.body,
      kind: input.kind,
      channel: input.channel,
      target: input.target,
      arrival,
    });
    if (this.messages.length > MAILBOX_MAX_UNREAD) {
      this.messages.shift();
      evicted = true;
    }
    return { status: "added", duplicate: false, evicted };
  }

  /** Remove and return messages. `ids === undefined` reads all unread. */
  read(ids?: string[]): MailboxReadResult {
    if (ids === undefined) {
      const all = this.messages.splice(0);
      return { read: all, missing: [], remaining: this.messages.length };
    }
    const read: MailboxMessage[] = [];
    const missing: string[] = [];
    const seen = new Set<string>();
    for (const requested of ids) {
      if (typeof requested !== "string" || requested.length === 0) continue;
      if (seen.has(requested)) continue;
      seen.add(requested);
      const index = this.messages.findIndex((m) => m.msgId === requested);
      if (index === -1) {
        missing.push(requested);
        continue;
      }
      read.push(this.messages[index]);
      this.messages.splice(index, 1);
    }
    read.sort((a, b) => a.arrival - b.arrival);
    return { read, missing, remaining: this.messages.length };
  }

  snapshot(): MailboxSnapshot {
    const entries: MailboxSnapshotEntry[] = this.messages.map((m) => ({
      id: m.msgId,
      sender: m.sender,
      kind: m.kind,
      channel: m.channel,
      target: m.target,
    }));
    const counts = new Map<string, number>();
    for (const m of this.messages) {
      counts.set(m.sender, (counts.get(m.sender) ?? 0) + 1);
    }
    const bySender: SenderGroup[] = [];
    for (const [sender, count] of counts) {
      bySender.push({ sender, count });
    }
    bySender.sort((a, b) =>
      a.count === b.count
        ? a.sender.localeCompare(b.sender)
        : b.count - a.count,
    );
    return { unread: this.messages.length, messages: entries, bySender };
  }

  clear(): void {
    this.messages.length = 0;
    this.seq = 0;
  }
}

/**
 * Orchestrates queued storage, metadata-only notices with debounced
 * coalescing, and immediate-mode burst delivery. All async work is guarded by
 * a generation counter so callbacks no-op after reload, replacement, or
 * shutdown.
 */
export class MailboxDispatcher {
  private readonly mailbox = new Mailbox();
  private mode: DeliveryMode;
  private debounceMs: number;
  private generation = 0;
  private noticeTimer: (() => void) | null = null;
  private pendingImmediate: PendingImmediate[] = [];
  private immediateBurstGen = 0;
  // A single generation-scoped pending-notice flag. While the agent is active,
  // arrivals hold at most one pending notice; on settle it is rebuilt from the
  // current mailbox and emitted as one latest complete snapshot. Reads that
  // empty the mailbox before the flush emit nothing.
  private pendingNotice = false;
  private noticeBurstGen = 0;

  constructor(
    private readonly host: MailboxHost,
    mode: DeliveryMode,
    debounceMs: number,
  ) {
    this.mode = mode;
    this.debounceMs = debounceMs;
  }

  get size(): number {
    return this.mailbox.size;
  }

  setDeliveryMode(mode: DeliveryMode): void {
    this.mode = mode;
  }

  getDeliveryMode(): DeliveryMode {
    return this.mode;
  }

  setDebounceMs(ms: number): void {
    this.debounceMs = ms;
  }

  /** Inbound message routing. Decides queued vs immediate delivery. */
  deliverInbound(dispatch: InboundDispatch): void {
    if (this.mode === "immediate" && dispatch.immediateMessage) {
      this.deliverImmediate(dispatch.immediateMessage);
      return;
    }
    const outcome = this.mailbox.add({
      msgId: dispatch.msgId,
      sender: dispatch.sender,
      body: dispatch.body,
      kind: dispatch.kind,
      channel: dispatch.channel,
      target: dispatch.target,
    });
    if (outcome.status === "malformed") {
      this.host.notifyWarning(
        "dropped an inbound message without a valid msg_id",
      );
      return;
    }
    if (outcome.status === "duplicate") {
      this.host.notifyWarning(
        `ignored duplicate message ${dispatch.msgId} from ${dispatch.sender} (first copy kept)`,
      );
      return;
    }
    if (outcome.evicted) {
      this.host.notifyWarning(
        `mailbox full; evicted the oldest unread message to stay under ${MAILBOX_MAX_UNREAD}`,
      );
    }
    this.scheduleNotice();
  }

  private deliverImmediate(message: InboundImmediateMessage): void {
    // Deliver right away only when Pi is idle with no queued continuation and
    // nothing else is already waiting. Otherwise coalesce into the pending
    // burst; `flushImmediate`
    // (called on agent-end / settled) triggers at most one new turn and
    // delivers the rest as non-triggering follow-up context.
    if (
      this.host.isIdle() &&
      !this.host.hasPendingMessages() &&
      this.pendingImmediate.length === 0
    ) {
      this.host.sendImmediate(message, true);
      return;
    }
    if (this.pendingImmediate.length === 0) {
      this.immediateBurstGen = this.generation;
    }
    this.pendingImmediate.push({ message });
  }

  /** Called when the agent run has settled (e.g. on agent-end). */
  flushImmediate(): void {
    const burst = this.pendingImmediate;
    if (burst.length === 0) return;
    if (this.immediateBurstGen !== this.generation) {
      this.pendingImmediate = [];
      return;
    }
    const [first, ...rest] = burst;
    this.pendingImmediate = [];
    this.host.sendImmediate(first.message, true);
    for (const item of rest) {
      this.host.sendImmediate(item.message, false);
    }
  }

  private scheduleNotice(): void {
    if (this.noticeTimer) {
      this.noticeTimer();
      this.noticeTimer = null;
    }
    const gen = this.generation;
    const fire = (): void => {
      this.noticeTimer = null;
      if (gen !== this.generation) return;
      this.holdOrDeliverNotice();
    };
    this.noticeTimer = this.host.schedule(fire, this.debounceMs);
  }

  // When Pi is idle with no queued continuation and no notice is already
  // pending, a queued arrival provokes one metadata-only mailbox-awareness turn
  // right away. Otherwise the latest arrival just marks one notice pending; on
  // settle (`flushNotices`) that pending notice is rebuilt from the current
  // mailbox and emitted as a single latest complete snapshot.
  private holdOrDeliverNotice(): void {
    const snap = this.mailbox.snapshot();
    if (snap.unread === 0) return;
    if (
      this.host.isIdle() &&
      !this.host.hasPendingMessages() &&
      !this.pendingNotice
    ) {
      this.host.sendNotice(this.buildNotice(snap), true);
      return;
    }
    if (!this.pendingNotice) {
      this.noticeBurstGen = this.generation;
    }
    this.pendingNotice = true;
  }

  private buildNotice(snap: MailboxSnapshot): MailboxNoticeMessage {
    return {
      customType: "inter-agent-mailbox",
      display: true,
      content: buildNoticeContent(snap),
      details: snap,
    };
  }

  /** Flush a pending waiting notice when the agent run has settled. */
  flushNotices(): void {
    if (!this.pendingNotice) return;
    this.pendingNotice = false;
    if (this.noticeBurstGen !== this.generation) return;
    const snap = this.mailbox.snapshot();
    if (snap.unread === 0) return;
    this.host.sendNotice(this.buildNotice(snap), true);
  }

  /** Flush waiting immediate bodies and notices only when truly settled. */
  settle(): void {
    if (!this.host.isIdle() || this.host.hasPendingMessages()) return;
    this.flushImmediate();
    this.flushNotices();
  }

  /** Read and remove messages; shared by the read tool. */
  read(ids?: string[]): MailboxReadResult {
    return this.mailbox.read(ids);
  }

  snapshot(): MailboxSnapshot {
    return this.mailbox.snapshot();
  }

  /** Stop all work and clear state for an explicit session shutdown. */
  shutdown(): void {
    this.generation += 1;
    if (this.noticeTimer) {
      this.noticeTimer();
      this.noticeTimer = null;
    }
    this.pendingImmediate = [];
    this.pendingNotice = false;
    this.mailbox.clear();
  }
}
