#!/usr/bin/env bash
# Exercise the combined stack with a synthetic connector; never contact Cloudflare.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
image=${1:?Pass locally built hosted image}
work=$(mktemp -d "${TMPDIR:-/tmp}/mcp-releem-stack.XXXXXXXX")
chmod 0755 "$work"
project=$(basename "$work" | tr '[:upper:].' '[:lower:]-')
compose() {
    docker compose -p "$project" --env-file "$work/hosted.env" \
        -f "$root/compose.yaml" -f "$work/connector.yaml" "$@"
}
cleanup() {
    compose down --timeout 10 >/dev/null
    rm -f "$work/hosted.env" "$work/connector.yaml" "$work/token"
    rmdir "$work"
}
trap cleanup EXIT
printf 'synthetic-not-a-cloudflare-token' > "$work/token"
chmod 0644 "$work/token"
cat > "$work/hosted.env" <<EOF
RELEEM_MCP_PUBLIC_URL=https://mcp.example.invalid/mcp
MCP_RELEEM_IMAGE=$image
MCP_RELEEM_HOST_PORT=0
COMPOSE_PROFILES=tunnel
RELEEM_MCP_TUNNEL_TOKEN_FILE=$work/token
EOF
cat > "$work/connector.yaml" <<EOF
services:
  cloudflared:
    image: $image
    entrypoint: [python, -u, -c]
    command:
      - |
        import time
        from http.client import HTTPConnection
        from pathlib import Path
        while True:
            if Path('/run/secrets/tunnel-token').read_text() == 'simulate-crash':
                raise RuntimeError('intentional synthetic connector crash')
            c = HTTPConnection('mcp', 8000, timeout=3)
            c.request('GET', '/healthz', headers={'Host': 'mcp.example.invalid'})
            assert c.getresponse().status == 200
            c.close()
            print('synthetic connector reached healthy MCP', flush=True)
            time.sleep(1)
EOF
# Without the optional profile only the application is selected.
test "$(COMPOSE_PROFILES='' compose config --services)" = mcp
export RELEEM_SECRET_KEY=synthetic-must-not-forward
compose config --quiet
compose up --detach --no-build --pull never --wait --wait-timeout 90
connector=$(compose ps --quiet cloudflared)
application=$(compose ps --quiet mcp)
test -n "$connector" && test -n "$application"
for container in "$connector" "$application"; do
    test "$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$container")" = unless-stopped
done
test "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$application")" = true
test "$(docker inspect --format '{{.Config.User}}' "$application")" = 65532:65532
test "$(docker inspect --format '{{(index (index .HostConfig.PortBindings "8000/tcp") 0).HostIp}}' "$application")" = 127.0.0.1
compose exec --no-TTY mcp python -c '
import os
from http.client import HTTPConnection
assert not any(name in os.environ for name in
    ("RELEEM_SECRET_KEY", "RELEEM_API_TOKEN", "RELEEM_API_TOKEN_FILE"))
c = HTTPConnection("127.0.0.1",8000,timeout=3)
c.request("POST","/mcp",body=b"{}",headers={"Host":"mcp.example.invalid"})
r = c.getresponse()
assert r.status == 401
c.close()
'
probe() {
    compose exec --no-TTY cloudflared python -c "
from http.client import HTTPConnection
c=HTTPConnection('mcp',8000,timeout=3)
c.request('GET','/healthz',headers={'Host':'mcp.example.invalid'})
assert c.getresponse().status == 200
"
}
probe
# A targeted application deployment must not recreate the connector.
compose up --detach --no-build --pull never --wait --wait-timeout 90 mcp
test "$(compose ps --quiet cloudflared)" = "$connector"
# Allow the restart-policy startup window, then trigger a natural service exit.
sleep 10
before=$(docker inspect -f '{{.RestartCount}}' "$connector")
printf 'simulate-crash' > "$work/token"
recovered=false
for _attempt in $(seq 1 60); do
    if test "$(docker inspect -f '{{.RestartCount}}' "$connector")" -gt "$before"; then
        recovered=true
        break
    fi
    sleep 1
done
printf 'synthetic-not-a-cloudflare-token' > "$work/token"
test "$recovered" = true
compose restart --timeout 40 mcp
wait_healthy() {
    for _attempt in $(seq 1 60); do
        if test "$(docker inspect -f '{{.State.Health.Status}}' "$application")" = healthy; then
            return 0
        fi
        sleep 1
    done
    printf 'Compose health deadline exceeded\n' >&2
    return 1
}
wait_healthy
# Kill the service child, not Docker's namespace-init process or another container.
before="$(docker inspect --format '{{.RestartCount}}' "$application")"
compose exec --no-TTY mcp python -c '
import os
import signal
from pathlib import Path
for path in Path("/proc").iterdir():
    if not path.name.isdigit():
        continue
    try:
        arguments = (path / "cmdline").read_bytes().split(b"\0")
    except (FileNotFoundError, PermissionError):
        continue
    if b"/opt/venv/bin/mcp-releem" in arguments:
        os.kill(int(path.name),signal.SIGKILL)
        break
else:
    raise SystemExit("Service process not found")
'
recovered=false
for _attempt in $(seq 1 60); do
  if test "$(docker inspect --format '{{.RestartCount}}' "$application")" -gt "$before"; then
    recovered=true
    break
  fi
  sleep 1
done
test "$recovered" = true
wait_healthy
connected=false
for _attempt in $(seq 1 60); do
    if probe >/dev/null 2>&1; then
        connected=true
        break
    fi
    sleep 1
done
test "$connected" = true
printf 'Compose smoke passed: private nonroot service, auth denial, DNS, connector/application crash recovery, manual restart and app-only update\n'
