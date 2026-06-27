---
title: Refine local install layout and path handling
description: Refine local install layout and path handling for application files versus runtime state, including platform-appropriate defaults and path expansion for settings such as `projectPath` and `dataDir`.
area: packaging
priority: user-prioritized
trigger: Host integrations need predictable, cross-platform paths for helper binaries, config, and runtime state.
source: Root IDEAS.md prioritized follow-up
---

## Notes

- Distinguish read-only application files from writable runtime state.
- Expand `~` and environment variables consistently.
- Document defaults for Linux and macOS.
