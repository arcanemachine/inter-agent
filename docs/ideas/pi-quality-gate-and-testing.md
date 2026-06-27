---
title: Pi extension quality gate and testing
description: Decide and implement the right level of automated validation for the Pi TypeScript extension.
area: pi-extension
priority: deferred
trigger: The TypeScript extension grows complex enough that manual validation is no longer sufficient.
source: Root IDEAS.md Pi extension follow-up
---

## Notes

- Decide whether `run-checks.sh` should also validate the Pi extension TypeScript.
- Decide what level of testing is acceptable: structural Python tests, a smoke test, or manual validation only.
- Full interactive testing inside Pi has not been done.
