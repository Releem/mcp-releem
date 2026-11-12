# Start and manage the hosted service with Compose

For the `mcp.releem.com` server, GitHub automation and named-tunnel setup, see
[GitHub deployment](github-deployment.md). The commands below remain the local
Compose operating reference.

One Compose project contains the MCP application and an optional cloudflared
connector (`tunnel` profile). The connector reaches `http://mcp:8000` through the
private Docker network; the host application port remains127.0.0.1-only. Install
its token and enable the profile using the [setup helper](github-deployment.md).
These commands do not create Cloudflare DNS/tunnel resources or deploy remotely.
Preserve the public Host header and the customer's Authorization header. Do not
apply browser challenge/login pages or caching to `/mcp`.

## Prepare

Requires Docker Engine and Docker Compose v2 with `up --wait` support (tested with
Compose5.0.2 locally and5.7.1 on the target). Native ARM64 and AMD64 have release
receipts; use the image verified for the target architecture. See the
[AMD64 server receipt](releases/evidence/2026-11-12-server-deployment.json).
Enable Docker startup at boot through the host's service management.

From the checkout root:

```bash
cp deploy/hosted.env.example deploy/hosted.env
```

Edit `deploy/hosted.env` to set the actual public HTTPS `/mcp` URL and unused local
port. This ignored file holds administrator settings only. Do not add customer
keys: clients supply them per request. Compose deliberately passes only named
administrator settings, without forwarding `.env`, shell customer tokens or an
entire environment file into the service. The local stdio `.env` stays separate.

Build a development candidate and validate configuration without starting:

```bash
docker compose --env-file deploy/hosted.env config --quiet
docker compose --env-file deploy/hosted.env build mcp
docker compose --env-file deploy/hosted.env run --rm --no-deps mcp --check
```

The environment file's default `mcp-releem:hosted` tag is for this source build.
For deployment use the exact reviewed image ID/digest in `MCP_RELEEM_IMAGE`,
load/pull it first, skip `build`, and use `up --no-build --pull never` below.
Do not build over an immutable image reference. No registry publication is implied.

## Start, inspect and restart

```bash
# Start in background and wait for liveness.
docker compose --env-file deploy/hosted.env up -d --no-build --pull never --wait --wait-timeout 90

# Show state and recent application logs.
docker compose --env-file deploy/hosted.env ps
docker compose --env-file deploy/hosted.env logs --tail 50 mcp

# Restart the existing container using its current image/configuration.
docker compose --env-file deploy/hosted.env restart mcp
```

After changing environment, image or Compose settings, run `up` again to apply the
changes; `restart` does not apply new configuration. Force recreation when needed:

```bash
docker compose --env-file deploy/hosted.env up -d --no-build --pull never --force-recreate --wait --wait-timeout 90
```

[`restart` behavior](https://docs.docker.com/reference/cli/docker/compose/restart/).
`restart: unless-stopped` restarts exited containers and running containers after
a Docker restart. A deliberately stopped service remains stopped. Docker must be
enabled/running on the host; this file does not configure the host service.
[Docker restart policies](https://docs.docker.com/engine/containers/start-containers-automatically/).

Health checks contact only local `/healthz`, with the configured public Host. They
require no API key, do not query Releem and report liveness rather than customer/API
readiness. An unhealthy process is **not** restarted merely because health checks
fail: alert/inspect and use `restart`. No Docker-socket-mounted autoheal component
is included. In-flight calls can fail during restart; clients must reconnect.

## Security and operating limits

- Host port binds only127.0.0.1. The plaintext backend must not be exposed publicly.
  Cloudflared shares the private Compose network and addresses `mcp:8000`, with no
  host networking or published connector port. Its sole host mount is the token
  file, read-only, with automatic source-path creation disabled.
- UID/GID65532, read-only root filesystem, writable16MiB ephemeral `/tmp`, no Linux
  capabilities, no-new-privileges and an init process. No host source, key or Docker
  socket mounts. Defaults1 CPU/256MiB memory/64 PIDs are pilot limits, not capacity
  guarantees; measure before increasing request concurrency.
- Application logs rotate at10MiB with3 files. Audit the ingress logging policy
  separately; never log Authorization, request bodies, SQL or customer payloads.
- One application container/worker preserves process-local quotas; the optional
  second container only provides the tunnel.
  Do not scale replicas without ingress-wide admission controls.
- Docker networking does not restrict arbitrary outbound destinations by itself.
  Enforce approved API/proxy egress on the host/network. Custom enterprise CA/proxy
  use requires an explicit reviewed Compose override with read-only CA mounts and
  administrator settings; this minimal profile does not mount them automatically.

[`Compose service configuration`](https://docs.docker.com/reference/compose-file/services/).

## Stop and roll back

```bash
# Stop without removing; start again with up.
docker compose --env-file deploy/hosted.env stop mcp

# Remove this project's container/network; no persistent application volumes exist.
docker compose --env-file deploy/hosted.env down
```

Keep the previous reviewed image and administrator configuration. To roll back,
restore `MCP_RELEEM_IMAGE` and matching settings, then `up --force-recreate --wait`.
Recheck liveness, authentication and a bounded diagnostic. No automatic rollback,
credential revocation, image pruning or unrelated service restart occurs.

## Local verification

`bash scripts/check-release.sh` now includes the Compose lifecycle smoke against
its freshly built hosted image. It starts a unique temporary project with a random
loopback port and placeholder URL, tests health and unauthenticated401, manual
restart and recovery after unexpected service-process exit, and removes only its
own project. No customer API request or Cloudflare connection is made. Its receipt
is saved in the checksummed candidate directory as `compose-smoke.log`.
For a focused repeat: `bash tools/release/compose_smoke.sh <LOCAL_HOSTED_IMAGE>`.
The same smoke uses a synthetic connector in the same project to
verify Docker service DNS, startup health ordering, connector crash recovery, MCP
restart and app-only updates without Cloudflare/customer calls. It does not prove
actual tunnel authentication, public streaming or real host reboot recovery.
Remote HTTPS, real customer revocation/isolation and client onboarding remain gates.

## Runtime base

The current image uses pinned Python3.12/Alpine3.24 with musl native wheels and
fixed stable OS package versions. SQLite is intentionally absent from this Docker
runtime; the HTTP adapter does not need it. Standard package installations retain
their own Python stdlib. See [security rationale](decisions/0003-hardened-runtime.md).
