#!/bin/sh
# Explicit apply flag; no credential or customer environment transfer.
set -eu
mode=${1:?Use --dry-run or --apply}
image=${2:?Pass GHCR image digest}
known_hosts=${DEPLOY_KNOWN_HOSTS_FILE:?Set verified known_hosts file}
key=${DEPLOY_SSH_KEY_FILE:?Set deployment key file}
case "$mode" in --dry-run|--apply) ;; *) exit 2;; esac
printf '%s\n' "$image" | grep -Eq '^ghcr\.io/releem/releem-mcp-server@sha256:[a-f0-9]{64}$'
root=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
ssh_run() {
    ssh -i "$key" -o BatchMode=yes -o IdentitiesOnly=yes -o ForwardAgent=no \
        -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$known_hosts" \
        -o ConnectTimeout=15 ubuntu@40.160.8.37 "$@"
}
# Expand uname on the target, never on the GitHub runner.
# shellcheck disable=SC2016
ssh_run 'set -e; sudo -n docker compose version; test "$(uname -m)" = x86_64'
if test "$mode" = --dry-run; then
    printf 'Transfer compose.yaml and activate.sh; deploy %s to ubuntu@40.160.8.37\n' "$image"
    exit 0
fi
staging=$(ssh_run 'mktemp -d /tmp/mcp-releem-upload.XXXXXXXX')
case "$staging" in /tmp/mcp-releem-upload.*) ;; *) exit 2;; esac
cleanup() {
    ssh_run "sudo -n rm -f $staging/registry/config.json; sudo -n rmdir $staging/registry; rm -f $staging/compose.yaml $staging/activate.sh $staging/recover.sh; rmdir $staging"
}
trap cleanup EXIT
scp -i "$key" -o BatchMode=yes -o IdentitiesOnly=yes -o ForwardAgent=no \
    -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$known_hosts" \
    "$root/compose.yaml" "$root/deploy/activate.sh" "$root/deploy/recover.sh" "ubuntu@40.160.8.37:$staging/"
ssh_run "sudo -n sh $staging/activate.sh --dry-run $image $staging/compose.yaml"
test -n "${GHCR_TOKEN:?Set ephemeral registry token}"
printf '%s\n' "${GHCR_USER:?Set registry user}" | grep -Eq '^[a-zA-Z0-9][a-zA-Z0-9-]{0,99}$'
ssh_run "sudo -n install -d -m 700 $staging/registry"
printf '%s' "$GHCR_TOKEN" | ssh_run "sudo -n env DOCKER_CONFIG=$staging/registry docker login ghcr.io -u $GHCR_USER --password-stdin"
ssh_run "sudo -n env DOCKER_CONFIG=$staging/registry sh $staging/activate.sh --apply $image $staging/compose.yaml"
if test "${DEPLOY_VERIFY_PUBLIC:-false}" = true; then
    if test "$(curl --silent --show-error --max-time 15 -o /dev/null -w '%{http_code}' https://mcp.releem.com/healthz)" = 200 &&
        test "$(curl --silent --show-error --max-time 15 -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' https://mcp.releem.com/mcp)" = 401; then
        printf 'HTTPS health and authentication denial passed\n'
    else
        printf 'Public verification failed; attempting previous application image\n' >&2
        ssh_run "sudo -n sh $staging/recover.sh $staging/activate.sh"
        exit 1
    fi
fi
