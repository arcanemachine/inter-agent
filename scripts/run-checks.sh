#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

python3 scripts/check-submodules.py
python3 scripts/validate-boundary.py

(
  cd core
  ./run-checks.sh
)
(
  cd extensions/pi
  scripts/run-checks.sh
)
(
  cd extensions/claude-code
  scripts/run-checks.sh
)

python3 scripts/run-installed-acceptance.py
python3 scripts/validate-boundary.py

git diff --check
git diff --exit-code
git submodule status --recursive | grep -Eq '^[[:space:]][0-9a-f]{40} '
