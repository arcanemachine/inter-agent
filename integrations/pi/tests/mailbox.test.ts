import { test } from "node:test";
import assert from "node:assert/strict";

import {
  MAILBOX_MAX_UNREAD,
  MAILBOX_NOTICE_DEBOUNCE_MS_DEFAULT,
  MailboxDispatcher,
  buildNoticeCompact,
  buildNoticeExpanded,
  deriveInboundMetadata,
  effectiveDeliveryMode,
  effectiveDebounceMs,
  isValidDebounceMs,
  isValidDeliveryMode,
  parseIncoming,
  type InboundDispatch,
  type InboundImmediateMessage,
  type MailboxHost,
  type MailboxNoticeMessage,
  type MessageKind,
} from "../src/mailbox.js";

interface ImmediateRecord {
  message: InboundImmediateMessage;
  triggerTurn: boolean;
}

interface NoticeRecord {
  message: MailboxNoticeMessage;
  triggerTurn: boolean;
}

interface FakeTimer {
  fn: () => void;
  cancelled: boolean;
}

class FakeHost implements MailboxHost {
  readonly notices: NoticeRecord[] = [];
  readonly immediates: ImmediateRecord[] = [];
  readonly warnings: string[] = [];
  readonly timers: FakeTimer[] = [];
  idle = true;
  pendingMessages = false;

  isIdle(): boolean {
    return this.idle;
  }

  hasPendingMessages(): boolean {
    return this.pendingMessages;
  }

  sendNotice(message: MailboxNoticeMessage, triggerTurn: boolean): void {
    this.notices.push({ message, triggerTurn });
  }

  sendImmediate(message: InboundImmediateMessage, triggerTurn: boolean): void {
    this.immediates.push({ message, triggerTurn });
  }

  notifyWarning(body: string): void {
    this.warnings.push(body);
  }

  // The dispatcher cancels prior notice timers itself via the returned cancel
  // function, so the host only needs to record each timer and let callers fire
  // them. This lets a deferred settlement timer coexist with a notice timer.
  schedule(fn: () => void, _ms: number): () => void {
    const timer: FakeTimer = { fn, cancelled: false };
    this.timers.push(timer);
    return () => {
      timer.cancelled = true;
    };
  }

  /** Fire the latest non-cancelled timer (debounce timers fire one at a time). */
  firePending(): void {
    for (let i = this.timers.length - 1; i >= 0; i--) {
      const timer = this.timers[i];
      if (!timer.cancelled) {
        timer.cancelled = true;
        timer.fn();
        return;
      }
    }
  }

  pendingCount(): number {
    return this.timers.filter((t) => !t.cancelled).length;
  }
}

function immediateMessage(
  id: string,
  body = `body-${id}`,
  sender = "peer",
): InboundImmediateMessage {
  return {
    customType: "inter-agent-message",
    content: `content-${id}`,
    display: true,
    details: {
      from: sender,
      text: body,
      toInfo: "to me",
      displayContent: `display-${id}`,
    },
  };
}

function queuedDispatch(
  id: string,
  body = `body-${id}`,
  sender = "peer",
  kind: MessageKind = "direct",
  channel?: string,
  target?: string,
): InboundDispatch {
  return { msgId: id, sender, body, kind, channel, target };
}

function makeDispatcher(
  host: FakeHost,
  mode: "queued" | "immediate" = "queued",
  debounceMs = 0,
): MailboxDispatcher {
  return new MailboxDispatcher(host, mode, debounceMs);
}

test("queued is the default and bodies stay out of notices until read", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  const body = "SECRET-MARKER-queued-body";
  mailbox.deliverInbound(queuedDispatch("m1", body, "alice"));

  assert.equal(host.notices.length, 0);
  host.firePending();
  assert.equal(host.notices.length, 1);
  // A queued arrival while idle provokes one mailbox-awareness turn.
  assert.equal(host.notices[0].triggerTurn, true);
  const notice = host.notices[0].message;
  assert.equal(notice.customType, "inter-agent-mailbox");
  assert.equal(notice.details.unread, 1);
  assert.deepEqual(notice.details.messages, [
    {
      id: "m1",
      sender: "alice",
      kind: "direct",
      channel: undefined,
      target: undefined,
    },
  ]);
  assert.equal(notice.details.bySender.length, 1);
  assert.equal(notice.details.bySender[0].sender, "alice");
  // Body never reaches model-visible notice content or details.
  assert.ok(!notice.content.includes(body));
  assert.ok(!JSON.stringify(notice.details).includes(body));
  assert.ok(notice.content.includes("m1"));
  assert.ok(notice.content.includes("alice"));
});

