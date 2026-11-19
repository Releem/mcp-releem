#!/bin/sh
# Public-check recovery uses the already verified cached previous image.
set -eu
activation=${1:?Pass activate.sh}
root=${MCP_DEPLOY_ROOT:-/opt/mcp-releem}
if test -L "$root/previous"; then
    previous=$(readlink -f "$root/previous")
    saved_env=$previous/hosted.env
    if ! test -f "$saved_env"; then
        printf 'Previous release is missing its saved hosted.env\n' >&2
        exit 2
    fi
    image=$(sed -n 's/^MCP_RELEEM_IMAGE=//p' "$saved_env")
    sh "$activation" --apply "$image" "$previous/compose.yaml" "$saved_env"
else
    current=$(readlink -f "$root/current")
    docker compose --project-name mcp-releem --env-file "$current/hosted.env" \
        --file "$current/compose.yaml" stop mcp
    printf 'First release stopped after public verification failure\n'
fi
