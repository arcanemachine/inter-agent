#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

export UV_OFFLINE="${UV_OFFLINE:-1}"
export NPM_CONFIG_OFFLINE="${NPM_CONFIG_OFFLINE:-true}"

# Keep successful gates silent; replay their diagnostics only on failure.
check_tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$check_tmpdir"
}
trap cleanup EXIT

quiet_check() {
  local label="$1"
  shift
  local log status
  log="$(mktemp "$check_tmpdir/check.XXXXXX")"
  if "$@" >"$log" 2>&1; then
    rm -f "$log"
    return 0
  fi
  status=$?
  printf '[run-checks] %s failed:\n' "$label" >&2
  cat "$log" >&2
  rm -f "$log"
  return "$status"
}

quiet_check 'initial submodule validation' python3 scripts/check-submodules.py
quiet_check 'initial boundary validation' python3 scripts/validate-boundary.py
quiet_check 'installed acceptance' python3 scripts/run-installed-acceptance.py
quiet_check 'final submodule validation' python3 scripts/check-submodules.py
quiet_check 'final boundary validation' python3 scripts/validate-boundary.py

git diff --check
git diff --exit-code
status="$(git submodule status --recursive)"
test "$(printf '%s\n' "$status" | awk '$1 ~ /^[0-9a-f]{40}$/ && substr($0, 1, 1) == " " {count++} END {print count + 0}')" = 4
