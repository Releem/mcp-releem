#!/usr/bin/env bash
# Run on the server from a trusted terminal; token never enters shell history.
set -euo pipefail
mode=${1:?Use --dry-run or --apply}
root=/opt/mcp-releem
[[ "$mode" = --dry-run || "$mode" = --apply ]]
test -f "$root/.managed-by-mcp-releem"
test -f "$root/current/compose.yaml"
test -f "$root/current/hosted.env"
legacy=$(docker ps -aq --filter label=com.docker.compose.project=mcp-releem-tunnel)
if test -n "$legacy"; then
    printf 'Legacy tunnel project exists; migrate it before starting a duplicate connector\n' >&2
    exit 1
fi
printf 'Enable cloudflared in the existing mcp-releem stack; privately read token if absent; route to http://mcp:8000\n'
if test "$mode" = --dry-run; then exit 0; fi
test "$(id -u)" = 0
if ! mkdir "$root/deploy.lock"; then
    printf 'Deployment already in progress; inspect deploy.lock\n' >&2
    exit 1
fi
trap 'rmdir "$root/deploy.lock"' EXIT
install -d -m 0700 "$root/secrets"
token_file=$root/secrets/tunnel-token
if ! test -s "$token_file"; then
    umask 077
    read -r -s -p 'Cloudflare tunnel token: ' token </dev/tty
    printf '\n' >/dev/tty
    test -n "$token"
    printf '%s' "$token" > "$token_file"
    unset token
    chown 65532:65532 "$token_file"
    chmod 0400 "$token_file"
fi
compose() {
    docker compose -p mcp-releem --profile tunnel --env-file "$root/current/hosted.env" \
        -f "$root/current/compose.yaml" "$@"
}
compose config --quiet
compose pull cloudflared
compose up --detach --no-build --pull never --wait --wait-timeout 90
# Persist the profile only after startup succeeds; no token is stored in this file.
if ! grep -qx 'COMPOSE_PROFILES=tunnel' "$root/current/hosted.env"; then
    printf '\nCOMPOSE_PROFILES=tunnel\n' >> "$root/current/hosted.env"
fi
printf 'Connector started; verify Healthy in Cloudflare and then HTTPS /healthz and /mcp authentication\n'
