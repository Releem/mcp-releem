#!/bin/sh
# Run on the target with sudo. Only this Compose project is changed.
set -eu
mode=${1:?Use --dry-run or --apply}
image=${2:?Pass immutable image reference}
source_compose=${3:?Pass staged compose.yaml}
root=${MCP_DEPLOY_ROOT:-/opt/mcp-releem}
case "$mode" in --dry-run|--apply) ;; *) exit 2;; esac
case "$#" in
    3) source_env=;;
    4) source_env=${4:?Pass saved hosted.env};;
    *) exit 2;;
esac
if ! printf '%s\n' "$image" | grep -Eq '^(ghcr\.io/releem/releem-mcp-server@)?sha256:[a-f0-9]{64}$'; then
    printf 'An immutable approved image reference is required\n' >&2
    exit 2
fi
case "$root" in /*) ;; *) exit 2;; esac
test "$root" != /
if { test -e "$root" || test -n "$source_env"; } && ! test -f "$root/.managed-by-mcp-releem"; then
    printf 'Deployment directory is not managed by this application\n' >&2
    exit 2
fi
read_saved_setting() {
    # Require literal single-line assignments so Compose cannot reinterpret a setting.
    awk -v key="$1" '
        /^[[:space:]]*($|#)/ { next }
        !/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]#$"\\\047]*$/ { invalid = 1; next }
        index($0, key "=") == 1 {
            count++
            value = substr($0, length(key) + 2)
        }
        END {
            if (invalid || count != 1 || value == "") exit 1
            print value
        }
    ' "$source_env"
}
validate_recovery() {
    if ! test -L "$root/previous" || ! saved_release=$(readlink -f "$root/previous") ||
        ! releases=$(readlink -f "$root/releases") ||
        test "${saved_release%/*}" != "$releases" ||
        ! test -f "$source_env" || ! test -f "$source_compose" ||
        test "$(readlink -f "$source_env")" != "$saved_release/hosted.env" ||
        test "$(readlink -f "$source_compose")" != "$saved_release/compose.yaml"; then
        printf 'Recovery requires the saved hosted.env and compose.yaml from the managed previous release\n' >&2
        exit 2
    fi
    source_env=$saved_release/hosted.env
    source_compose=$saved_release/compose.yaml
    if ! saved_image=$(read_saved_setting MCP_RELEEM_IMAGE) || test "$saved_image" != "$image"; then
        printf 'Saved hosted.env must specify the requested immutable image once\n' >&2
        exit 2
    fi
    saved_upstream=$(read_saved_setting RELEEM_API_BASE_URL) || saved_upstream=
    case "$saved_upstream" in
        https://?*) ;;
        *) printf 'Saved hosted.env must specify a literal HTTPS API origin once\n' >&2; exit 2;;
    esac
}
if test -z "$source_env"; then
    test -f "$source_compose"
fi
if test "$mode" = --dry-run; then
    if test -n "$source_env"; then validate_recovery; fi
    printf 'Deploy %s to %s; public URL https://mcp.releem.com/mcp\n' "$image" "$root"
    printf 'Validate image; start loopback Compose; verify health and 401; recover previous release on failure\n'
    exit 0
fi
umask 077
command -v docker >/dev/null
docker compose version >/dev/null
if test -z "$source_env"; then
    mkdir -p "$root/releases"
    touch "$root/.managed-by-mcp-releem"
fi
if ! mkdir "$root/deploy.lock"; then
    printf 'Deployment already in progress; inspect deploy.lock\n' >&2
    exit 1
fi
trap 'rmdir "$root/deploy.lock"' EXIT
if test -n "$source_env"; then validate_recovery; fi
previous=
if test -L "$root/current"; then previous=$(readlink -f "$root/current"); fi
release=$(mktemp -d "$root/releases/release.XXXXXXXX")
cp "$source_compose" "$release/compose.yaml"
if test -n "$source_env"; then
    # The connector profile follows the installed token, independently of the saved application settings.
    awk '!/^COMPOSE_PROFILES=/' "$source_env" > "$release/hosted.env"
else
    cat > "$release/hosted.env" <<EOF
RELEEM_MCP_PUBLIC_URL=https://mcp.releem.com/mcp
RELEEM_API_BASE_URL=https://api2.releem.com
MCP_RELEEM_IMAGE=$image
MCP_RELEEM_HOST_PORT=8000
RELEEM_MCP_SENSITIVE_DETAILS=false
EOF
fi
if test -s "$root/secrets/tunnel-token"; then
    printf 'COMPOSE_PROFILES=tunnel\n' >> "$release/hosted.env"
fi
compose_at() (
    directory=$1
    shift
    # Compose gives the caller's environment precedence over the release's --env-file.
    unset COMPOSE_PROFILES MCP_RELEEM_IMAGE MCP_RELEEM_HOST_PORT RELEEM_API_BASE_URL \
        RELEEM_MCP_PUBLIC_URL RELEEM_MCP_SENSITIVE_DETAILS RELEEM_MCP_MAX_OUTPUT_BYTES \
        RELEEM_MCP_REQUESTS_PER_MINUTE RELEEM_MCP_MAX_CONCURRENT_REQUESTS \
        RELEEM_MCP_PER_KEY_CONCURRENCY RELEEM_MCP_TUNNEL_TOKEN_FILE
    docker compose --project-name mcp-releem --env-file "$directory/hosted.env" \
        --file "$directory/compose.yaml" "$@"
)
compose_at "$release" config --quiet
if test -z "$source_env" && test "${MCP_DEPLOY_OFFLINE:-false}" != true; then
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
