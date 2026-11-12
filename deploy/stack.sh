#!/bin/sh
# Stable operator entrypoint to the currently selected release, both services.
set -eu
root=${MCP_DEPLOY_ROOT:-/opt/mcp-releem}
test -f "$root/.managed-by-mcp-releem"
test -f "$root/current/compose.yaml"
test -f "$root/current/hosted.env"
exec docker compose --project-name mcp-releem --env-file "$root/current/hosted.env" \
    --file "$root/current/compose.yaml" "$@"
