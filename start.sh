#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: ./start.sh <server|connect|send|broadcast|list|status> [args...]"
  exit 2
fi

CMD="$1"
shift

case "$CMD" in
  server)
    exec "$ROOT/.venv/bin/python" "$ROOT/core/server.py" "$@"
    ;;
  connect)
    exec "$ROOT/.venv/bin/python" "$ROOT/adapters/pi/cli.py" connect "$@"
    ;;
  send)
    exec "$ROOT/.venv/bin/python" "$ROOT/adapters/pi/cli.py" send "$@"
    ;;
  broadcast)
    exec "$ROOT/.venv/bin/python" "$ROOT/adapters/pi/cli.py" broadcast "$@"
    ;;
  list)
    exec "$ROOT/.venv/bin/python" "$ROOT/adapters/pi/cli.py" list "$@"
    ;;
  status)
    exec "$ROOT/.venv/bin/python" "$ROOT/adapters/pi/cli.py" status "$@"
    ;;
  *)
    echo "Unknown command: $CMD"
    exit 2
    ;;
esac
