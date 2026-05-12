#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ $# -lt 1 ]]; then
  echo "Usage: ./start.sh <server|connect|send|broadcast|list|status|shutdown> [args...]"
  exit 2
fi

CMD="$1"
shift

case "$CMD" in
  server)
    exec uv run inter-agent-server "$@"
    ;;
  connect)
    exec uv run inter-agent-pi connect "$@"
    ;;
  send)
    exec uv run inter-agent-pi send "$@"
    ;;
  broadcast)
    exec uv run inter-agent-pi broadcast "$@"
    ;;
  list)
    exec uv run inter-agent-pi list "$@"
    ;;
  status)
    exec uv run inter-agent-pi status "$@"
    ;;
  shutdown)
    exec uv run inter-agent-pi shutdown "$@"
    ;;
  *)
    echo "Unknown command: $CMD"
    exit 2
    ;;
esac
