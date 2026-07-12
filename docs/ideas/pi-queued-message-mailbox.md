---
title: Add a queued Pi message mailbox
description: Queue inbound Pi messages outside model context until the receiving agent explicitly reads all or selected messages.
area: pi-extension
priority: user-prioritized
trigger: Activate after the leader/executor workflow bootstrap when the user selects Pi mailbox delivery for implementation.
source: User design discussion during agent workflow planning.
---

## Purpose

Add an in-memory Pi mailbox between transport receipt and model-context delivery. The mailbox preserves an agent's ability to complete independent reasoning before reading peer message bodies.

Queued delivery is the default. Receiving a message produces a minimal mailbox notice that triggers a Pi turn without placing the peer message body in model context. The receiving agent decides when to read messages.

## Accepted behavior

- Implement this only for Pi. Claude Code already separates message notification from explicit message-body retrieval through its bounded message log and does not need this mailbox feature.
- Treat the existing Claude Code behavior as the conceptual precedent, not as follow-up implementation scope.
- Default inbound delivery mode is `queued`; support `immediate` as an alternative.
- Pi extension configuration supplies the initial delivery mode.
- Add an autocomplete-aware `/inter-agent` subcommand that changes delivery mode for the current Pi session without rewriting configuration.
- Switching to immediate mode affects future arrivals. Existing queued messages remain queued until read.
- Queue direct and broadcast messages consistently.
- Keep the mailbox in memory. It survives listener disconnect/reconnect within the Pi session but not Pi process/session restart.
- Store at most 128 unread messages. On overflow, evict the oldest unread message and produce an explicit warning; never discard silently.
- Remove messages from the mailbox after they are read. Their tool results remain in normal Pi conversation history.

## Message identity and notices

Use the existing protocol `msg_id` as the mailbox selection ID. The core currently generates it as a 16-character random hexadecimal token with `secrets.token_hex(8)`. The ID is server-issued rather than namespaced to a Pi session; the mailbox containing it is session-local.

Every mailbox notice should describe the complete current unread mailbox using compact metadata only:

- protocol message ID;
- sender routing name;
- total unread count and grouped sender counts where useful.

Do not include peer message bodies in the notice. Do not add notice truncation, pagination, or a size ceiling in the first implementation; the 128-message mailbox bound is sufficient for this context-preservation feature.

Follow existing Pi custom-message rendering conventions:

- compact rendering shows a concise unread count grouped by sender;
- expanded rendering lists each unread message ID and sender routing name.

The underlying model-visible mailbox notice must retain the complete ID/sender list even when the human-facing transcript rendering is compact, so the agent can select messages without first receiving their bodies.

## Read tool

Expose one agent-callable read tool:

- no message IDs reads all currently unread messages;
- a list of message IDs reads only those messages;
- one call may select multiple IDs;
- valid requested messages are returned even if other requested IDs are unknown or already read;
- missing IDs are reported concisely rather than failing the entire call.

The exact tool and command names should match existing integration naming conventions during concrete planning.

## Notification debounce

Support an optional Pi extension configuration value for mailbox-notice debounce in milliseconds:

- default: `0`, producing an immediate notice for each arrival;
- recommended opt-in value: `200` milliseconds for coalescing messages arriving in a burst;
- candidate validation range: `0` through `5000` milliseconds, to be confirmed during concrete planning;
- debounce affects notice emission only, never message storage.

Do not add an interactive command for debounce tuning.

## Deferred protocol metadata

Do not add subject, generic extensible metadata, priority, or request/reply correlation in the first mailbox implementation.

A later protocol-level priority field may be considered separately. If accepted, it should be informational (`normal` or `urgent`), affect mailbox display or agent selection only, never bypass queued delivery, and include prompt guidance against escalating priority merely to obtain attention.

## Planning and verification requirements

Before implementation, inspect the Pi extension's listener, custom rendering, command autocomplete, configuration cascade, agent tool registration, and relevant static/live tests. Split protocol metadata work from the Pi mailbox task if metadata is later promoted.

The eventual user acceptance test should demonstrate:

1. queued mode prevents an inbound peer body from entering model context automatically;
2. the agent receives sender/count/ID metadata and can continue without reading;
3. one tool call can read all messages or selected IDs;
4. immediate mode applies to future arrivals while preserving existing queued messages;
5. mailbox state survives listener reconnect but clears on Pi restart;
6. overflow and optional debounce behavior are observable and tested.