test("direct, broadcast, and channel bodies share one mailbox with metadata distinct", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(
    queuedDispatch("d1", "bd", "a", "direct", undefined, "me"),
  );
  mailbox.deliverInbound(queuedDispatch("b1", "bb", "a", "broadcast"));
  mailbox.deliverInbound(queuedDispatch("c1", "bc", "a", "channel", "updates"));

  host.firePending();
  const snap = host.notices[0].message.details;
  assert.equal(snap.unread, 3);
  const ids = snap.messages.map((m) => m.id);
  assert.deepEqual(["d1", "b1", "c1"], ids);
  assert.equal(snap.messages[2].channel, "updates");
  assert.equal(snap.messages[0].target, "me");
  // No body text anywhere in the notice.
  assert.ok(!JSON.stringify(snap).includes("bd"));
  assert.ok(!JSON.stringify(snap).includes("bb"));
  assert.ok(!JSON.stringify(snap).includes("bc"));
});

test("read-all returns messages in arrival order and empties the mailbox", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("a", "1", "alice"));
  mailbox.deliverInbound(queuedDispatch("b", "2", "bob"));
  mailbox.deliverInbound(
    queuedDispatch("c", "3", "alice", "channel", "updates"),
  );

  const result = mailbox.read();
  assert.equal(result.read.length, 3);
  assert.deepEqual(
    result.read.map((m) => m.msgId),
    ["a", "b", "c"],
  );
  assert.equal(result.remaining, 0);
  assert.equal(result.missing.length, 0);
  assert.equal(mailbox.size, 0);
  // Reading performs no outbound action.
  assert.equal(host.notices.length, 0);
  assert.equal(host.immediates.length, 0);
});

test("read selected ids returns arrival order regardless of request order", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("a", "1"));
  mailbox.deliverInbound(queuedDispatch("b", "2"));
  mailbox.deliverInbound(queuedDispatch("c", "3"));

  const result = mailbox.read(["c", "a"]);
  assert.deepEqual(
    result.read.map((m) => m.msgId),
    ["a", "c"],
  );
  assert.equal(result.remaining, 1);
  // Remaining unread set is the untouched message.
  assert.deepEqual(
    mailbox.read().read.map((m) => m.msgId),
    ["b"],
  );
});

test("mixed valid and missing ids succeed and report missing separately", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("a", "1"));

  const result = mailbox.read(["a", "ghost", "a"]);
  assert.deepEqual(
    result.read.map((m) => m.msgId),
    ["a"],
  );
  assert.deepEqual(result.missing, ["ghost"]);
});

test("explicitly empty ids selection and empty mailbox reads succeed", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  // Empty mailbox, no ids.
  const empty = mailbox.read();
  assert.equal(empty.read.length, 0);
  assert.equal(empty.missing.length, 0);
  // Empty mailbox, explicitly empty ids array.
  const emptyIds = mailbox.read([]);
  assert.equal(emptyIds.read.length, 0);
  assert.equal(emptyIds.missing.length, 0);
  // Non-empty mailbox with explicitly empty ids selects nothing.
  mailbox.deliverInbound(queuedDispatch("a", "1"));
  const selection = mailbox.read([]);
  assert.equal(selection.read.length, 0);
  assert.equal(selection.remaining, 1);
});

test("reading a previously-shown id after clearing reports missing", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("a", "1"));
  const before = mailbox.read(["a"]);
  assert.equal(before.read.length, 1);
  // Simulate reload/replacement clearing in-memory state.
  mailbox.shutdown();
  const after = mailbox.read(["a"]);
  assert.equal(after.read.length, 0);
  assert.deepEqual(after.missing, ["a"]);
});

test("immediate mode while idle delivers the body immediately with a trigger", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "immediate", 0);
  host.idle = true;
  mailbox.deliverInbound({
    ...queuedDispatch("m1", "SECRET-body", "alice"),
    immediateMessage: immediateMessage("m1", "SECRET-body", "alice"),
  });

  assert.equal(host.immediates.length, 1);
  assert.equal(host.immediates[0].triggerTurn, true);
  // Immediate bodies never enter the unread mailbox.
  assert.equal(mailbox.size, 0);
  assert.equal(host.notices.length, 0);
});

