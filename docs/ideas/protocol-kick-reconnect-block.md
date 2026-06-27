---
title: Kick reconnect block
description: Make the kick operation effective against auto-reconnecting listeners by adding a temporary server-side blocklist.
area: protocol
priority: deferred
trigger: Stale sessions need to be reaped before auto-reconnecting listeners reclaim their names.
source: Root IDEAS.md protocol extensions
---

## Notes

- Keep an in-memory `kicked_names` map (name → expiry timestamp) populated on kick.
- Reject `hello` for a blocked name with a dedicated `KICKED` error until the block expires.
- Default block duration (e.g. 60s), optionally configurable via `INTER_AGENT_KICK_BLOCK_S`.
- Block by name only (agent names are unique) or also by session_id.
- Listeners should treat `KICKED` as non-permanent and retry with normal backoff so they recover automatically once the block lifts.
- The block is in-memory only and does not survive a server restart.
