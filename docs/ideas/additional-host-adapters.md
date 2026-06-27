---
title: Additional host adapters
description: Add support for other coding-agent hosts once the adapter boundary is stable.
area: adapters
priority: deferred
trigger: A new host needs inter-agent integration and its runtime constraints are understood.
source: Root IDEAS.md additional host adapters
---

## Notes

- New adapters should use core APIs, preserve shared bus defaults, and must not redefine protocol semantics.
- Follow the thin-adapter pattern used by Pi and Claude Code.