test("queued messages are retained when switching to immediate and back", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("old", "queued-body", "alice"));
  host.firePending();

  mailbox.setDeliveryMode("immediate");
  host.idle = true;
  mailbox.deliverInbound({
    ...queuedDispatch("new", "immediate-body", "bob"),
    immediateMessage: immediateMessage("new", "immediate-body", "bob"),
  });
  assert.equal(host.immediates.length, 1);
  // Old queued message is retained as unread.
  assert.equal(mailbox.size, 1);
  assert.deepEqual(
    mailbox.read().read.map((m) => m.msgId),
    ["old"],
  );

  // Switch back to queued; future arrivals queue again.
  mailbox.setDeliveryMode("queued");
  mailbox.deliverInbound(queuedDispatch("after", "again", "alice"));
  assert.equal(mailbox.size, 1);
  assert.deepEqual(
    mailbox.read().read.map((m) => m.msgId),
    ["after"],
  );
});

test("immediate burst waiting behind active work triggers at most one new turn", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "immediate", 0);
  host.idle = false;

  mailbox.deliverInbound({
    ...queuedDispatch("a"),
    immediateMessage: immediateMessage("a"),
  });
  mailbox.deliverInbound({
    ...queuedDispatch("b"),
    immediateMessage: immediateMessage("b"),
  });
  mailbox.deliverInbound({
    ...queuedDispatch("c"),
    immediateMessage: immediateMessage("c"),
  });
  // Nothing delivered while active.
  assert.equal(host.immediates.length, 0);

  host.idle = true;
  mailbox.settle();
  const triggered = host.immediates.filter((i) => i.triggerTurn).length;
  const followups = host.immediates.filter((i) => !i.triggerTurn).length;
  assert.equal(triggered, 1);
  assert.equal(followups, 2);
  assert.equal(host.immediates.length, 3);
  // First delivered with a trigger, rest as follow-up context.
  assert.equal(host.immediates[0].triggerTurn, true);
  assert.equal(host.immediates[1].triggerTurn, false);
  assert.equal(host.immediates[2].triggerTurn, false);

  // A second waiting burst after the agent runs again also triggers once.
  host.immediates.length = 0;
  host.idle = false;
  mailbox.deliverInbound({
    ...queuedDispatch("d"),
    immediateMessage: immediateMessage("d"),
  });
  mailbox.deliverInbound({
    ...queuedDispatch("e"),
    immediateMessage: immediateMessage("e"),
  });
  host.idle = true;
  mailbox.settle();
  assert.equal(host.immediates.filter((i) => i.triggerTurn).length, 1);
});

test("immediate arrival waits while idle with a queued continuation", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "immediate", 0);
  host.idle = true;
  host.pendingMessages = true;

  mailbox.deliverInbound({
    ...queuedDispatch("a", "body-a", "alice"),
    immediateMessage: immediateMessage("a", "body-a", "alice"),
  });
  // isIdle() alone is insufficient: a queued continuation must settle first.
  assert.equal(host.immediates.length, 0);

  mailbox.settle();
  assert.equal(host.immediates.length, 0);

  host.pendingMessages = false;
  mailbox.settle();
  assert.equal(host.immediates.length, 1);
  assert.equal(host.immediates[0].triggerTurn, true);
  assert.equal(host.immediates[0].message.details.text, "body-a");
});

test("immediate delivery never calls steer or abort", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "immediate", 0);
  host.idle = true;
  mailbox.deliverInbound({
    ...queuedDispatch("a"),
    immediateMessage: immediateMessage("a"),
  });
  // The host interface exposes no steer or abort; delivery only uses
  // sendImmediate with follow-up delivery.
  assert.equal(host.immediates.length, 1);
  assert.equal(host.warnings.length, 0);
  assert.equal(host.notices.length, 0);
});

test("128-message overflow evicts the oldest unread and warns once", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  for (let i = 0; i <= MAILBOX_MAX_UNREAD; i++) {
    mailbox.deliverInbound(queuedDispatch(`m-${i}`, `body-${i}`, "peer"));
  }
  assert.equal(mailbox.size, MAILBOX_MAX_UNREAD);
  const evictionWarnings = host.warnings.filter((w) => w.includes("evicted"));
  assert.equal(evictionWarnings.length, 1);
  const remaining = mailbox.read().read.map((m) => m.msgId);
  assert.ok(!remaining.includes("m-0"));
  assert.deepEqual(remaining[0], "m-1");
  assert.deepEqual(remaining[remaining.length - 1], `m-${MAILBOX_MAX_UNREAD}`);
});

