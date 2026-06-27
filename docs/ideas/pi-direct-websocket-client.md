---
title: Pi direct WebSocket client
description: Replace the Python CLI bridge in the Pi extension with a direct TypeScript WebSocket client.
area: pi-extension
priority: deferred
trigger: The prospective OpenCode direct client proves the JavaScript client shape and Pi packaging favors a host-native client.
source: Root IDEAS.md Pi extension follow-up
---

## Notes

- Add `ws` as a runtime dependency.
- Implement hello handshake, token auth, send/broadcast/list/status/shutdown, and the listener loop.
- Port token path, identity verification, and frame parsing from the Python core.
