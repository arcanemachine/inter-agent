#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

export UV_OFFLINE="${UV_OFFLINE:-1}"
export NPM_CONFIG_OFFLINE="${NPM_CONFIG_OFFLINE:-true}"

python3 scripts/check-submodules.py
python3 scripts/validate-boundary.py
python3 scripts/run-installed-acceptance.py
python3 scripts/check-submodules.py
python3 scripts/validate-boundary.py

git diff --check
git diff --exit-code
status="$(git submodule status --recursive)"
test "$(printf '%s\n' "$status" | awk '$1 ~ /^[0-9a-f]{40}$/ && substr($0, 1, 1) == " " {count++} END {print count + 0}')" = 4