test("duplicate live msg_id keeps the first body and warns", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("dup", "first-body", "alice"));
  mailbox.deliverInbound(queuedDispatch("dup", "second-body", "alice"));

  assert.equal(mailbox.size, 1);
  const dupWarnings = host.warnings.filter((w) => w.includes("duplicate"));
  assert.equal(dupWarnings.length, 1);
  const result = mailbox.read(["dup"]);
  assert.equal(result.read[0].body, "first-body");
});

test("malformed msg_id without a valid id is rejected with a warning", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound({ ...queuedDispatch("ok"), msgId: "" });
  assert.equal(mailbox.size, 0);
  assert.equal(host.warnings.length, 1);
  assert.equal(host.notices.length, 0);
});

test("debounce 0 delivers a notice for the latest snapshot on fire", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("a", "1", "alice"));
  mailbox.deliverInbound(queuedDispatch("b", "2", "bob"));
  mailbox.deliverInbound(queuedDispatch("c", "3", "alice"));

  assert.equal(host.notices.length, 0);
  host.firePending();
  assert.equal(host.notices.length, 1);
  assert.equal(host.notices[0].message.details.unread, 3);
});

test("debounce coalesces a burst into one notice with the latest snapshot", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 200);
  mailbox.deliverInbound(queuedDispatch("a", "1", "alice"));
  mailbox.deliverInbound(queuedDispatch("b", "2", "bob"));
  mailbox.deliverInbound(queuedDispatch("c", "3", "alice"));

  assert.equal(host.pendingCount(), 1);
  host.firePending();
  assert.equal(host.notices.length, 1);
  assert.deepEqual(
    host.notices[0].message.details.messages.map((m) => m.id),
    ["a", "b", "c"],
  );
});

test("debounce replaces the pending timer with the latest snapshot", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 200);
  mailbox.deliverInbound(queuedDispatch("a", "1", "alice"));
  const firstTimer = host.timers[host.timers.length - 1];
  mailbox.deliverInbound(queuedDispatch("b", "2", "bob"));

  assert.equal(host.timers.length, 2);
  assert.equal(firstTimer.cancelled, true);
  assert.equal(host.pendingCount(), 1);
  host.firePending();
  assert.deepEqual(
    host.notices[0].message.details.messages.map((m) => m.id),
    ["a", "b"],
  );
});

test("shutdown cancels pending notice timers and clears mailbox state", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 200);
  mailbox.deliverInbound(queuedDispatch("a", "1", "alice"));
  assert.equal(host.pendingCount(), 1);
  mailbox.shutdown();
  assert.equal(host.pendingCount(), 0);
  host.firePending();
  assert.equal(host.notices.length, 0);
  assert.equal(mailbox.size, 0);
  assert.deepEqual(mailbox.read(["a"]).missing, ["a"]);
});

test("stale immediate callbacks after shutdown cannot deliver bodies", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "immediate", 0);
  host.idle = false;
  mailbox.deliverInbound({
    ...queuedDispatch("a"),
    immediateMessage: immediateMessage("a"),
  });
  // Bodies were waiting; shutdown clears them and bumps the generation so a
  // late flush is a no-op.
  mailbox.shutdown();
  mailbox.flushImmediate();
  assert.equal(host.immediates.length, 0);
});

test("stale notice timer after a simulated reload does not emit", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 200);
  mailbox.deliverInbound(queuedDispatch("a", "1", "alice"));
  // Reload replaces the runtime; emulate it with shutdown on the prior owner.
  mailbox.shutdown();
  host.firePending();
  assert.equal(host.notices.length, 0);
});

test("config validation: delivery mode bounds and fallback", () => {
  assert.equal(effectiveDeliveryMode("immediate"), "immediate");
  assert.equal(effectiveDeliveryMode("queued"), "queued");
  assert.equal(effectiveDeliveryMode(undefined), "queued");
  assert.equal(effectiveDeliveryMode("bogus"), "queued");
  assert.ok(isValidDeliveryMode("queued"));
  assert.ok(isValidDeliveryMode("immediate"));
  assert.ok(!isValidDeliveryMode("bogus"));
  assert.ok(!isValidDeliveryMode(123));
});

