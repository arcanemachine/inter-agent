#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

# Pi's standalone child deliberately has no Node entry in .tool-versions.
# Keep the coordinated gate on the reviewed workspace Node line.
export ASDF_NODEJS_VERSION="${ASDF_NODEJS_VERSION:-24.16.0}"
export ASDF_PYTHON_VERSION="${ASDF_PYTHON_VERSION:-3.12.8}"
export ASDF_UV_VERSION="${ASDF_UV_VERSION:-0.10.4}"
export UV_OFFLINE="${UV_OFFLINE:-1}"
export NPM_CONFIG_OFFLINE="${NPM_CONFIG_OFFLINE:-true}"

python3 scripts/check-submodules.py
python3 scripts/validate-boundary.py
python3 scripts/run-installed-acceptance.py
python3 scripts/check-submodules.py
python3 scripts/validate-boundary.py

git diff --check
git diff --exit-code
git submodule status --recursive | grep -Eq '^[[:space:]][0-9a-f]{40} '
