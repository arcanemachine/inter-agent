---
title: Pi project path auto-discovery
description: Improve project-path auto-discovery for the Pi extension instead of relying on a hardcoded fallback or explicit settings override.
area: pi-extension
priority: deferred
trigger: Users report friction locating the inter-agent project from arbitrary working directories.
source: Root IDEAS.md Pi extension follow-up
---

## Notes

- Check `PATH` first, then walk up from `process.cwd()` looking for `.venv/bin/inter-agent-pi`.
- Preserve existing override precedence.
