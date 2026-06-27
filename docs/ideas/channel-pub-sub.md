---
title: Implement channel pub/sub routing behind explicit capability flags
description: Add channel-based routing so agents can subscribe to named topics instead of receiving only direct messages or global broadcasts.
area: protocol
priority: user-prioritized
trigger: A concrete workflow or host integration needs targeted multicast that direct send and broadcast cannot express cleanly.
source: Root IDEAS.md prioritized follow-up
---

## Notes

- Channel naming and validation rules.
- Subscribe/unsubscribe operations.
- Interaction with direct messages and global broadcast.
- Capability negotiation and fallback behavior.
- Conformance tests and schema updates.