test("config validation: debounce bounds and fallback", () => {
  assert.equal(MAILBOX_NOTICE_DEBOUNCE_MS_DEFAULT, 0);
  assert.equal(effectiveDebounceMs(undefined), 0);
  assert.equal(effectiveDebounceMs(0), 0);
  assert.equal(effectiveDebounceMs(200), 200);
  assert.equal(effectiveDebounceMs(5000), 5000);
  assert.equal(effectiveDebounceMs(5001), 0);
  assert.equal(effectiveDebounceMs(-1), 0);
  assert.equal(effectiveDebounceMs(1.5), 0);
  assert.equal(effectiveDebounceMs("200"), 0);
  assert.equal(effectiveDebounceMs(NaN), 0);
  assert.equal(effectiveDebounceMs(Infinity), 0);
  assert.ok(isValidDebounceMs(0));
  assert.ok(isValidDebounceMs(5000));
  assert.ok(!isValidDebounceMs(5001));
  assert.ok(!isValidDebounceMs(-1));
  assert.ok(!isValidDebounceMs(1.5));
  assert.ok(!isValidDebounceMs("200"));
});

test("notice renders complete metadata compactly and expanded without bodies", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(
    queuedDispatch("a", "SECRET-a", "alice", "direct", undefined, "me"),
  );
  mailbox.deliverInbound(
    queuedDispatch("b", "SECRET-b", "alice", "channel", "updates"),
  );
  mailbox.deliverInbound(queuedDispatch("c", "SECRET-c", "bob", "broadcast"));

  host.firePending();
  const snap = host.notices[0].message.details;

  const compact = buildNoticeCompact(snap);
  assert.ok(compact.includes("3 unread"));
  assert.ok(compact.includes("alice"));
  assert.ok(!compact.includes("SECRET"));

  const expanded = buildNoticeExpanded(snap);
  assert.equal(expanded.length, 3);
  for (const line of expanded) {
    assert.ok(!line.includes("SECRET"));
  }
  assert.ok(expanded[0].includes("a"));
  assert.ok(expanded[0].includes("alice"));
  assert.ok(expanded[1].includes("updates"));
  assert.ok(expanded[1].includes("channel"));
  assert.ok(expanded[2].includes("bob"));
  assert.ok(expanded[2].includes("broadcast"));
});

test("queued notices are metadata-only and never include bodies across kinds", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(
    queuedDispatch("d", "D-MARKER", "a", "direct", undefined, "me"),
  );
  mailbox.deliverInbound(queuedDispatch("br", "BR-MARKER", "a", "broadcast"));
  mailbox.deliverInbound(
    queuedDispatch("ch", "CH-MARKER", "a", "channel", "x"),
  );

  host.firePending();
  const notice = host.notices[0].message;
  for (const marker of ["D-MARKER", "BR-MARKER", "CH-MARKER"]) {
    assert.ok(!notice.content.includes(marker));
    assert.ok(!JSON.stringify(notice.details).includes(marker));
  }
});

test("queued notice provokes one non-steering awareness turn while idle", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  host.idle = true;
  mailbox.deliverInbound(queuedDispatch("a", "1", "alice"));
  host.firePending();
  assert.equal(host.notices.length, 1);
  assert.equal(host.notices[0].triggerTurn, true);
  // Hold for read decision only; no outbound action prescribed.
  assert.ok(
    host.notices[0].message.content.includes(
      "Decide for yourself whether reading",
    ),
  );
  assert.ok(
    host.notices[0].message.content.includes(
      "does not require a reply, acknowledgment, or any outbound action",
    ),
  );
});

test("queued active burst holds one pending notice and flushes the latest snapshot", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  host.idle = false;

  // Three active arrivals each fire their debounce timer while the agent is
  // active, so they coalesce into a single pending notice rather than stale
  // intermediate snapshots [a], [a,b], [a,b,c].
  mailbox.deliverInbound(queuedDispatch("a", "body-a", "alice"));
  host.firePending();
  mailbox.deliverInbound(queuedDispatch("b", "body-b", "bob"));
  host.firePending();
  mailbox.deliverInbound(queuedDispatch("c", "body-c", "alice"));
  host.firePending();
  // Nothing delivered while the agent is active.
  assert.equal(host.notices.length, 0);

  host.idle = true;
  mailbox.settle();
  assert.equal(host.notices.length, 1);
  assert.equal(host.notices[0].triggerTurn, true);
  // The single flushed notice is rebuilt from the current mailbox, so it is
  // the latest complete snapshot, not an accumulated list of stale ones.
  assert.deepEqual(
    host.notices[0].message.details.messages.map((m) => m.id),
    ["a", "b", "c"],
  );
  for (const marker of ["body-a", "body-b", "body-c"]) {
    assert.ok(!host.notices[0].message.content.includes(marker));
    assert.ok(
      !JSON.stringify(host.notices[0].message.details).includes(marker),
    );
  }
});

