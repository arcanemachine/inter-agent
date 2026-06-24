# Todo

Items from this list should be addressed as soon as possible.

> Using OpenCode Go with Claude Code
>
> Start the proxy: OC_GO_CC_API_KEY=sk-your-opencode-go-api-key /workspace/local/bin/oc-go-cc_linux-amd64 serve
>
> Start Claude Code: ANTHROPIC_BASE_URL=http://127.0.0.1:3456 ANTHROPIC_AUTH_TOKEN=unused claude --model kimi-k2.6 --plugin-dir /workspace/projects/inter-agent/integrations/claude-code/

## User-specified items (these are top priority items)

- Immediate: work `plans/09-host-extension-packaging/00-execution-guide.md` next. Start with a focused user discussion to settle the Claude Code and Pi installability/setup model, then prove Claude persistent plugin installation before broader repository/package split work. Do not let this get buried behind other follow-on integration tasks unless the user explicitly redirects.

- Add the Claude Code and Pi extensions to the appropriate distribution/discovery areas, such as Claude Code plugins, npm/package registries, and the Pi packages page.

- Improve README.md references:
  - Pi extension location inaccurate (is now part of this repo)

- Implement a local install layout and path handling for app files vs. state:
  - Linux: app files in `~/.local/share/inter-agent`, runtime state in `~/.local/state/inter-agent`, optional config in `~/.config/inter-agent/config.json`.
  - macOS: app files in `~/Library/Application Support/inter-agent/app`, runtime state in `~/Library/Application Support/inter-agent/state`, optional config at `~/Library/Application Support/inter-agent/config.json`.
  - Pi should use platform-appropriate default `projectPath` values and expand `~`, `$VAR`, and `${VAR}` for path-like settings such as `projectPath` and `dataDir`.

## Misc

- Ensure README instructions are up-to-date - Include server setup and usage instructions before running the extension

## Integrations - Claude Code

- Add auto-complete for the inter-agent commands. (This has been implemented in [claude-code-inter-session](https://github.com/yilunzhang/claude-code-inter-session))
  - NOTE: Not sure if this still needs to be done. Worth a double-check.

