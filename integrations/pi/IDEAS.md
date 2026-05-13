# Ideas

- Have the harness check if the inter-agent server is already running. If not, then start it.
- Add tests. The repo currently only has `npm run typecheck`. Add unit tests for config loading, script path resolution, and message parsing. Consider integration tests that spin up a real inter-agent server and verify commands end-to-end.
- Convert slash command syntax: e.g. `/inter-agent-connect` -> `/inter-agent connect`