test("reads that empty the mailbox before a pending notice flush emit nothing", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  host.idle = false;

  mailbox.deliverInbound(queuedDispatch("a", "body-a", "alice"));
  host.firePending();
  mailbox.deliverInbound(queuedDispatch("b", "body-b", "bob"));
  host.firePending();
  mailbox.deliverInbound(queuedDispatch("c", "body-c", "alice"));
  host.firePending();
  assert.equal(host.notices.length, 0);

  // The agent reads and removes everything before the settlement check.
  mailbox.read();
  host.idle = true;
  mailbox.settle();
  assert.equal(host.notices.length, 0);
  assert.equal(mailbox.size, 0);
});

test("queued arrival waits while idle with a queued continuation", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  host.idle = true;
  host.pendingMessages = true;

  mailbox.deliverInbound(queuedDispatch("a", "body-a", "alice"));
  host.firePending();
  // A queued continuation holds the mailbox-awareness notice even though Pi is
  // momentarily idle between runs.
  assert.equal(host.notices.length, 0);

  mailbox.settle();
  assert.equal(host.notices.length, 0);

  host.pendingMessages = false;
  mailbox.settle();
  assert.equal(host.notices.length, 1);
  assert.equal(host.notices[0].triggerTurn, true);
  assert.deepEqual(
    host.notices[0].message.details.messages.map((m) => m.id),
    ["a"],
  );
});

test("queued notice never steers or aborts, and is body-free", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  host.idle = true;
  mailbox.deliverInbound(queuedDispatch("a", "SECRET-q", "alice"));
  host.firePending();
  assert.equal(host.notices.length, 1);
  assert.equal(host.notices[0].triggerTurn, true);
  assert.ok(!host.notices[0].message.content.includes("SECRET-q"));
  assert.ok(
    !JSON.stringify(host.notices[0].message.details).includes("SECRET-q"),
  );
  // The host interface exposes no steer or abort path; nothing else recorded.
  assert.equal(host.immediates.length, 0);
});

test("settlement flushes once after the final agent_settled with no pending continuations", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);

  // Active run with queued continuations: the settled handler finds pending
  // messages and flushes nothing, leaving the next agent_settled to retry.
  host.idle = false;
  host.pendingMessages = true;
  mailbox.deliverInbound(queuedDispatch("a", "body-a", "alice"));
  host.firePending();
  mailbox.settle();
  assert.equal(host.notices.length, 0);

  // A queued continuation runs and ends; still pending, so still no flush.
  mailbox.settle();
  assert.equal(host.notices.length, 0);

  // The final continuation ends with the agent idle and nothing pending: the
  // settled event flushes exactly one latest notice.
  host.idle = true;
  host.pendingMessages = false;
  mailbox.settle();
  assert.equal(host.notices.length, 1);
  assert.equal(host.notices[0].triggerTurn, true);
  assert.deepEqual(
    host.notices[0].message.details.messages.map((m) => m.id),
    ["a"],
  );
  assert.equal(host.pendingCount(), 0);
});

test("shutdown drops a pending settlement without flushing", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  host.idle = false;
  host.pendingMessages = true;
  mailbox.deliverInbound(queuedDispatch("a", "body-a", "alice"));
  host.firePending();
  mailbox.settle();
  // Shutdown clears the pending notice before terminal settlement.
  mailbox.shutdown();
  assert.equal(host.notices.length, 0);
  assert.equal(mailbox.size, 0);
});

test("settlement does not poll indefinitely while pending messages remain", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  // Active run holds the notice pending; queued continuations remain.
  host.idle = false;
  host.pendingMessages = true;
  mailbox.deliverInbound(queuedDispatch("a", "body-a", "alice"));
  host.firePending();
  assert.equal(host.notices.length, 0);
  // The agent ends but continuations remain; settlement flushes nothing and
  // does not reschedule itself.
  mailbox.settle();
  assert.equal(host.notices.length, 0);
  assert.equal(host.pendingCount(), 0);
  // The mailbox still holds the message for the next agent_settled to settle.
  assert.equal(mailbox.size, 1);
});

