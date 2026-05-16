# Package Scaffold and Installation

Extra Phase: 8 — OpenCode Support

## Purpose

Create the OpenCode plugin package scaffold and install documentation so implementation can proceed inside a stable package layout.

## Scope

- Add a standalone npm package under `integrations/opencode/`.
- Configure separate OpenCode TUI and server plugin entry points.
- Add TypeScript build, typecheck, formatting, and package metadata.
- Document local development installation and eventual package installation.

## Package layout

Target layout:

```text
integrations/opencode/
  AGENTS.md
  README.md
  package.json
  tsconfig.json
  src/
    client.ts
    config.ts
    errors.ts
    format.ts
    identity.ts
    inbox.ts
    protocol.ts
    server.ts
    state.ts
    tui.ts
```

Expected module roles:

- `tui.ts` — OpenCode TUI plugin entry point.
- `server.ts` — OpenCode server plugin entry point and LLM tool registration.
- `client.ts` — shared direct WebSocket operations.
- `protocol.ts` — protocol envelope builders and parsers.
- `identity.ts` — token loading and server identity verification.
- `config.ts` — plugin settings and defaults.
- `state.ts` — active connection state persistence.
- `inbox.ts` — recent inbound message storage and truncation continuation records.
- `format.ts` — human-readable notification, toast, command, and tool output formatting.
- `errors.ts` — protocol and host error mapping.

## Work

1. Create `integrations/opencode/package.json`.
   - Use `type: "module"`.
   - Export separate target modules:
     - `./tui`
     - `./server`
   - Keep shared modules internal to the package.
   - Declare runtime dependencies only when needed.
   - Use OpenCode plugin peer or dev dependencies consistently with OpenCode examples.

2. Ensure the package does not default-export both server and TUI from one module.
   - OpenCode rejects a single module that exports both targets.
   - `./tui` and `./server` must resolve to target-specific modules.

3. Add TypeScript configuration.
   - Use module settings compatible with OpenCode's Bun/ESM runtime.
   - Enable strict type checking unless the current OpenCode plugin types force narrower settings.
   - Keep emitted files in `dist/`.

4. Add package scripts.
   - `typecheck`
   - `build`
   - `format`
   - Add `test` only after there are meaningful tests.

5. Add `integrations/opencode/AGENTS.md`.
   - Include local package checks.
   - State that changes to behavior require README updates.
   - State that package exports must remain split by OpenCode target.

6. Add `integrations/opencode/README.md`.
   - Explain install, configuration, connect, send, receive, disconnect, and troubleshooting.
   - Mark the package as planned or experimental until live validation is complete.

7. Document local development installation.
   - Use OpenCode's plugin install flow with a local `file://` path if supported by the current OpenCode version.
   - Include separate notes for TUI and server plugin activation if OpenCode stores them in different config files.

8. Document production installation shape.
   - If package publishing is desired later, keep package metadata ready for an npm package.
   - Do not publish as part of this phase unless explicitly requested.

9. Add a minimal placeholder implementation only after the package metadata is correct.
   - The placeholder TUI plugin should load and dispose cleanly.
   - The placeholder server plugin should load without registering tools until the tool surface is implemented.

10. Add packaging checks to the root quality gate only after the package can pass consistently.

## Acceptance criteria

- `integrations/opencode/` contains a valid standalone npm package.
- OpenCode can resolve `./tui` and `./server` entry points separately.
- The package can be installed locally into OpenCode without project-local absolute paths baked into source files.
- Placeholder entry points load without starting network listeners or mutating inter-agent state.
- `npm run typecheck` and `npm run build` pass inside `integrations/opencode/`.
- The README documents local development install and uninstall steps.

## Files likely to change

- `integrations/opencode/package.json`
- `integrations/opencode/tsconfig.json`
- `integrations/opencode/AGENTS.md`
- `integrations/opencode/README.md`
- `integrations/opencode/src/tui.ts`
- `integrations/opencode/src/server.ts`
- `README.md`

## Checks

```bash
cd integrations/opencode
npm run typecheck
npm run build
npm run format
```

Run the root gate before completing the phase:

```bash
./run-checks.sh
```
