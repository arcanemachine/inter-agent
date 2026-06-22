# inter-agent Claude Code bootstrap

Read this only for first-time setup, connect failures, or name-conflict edge
cases. Normal message handling lives in `SKILL.md`.

## Install `inter-agent-claude`

`inter-agent-claude` must be on PATH. Replace `<path-to-inter-agent>` with the
inter-agent checkout.

Use an already-installed isolated Python CLI installer; do **not** install
`pipx` or `uv` yourself.

1. If `pipx` exists:

   ```bash
   pipx install -e <path-to-inter-agent>
   inter-agent-claude status
   ```

2. Else if `uv` exists:

   ```bash
   uv tool install --from <path-to-inter-agent> .
   inter-agent-claude status
   ```

3. Else stop and tell the user no supported installer is available. Suggest one
   of these user-run installs, then retry:

   ```bash
   brew install pipx        # macOS/Homebrew
   pip install --user pipx  # user Python, if allowed
   brew install uv          # macOS/Homebrew
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

Why: `pip install -e <path>` against system/Homebrew Python can fail with PEP
668 `externally-managed-environment`. `pipx` and `uv tool install` create an
isolated tool environment and put `inter-agent-claude` on PATH.

## Connect fallback

Try the persistent Monitor from `SKILL.md` first and wait for a connected line.
Do not use `status` or `list` as pre-checks.

Only if the **persistent** Monitor task exits without a connected or
already-connected line, run one fallback:

```bash
inter-agent-claude status
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

Then run `inter-agent-claude list`, pick a unique name, and reconnect. If a
listener was killed with `kill -9` instead of `/inter-agent disconnect`, the
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
