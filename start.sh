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
    exec "$ROOT/.venv/bin/python" -m inter_agent.core.server "$@"
    ;;
  connect)
    exec "$ROOT/.venv/bin/python" -m inter_agent.adapters.pi.cli connect "$@"
    ;;
  send)
    exec "$ROOT/.venv/bin/python" -m inter_agent.adapters.pi.cli send "$@"
    ;;
  broadcast)
    exec "$ROOT/.venv/bin/python" -m inter_agent.adapters.pi.cli broadcast "$@"
    ;;
  list)
    exec "$ROOT/.venv/bin/python" -m inter_agent.adapters.pi.cli list "$@"
    ;;
  status)
    exec "$ROOT/.venv/bin/python" -m inter_agent.adapters.pi.cli status "$@"
    ;;
  *)
    echo "Unknown command: $CMD"
    exit 2
    ;;
esac
