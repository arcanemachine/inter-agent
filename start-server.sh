#!/usr/bin/env bash
# A quickstart script to start the inter-agent server

set -e

exec uv run inter-agent-server "$@"
