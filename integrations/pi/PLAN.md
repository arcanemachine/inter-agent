# pi-inter-agent Extension Plan

## Goal
Create a Pi coding agent extension that connects to the inter-agent message bus, allowing Pi sessions to send, broadcast, list, check status, connect, and disconnect through documented commands.

## Design Decisions

1. **Entry point resolution**: Use `uv run inter-agent-pi ...` and `uv run inter-agent-connect ...` (slower but reliable, per user instruction).
2. **Notification truncation**: 1000 character limit for `ctx.ui.notify()`.
3. **File placement**: Part of the inter-agent monorepo under `integrations/pi/`.
4. **Testing**: Structural tests + live smoke test.

## Tasks

### Phase 1: Project Scaffold
- [x] Create `package.json` with proper metadata, scripts, and `pi` config
- [x] Create `tsconfig.json`
- [x] Create `.gitignore`
- [x] Create `AGENTS.md`
- [x] Initialize git repo and first commit

### Phase 2: Core Extension Implementation
- [x] Create `src/index.ts` with:
  - Background listener via `uv run inter-agent-connect`
  - JSON line parsing from stdout
  - Notification delivery with 1000-char truncation
  - Session state persistence via `pi.appendEntry()`
  - Cleanup on `session_shutdown`
- [x] Register commands: `/inter-agent-connect`, `/inter-agent-disconnect`, `/inter-agent-send`, `/inter-agent-broadcast`, `/inter-agent-list`, `/inter-agent-status`, `/inter-agent-shutdown`
- [x] Register tools: `inter_agent_send`, `inter_agent_broadcast`, `inter_agent_list`, `inter_agent_status`

### Phase 3: Documentation
- [x] Create `README.md` with installation, configuration, and usage
- [x] Document commands and tools
- [ ] Document settings.json configuration options (not applicable — no settings needed)

### Phase 4: Quality Assurance
- [x] Run `npm run typecheck`
- [x] Manually test the extension with `pi -e ./src/index.ts`
- [x] Verify listener spawn and message delivery against a running inter-agent server
- [x] Commit final changes

## Completion Criteria
- Extension loads without errors in Pi
- All commands function correctly against a live inter-agent server
- Incoming messages are delivered as Pi notifications
- State persists across Pi reloads
- Documentation is complete and accurate