test("mailbox state survives a simulated listener stop/start with no reconnect method", () => {
  const host = new FakeHost();
  const mailbox = makeDispatcher(host, "queued", 0);
  mailbox.deliverInbound(queuedDispatch("a", "body-a", "alice"));
  mailbox.deliverInbound(queuedDispatch("b", "body-b", "bob"));
  host.firePending();
  assert.equal(mailbox.size, 2);
  // Listener stop/start within the same extension runtime does not clear the
  // dispatcher; there is no reconnect() method to call.
  assert.equal(
    typeof (mailbox as unknown as { reconnect?: unknown }).reconnect,
    "undefined",
  );
  assert.equal(mailbox.size, 2);
  const result = mailbox.read();
  assert.deepEqual(
    result.read.map((m) => m.msgId),
    ["a", "b"],
  );
});

test("deriveInboundMetadata derives kind and labels in channel/direct/broadcast order", () => {
  const channel = deriveInboundMetadata({
    msg_id: "c1",
    from_name: "alice",
    text: "hi",
    channel: "updates",
  });
  assert.equal(channel?.kind, "channel");
  assert.equal(channel?.toInfo, "on updates");
  assert.equal(channel?.channel, "updates");

  const direct = deriveInboundMetadata({
    msg_id: "d1",
    from_name: "alice",
    text: "hi",
    to: "me",
  });
  assert.equal(direct?.kind, "direct");
  assert.equal(direct?.toInfo, "to me");
  assert.equal(direct?.target, "me");

  // Broadcast uses the `via broadcast` label, never `to undefined`.
  const broadcast = deriveInboundMetadata({
    msg_id: "b1",
    from_name: "alice",
    text: "hi",
  });
  assert.equal(broadcast?.kind, "broadcast");
  assert.equal(broadcast?.toInfo, "via broadcast");
  assert.equal(broadcast?.target, undefined);
});

test("parseIncoming strips an optional [from: name] prefix and deriveInboundMetadata uses it", () => {
  assert.deepEqual(parseIncoming("[from: bob] hello"), {
    from: "bob",
    text: "hello",
  });
  assert.deepEqual(parseIncoming("no prefix"), {
    from: null,
    text: "no prefix",
  });

  const meta = deriveInboundMetadata({
    msg_id: "p1",
    from_name: "server-name",
    text: "[from: bob] real body",
  });
  assert.equal(meta?.sender, "bob");
  assert.equal(meta?.body, "real body");
  assert.equal(meta?.kind, "broadcast");
});

test("deriveInboundMetadata returns null for a malformed frame so the caller can continue", () => {
  assert.equal(deriveInboundMetadata({ from_name: "a", text: "x" }), null);
  assert.equal(deriveInboundMetadata({ msg_id: "", text: "x" }), null);
  assert.equal(deriveInboundMetadata({ msg_id: 5, text: "x" }), null);
  // A later valid frame in the same chunk is still selectable when present.
  assert.ok(deriveInboundMetadata({ msg_id: "ok", text: "x" }));
});

test("immediate delivery carries the body while queued notices stay metadata-only", () => {
  const marker = "IMMEDIATE-vs-QUEUED-body";
  const hostQ = new FakeHost();
  const queued = makeDispatcher(hostQ, "queued", 0);
  queued.deliverInbound(queuedDispatch("q1", marker, "alice"));
  hostQ.firePending();
  assert.equal(hostQ.immediates.length, 0);
  assert.equal(hostQ.notices.length, 1);
  assert.ok(!hostQ.notices[0].message.content.includes(marker));
  assert.ok(!JSON.stringify(hostQ.notices[0].message.details).includes(marker));

  const hostI = new FakeHost();
  const immediate = makeDispatcher(hostI, "immediate", 0);
  hostI.idle = true;
  immediate.deliverInbound({
    ...queuedDispatch("i1", marker, "alice"),
    immediateMessage: immediateMessage("i1", marker, "alice"),
  });
  assert.equal(hostI.immediates.length, 1);
  assert.equal(hostI.notices.length, 0);
  assert.equal(hostI.immediates[0].message.details.text, marker);
  assert.equal(hostI.immediates[0].triggerTurn, true);
});
