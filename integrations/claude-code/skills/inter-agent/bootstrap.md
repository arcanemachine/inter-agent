# inter-agent Claude Code bootstrap

Read this only for first-time setup, connect failures, or name-conflict edge
cases. Normal message handling lives in `SKILL.md`.

## Runtime wrapper

All skill commands call `<bin>/inter-agent-claude`, where `<bin>` is this
skill's absolute `bin/` directory. The wrapper finds the Python helper in this
order:

1. `INTER_AGENT_CLAUDE_HELPER`, an exact executable path for development or
   emergency override.
2. `CLAUDE_PLUGIN_OPTION_PROJECT_PATH`, injected from the installed plugin's
   `project_path` config, using
   `<project_path>/.venv/bin/inter-agent-claude`.
3. The Claude-managed runtime helper at
   `~/.claude/data/inter-agent/venv/bin/inter-agent-claude`.
4. `inter-agent-claude` on PATH.

If none exists, the wrapper prints a short setup-needed message and exits. Do
not guess alternate commands.

## Configure a local checkout

For development or a custom local core checkout, configure the installed plugin
`project_path` option to the checkout path, then prepare its venv:

```bash
cd /path/to/inter-agent
uv sync --locked
```

The wrapper expects this helper:

```text
/path/to/inter-agent/.venv/bin/inter-agent-claude
```

For one-off debugging, `INTER_AGENT_CLAUDE_HELPER=/path/to/inter-agent-claude`
overrides the plugin config.

## Managed runtime bootstrap

Bootstrap creates an isolated runtime venv at:

```text
~/.claude/data/inter-agent/venv
```

It installs the inter-agent Python package into that venv and does not change
the bus endpoint, token, or state directory. Claude, Pi, and other hosts still
use the normal inter-agent defaults unless explicitly configured otherwise:

```text
127.0.0.1:16837
platform inter-agent state directory
```

The current bootstrap source is the GitHub `main` archive:

```text
https://github.com/arcanemachine/inter-agent/archive/refs/heads/main.zip
```

This is a temporary pre-release install source. Future packaging work should
switch managed bootstrap to a stable PyPI release, tag, or pinned archive.

### Approval gate

Do not install anything silently. When setup is needed, tell the user:

- destination: `~/.claude/data/inter-agent/venv`;
- source: the GitHub archive above;
- requirement: Python 3.10+ with `venv` support;
- bus state: unchanged shared inter-agent defaults.

Ask for explicit approval. Only after the user approves, run:

```bash
<bin>/inter-agent-claude bootstrap --yes
```

The script requires `--yes`; without it, it exits with an approval-required
message.

### Failure messages

Keep user-facing failures short and point to runtime setup docs, for example:

```text
[inter-agent] setup failed: Python 3.10+ not found. See integrations/claude-code/README.md#runtime-setup
```

Common failures:

- Python 3.10+ is not installed or is not on PATH.
- Python exists but cannot create venvs.
- Network access to GitHub is unavailable.
- The install completes but `inter-agent-claude` is missing from the venv.

To reset or upgrade the managed runtime, remove the venv and bootstrap again:

```bash
rm -rf ~/.claude/data/inter-agent/venv
<bin>/inter-agent-claude bootstrap --yes
```

## Connect fallback

Try the persistent Monitor from `SKILL.md` first and wait for a connected line.
Do not use `status` or `list` as pre-checks.

Only if the **persistent** Monitor task exits without a connected or
already-connected line, run one fallback:

```bash
<bin>/inter-agent-claude status
```

- `connected=true` for your name: this session is already connected; stop.
- `connected=false`: connect again with a unique name.

## Name conflicts

The Claude listener retries one name conflict automatically:

```
[inter-agent] name "<name>" is already in use; retrying as "<name>-2".
```

Wait for the connected line under the retried name. If the retry also fails:

```
[inter-agent] name "<name>-2" is already in use after retry.
```

Then run `<bin>/inter-agent-claude list`, pick a unique name, and reconnect. If
a listener was killed with `kill -9` instead of `/inter-agent disconnect`, the
server may hold the name for up to ~40s; wait or choose another name.

## Persistent Monitor wrapper behavior

Empirically, Claude Code may render a persistent Monitor as two task entries: a
launcher wrapper that exits right after bootstrap (you may see `Monitor "..."
stream ended`) and the real persistent watch, which keeps running. That `stream
ended` line can arrive before the connected line.

Do not treat the wrapper exit as failure while the persistent task is still
running. Keep waiting for `[inter-agent] connected as "<name>"` or
`[inter-agent] already connected as "<name>"; no new listener started.` Only one
`inter-agent-claude listen` process actually runs.

Do not manually run `inter-agent-claude listen` in Bash; `/inter-agent connect`
starts the one Monitor listener, and a hand-started `listen` can race it and
steal the name.
