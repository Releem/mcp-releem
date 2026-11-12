#!/bin/sh
# Run on the target with sudo. Only this Compose project is changed.
set -eu
mode=${1:?Use --dry-run or --apply}
image=${2:?Pass immutable image reference}
source_compose=${3:?Pass staged compose.yaml}
root=${MCP_DEPLOY_ROOT:-/opt/mcp-releem}
case "$mode" in --dry-run|--apply) ;; *) exit 2;; esac
if ! printf '%s\n' "$image" | grep -Eq '^(ghcr\.io/releem/releem-mcp-server@)?sha256:[a-f0-9]{64}$'; then
    printf 'An immutable approved image reference is required\n' >&2
    exit 2
fi
test -f "$source_compose"
case "$root" in /*) ;; *) exit 2;; esac
test "$root" != /
if test -e "$root" && ! test -f "$root/.managed-by-mcp-releem"; then
    printf 'Deployment directory is not managed by this application\n' >&2
    exit 2
fi
if test "$mode" = --dry-run; then
    printf 'Deploy %s to %s; public URL https://mcp.releem.com/mcp\n' "$image" "$root"
    printf 'Validate/pull image; start loopback Compose; verify health and 401; recover previous release on failure\n'
    exit 0
fi
umask 077
command -v docker >/dev/null
docker compose version >/dev/null
mkdir -p "$root/releases"
touch "$root/.managed-by-mcp-releem"
if ! mkdir "$root/deploy.lock"; then
    printf 'Deployment already in progress; inspect deploy.lock\n' >&2
    exit 1
fi
trap 'rmdir "$root/deploy.lock"' EXIT
previous=
if test -L "$root/current"; then previous=$(readlink -f "$root/current"); fi
release=$(mktemp -d "$root/releases/release.XXXXXXXX")
cp "$source_compose" "$release/compose.yaml"
cat > "$release/hosted.env" <<EOF
RELEEM_MCP_PUBLIC_URL=https://mcp.releem.com/mcp
RELEEM_API_BASE_URL=https://api2.dev.releem.com
MCP_RELEEM_IMAGE=$image
MCP_RELEEM_HOST_PORT=8000
RELEEM_MCP_SENSITIVE_DETAILS=false
EOF
if test -s "$root/secrets/tunnel-token"; then
    printf 'COMPOSE_PROFILES=tunnel\n' >> "$release/hosted.env"
fi
compose_at() {
    directory=$1
    shift
    docker compose --project-name mcp-releem --env-file "$directory/hosted.env" \
        --file "$directory/compose.yaml" "$@"
}
compose_at "$release" config --quiet
if test "${MCP_DEPLOY_OFFLINE:-false}" != true; then
    case "$image" in ghcr.io/*) docker pull "$image";; esac
fi
docker image inspect "$image" >/dev/null
verify_auth() {
    compose_at "$1" exec --no-TTY mcp python -c '
from http.client import HTTPConnection
c = HTTPConnection("127.0.0.1", 8000, timeout=5)
c.request("POST", "/mcp", body=b"{}", headers={"Host": "mcp.releem.com"})
assert c.getresponse().status == 401, "Expected unauthenticated 401"
c.close()
'
}
if compose_at "$release" up --detach --no-build --pull never --wait --wait-timeout 90 mcp &&
    verify_auth "$release"; then
    ln -s "$release" "$root/current.next"
    mv -Tf "$root/current.next" "$root/current"
    if test -n "$previous"; then
        ln -s "$previous" "$root/previous.next"
        mv -Tf "$root/previous.next" "$root/previous"
    fi
    printf 'Activated %s\n' "$image"
else
    printf 'Activation failed\n' >&2
    if test -n "$previous"; then
        if compose_at "$previous" up --detach --no-build --pull never --wait --wait-timeout 90 mcp &&
            verify_auth "$previous"; then
            printf 'Previous release recovered\n' >&2
        else
            printf 'ROLLBACK FAILED; operator intervention required\n' >&2
        fi
    else
        compose_at "$release" stop mcp
        printf 'First deployment failed; candidate stopped\n' >&2
    fi
    exit 1
fi
