#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PATH="$HOME/.asdf/shims:$HOME/.asdf/bin:$PATH"

run() {
  printf '\n==> %s\n' "$*"
  "$@"
}

run uv sync --locked
run uv run pytest
run uv run ruff check .
run uv run black --check .
run uv run mypy src tests
