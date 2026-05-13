# Todo

Items from this list should be addressed as soon as possible.

> Using OpenCode Go with Claude Code
>
> Start the proxy: OC_GO_CC_API_KEY=sk-your-opencode-go-api-key /workspace/local/bin/oc-go-cc_linux-amd64 serve
>
> Start Claude Code: ANTHROPIC_BASE_URL=http://127.0.0.1:3456 ANTHROPIC_AUTH_TOKEN=unused claude --model kimi-k2.6 --plugin-dir /workspace/projects/inter-agent/integrations/claude-code/

## Misc

- Ensure README instructions are up-to-date - Include server setup and usage instructions before running the extension

## Integrations - Claude Code

- Agents keep getting confused and sending messages back to "control". This should be fixed (was also handled in Pi)

- Add auto-complete for the inter-agent commands. (This has been implemented in claude-code-inter-session)
