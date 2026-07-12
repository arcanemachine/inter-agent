# Packaging, Docs, and Quality Gate

Prospective roadmap item — OpenCode Support

## Purpose

Make OpenCode support installable, documented, and included in the repository's completion checks once the implementation is stable.

## Scope

- OpenCode package metadata and built artifact policy.
- Root documentation updates.
- Security and architecture documentation updates where needed.
- Quality-gate integration.
- Release validation notes.

## Work

1. Finalize package metadata.
   - Confirm package name.
   - Confirm files allowlist.
   - Confirm exports for `./tui` and `./server`.
   - Confirm runtime dependencies are minimal.
   - Confirm dev dependencies are not published as runtime dependencies.

2. Finalize install documentation.
   - Local development install.
   - User install path.
   - Enabling both TUI and server plugin targets.
   - Uninstall and disable instructions.
   - Version compatibility notes for OpenCode.

3. Finalize configuration documentation.
   - Host and port.
   - Data directory.
   - Connection name and label.
   - Notification length.
   - Inbox length.
   - Auto-connect setting.
   - Server lifecycle policy: whether the server must already be running or whether an accepted auto-start path exists.
   - Whether inbound messages are human-visible only or also model-visible, and how the model can inspect pending messages.
   - Troubleshooting for token, identity metadata, server not running, duplicate names, state collisions, and plugin load errors.

4. Update root `README.md`.
   - List OpenCode as supported only after implementation and validation are complete.
   - While OpenCode is prospective, keep it out of the supported integration list and point interested contributors to `ROADMAP.md` instead.
   - Remove language that implies plugin-only Codex extension support is planned.
   - State prominently that Codex plugin-only extension surfaces do not expose the background delivery/control surface required for inter-agent parity. Future Codex work should follow the separate App Server sidecar direction documented in `integrations/codex/README.md`.

5. Update `ARCHITECTURE.md` if needed.
   - Add OpenCode to the host integration layer only after implementation exists.
   - Explain direct TypeScript WebSocket client as an allowed integration strategy.
   - Keep core protocol unchanged.

6. Update `SECURITY.md` if needed.
   - Document OpenCode plugin trust assumptions.
   - Document fallback token-file and TLS certificate access from a Bun plugin.
   - Document challenge-response server proof verification and any accepted degraded behavior.
   - Document notification and inbox privacy implications.

7. Update planning docs.
   - Remove completed OpenCode work from `.agents/PLAN.md` when the active slice is done.
   - Update `ROADMAP.md` with implementation status and any remaining follow-on work.
   - State completion criteria.
   - State the Codex plugin-only extension non-goal and point to the App Server sidecar direction.

8. Update `docs/IDEAS.md` if needed.
   - Move OpenCode-only ideas into `ROADMAP.md` only after user acceptance.
   - Copy only active OpenCode work slices into `.agents/PLAN.md`.
   - Keep Codex App Server sidecar direction aligned with `ROADMAP.md` and `integrations/codex/README.md`.

9. Integrate checks.
   - Add stable OpenCode checks to `run-checks.sh`.
   - Keep interactive OpenCode UAT outside the required gate unless it becomes reliable and headless.
   - Document manual checks clearly.

10. Validate packaging.
   - Ensure built package contains only expected files.
   - Ensure local install works from a clean checkout.
   - Ensure docs do not embed machine-specific paths.

## Acceptance criteria

- OpenCode install, configuration, commands, tools, receive behavior, disconnect, and troubleshooting are documented.
- Root docs no longer imply that plugin-only Codex extension support is planned.
- Security docs describe OpenCode-specific trust and token-access assumptions.
- Root quality gate includes OpenCode checks once stable.
- Manual UAT has been run and recorded in the handoff or completion note.
- Repository checks pass.

## Files likely to change

- `integrations/opencode/README.md`
- `integrations/opencode/package.json`
- `README.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `.agents/PLAN.md`
- `ROADMAP.md`
- `docs/IDEAS.md`
- `run-checks.sh`
- Release validation scripts if package assets are included in release artifacts

## Checks

```bash
cd integrations/opencode
npm run typecheck
npm run build
npm run format
npm test  # after a test script exists
```

Root checks:

```bash
./run-checks.sh
```
