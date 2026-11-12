# Automated SSH deployment and Cloudflare Tunnel

The later [unified-stack plan](../superpowers/plans/2026-11-12-unified-compose.md)
supersedes this document's separate-project/host-network connector design. Current
operation uses one project/private service DNS and route `http://mcp:8000`.

Status: owner approved and implementation delivered2026-11-12. The later
[GitHub implementation plan](../superpowers/plans/2026-11-12-github-deployment.md)
selects GHCR for repeat deployments, superseding archive transfer below. Initial
bootstrap used a native verified source export without publishing. SSH user is
ubuntu with sudo (server rejects root login). See [current setup](../github-deployment.md).
Target authorized by owner: `root@40.160.8.37`, using a passphrase-protected
SSH key unlocked locally. No passphrase storage or unattended key decryption.

## Recommended approach

Reuse the existing Docker Compose hosted profile and distribute a verified image
archive over SSH. Run a digest-pinned cloudflared container with host networking
on the Linux target, connecting a remotely managed named tunnel to the existing
loopback-only `http://127.0.0.1:8000` backend. This preserves the current Compose
network boundary without publishing the application port externally. The tunnel
has no inbound published ports and needs no Docker socket or privileged mode.

Alternative: install cloudflared as a host service. This fits the existing runbook
but adds a separately managed host package. A registry-based deployment can be
added later if an approved registry and publication workflow are selected; it is
not needed for this single-host pilot. Quick Tunnels are unsuitable for the stable
endpoint and streaming requirement.

## Automation contract

- Provide explicit preflight/dry-run and apply modes; dry-run performs only reads
  and prints a redacted mutation plan. Do not claim remote APIs support native
  dry-run when they do not. Remote API writes follow a reviewed dry-run.
- Authenticate through ssh-agent with strict host-key checking, no agent
  forwarding, no password injection, and no private-key transfer. A trusted host
  fingerprint is required before accepting an initially unknown host key.
- Preflight OS/architecture, Docker Engine/Compose availability, disk capacity,
  free loopback port, existing deployment ownership and Cloudflare route conflicts.
  Do not install host packages automatically. Inspect before changing any service.
- Use a dedicated `/opt/mcp-releem` directory and fixed Compose project name.
  Transfer only allowlisted deployment files and checksum-verified image artifacts;
  never rsync the checkout, `.env`, client configuration or private backup.
- Build/test an image for the actual target architecture. Prior ARM64 receipts
  do not qualify an AMD64 target. Keep the existing locked dependency, format/lint,
  typecheck, offline test, build, transport and Compose lifecycle checks. Run the
  explicitly requested public-advisory security gate before release activation.
- Use immutable image IDs/digests and retain the previous image and matching admin
  configuration. Start with `up --no-build --pull never --wait`; on activation
  failure restore the previous application configuration and verify recovery.
  First deployment failure leaves a clear failed state, not fabricated rollback.
- Manage cloudflared under Compose with `unless-stopped`, resource/log bounds,
  a read-only filesystem and only its necessary credential-file mount. Verify
  token-file support and file permissions against the selected pinned image.
  Tunnel tokens must never appear in command arguments, logs, repository files,
  tool output or application environment. Transfer credentials through a protected
  local-to-remote channel, independently of customer Releem API keys.
- Create/reuse only the selected named tunnel and exact DNS hostname. Reject
  conflicting existing records/routes rather than replacing them. Route the
  public hostname to the loopback origin with an explicit matching HTTP Host,
  preserve Authorization and streaming, and end ingress with an HTTP 404 rule.
  Inspect caching, Access and challenge behavior without changing zone-wide rules.
- Verify local liveness and unauthenticated 401 before publishing DNS, then HTTPS,
  unauthenticated 401, authenticated MCP initialization/tools discovery and an
  actual client streaming journey. Use synthetic upstream credentials/responses
  for automated contracts; do not put a global customer API key on the server.
- Report host deployment, tunnel connectivity, HTTPS/auth checks and client
  validation separately. Creating a tunnel or a healthy container is not proof
  of production tenant isolation or complete release readiness.

## Observed prerequisites

- SSH user confirmed: root. Agent now exposes `/Users/roman/.ssh/id_rsa` after
  owner unlocked it. Remote key acceptance remains unverified.
- ED25519 host fingerprint observed over the network:
  `SHA256:vUhcic9+BnLGbikRaBg0ocgyPa5ixjmyIyYmOJ5wN7A`.
  UNVERIFIED: owner must compare with a trusted provider/server-console value.
  Strict SSH preflight stopped at unknown host key; remote OS remains uninspected.
- Public hostname has not been selected by the owner.
- Cloudflare account discovery works. Zone listing is denied for missing Zone
  Read; tunnel listing is denied for missing Tunnel/Connector Read. Setup needs
  DNS Read/Write and Tunnel Read/Write permissions scoped to the chosen resources.
  No Cloudflare write has been performed.

## Acceptance

Repeatable dry-run/apply, fail-closed preflight, no secret output, verified
architecture-specific release, idempotent resource reuse, isolated remote changes,
reboot recovery, tested image rollback and end-to-end HTTPS MCP authentication and
streaming. DNS/caching/Access changes must be exact-host scoped and reviewable.

## Sources

- Existing `compose.yaml`, `docs/compose-hosting.md`, `docs/hosted-pilot.md` and
  `scripts/check-release.sh` define the application runtime and validation.
- Cloudflare [origin parameters](https://developers.cloudflare.com/tunnel/reference/origin-parameters/)
  document `httpHostHeader` and origin connection settings.
- Cloudflare [Tunnel getting started](https://developers.cloudflare.com/tunnel/get-started/)
  documents remotely managed tunnels and Docker connectors.
- Cloudflare [tunnel streaming limitations](https://developers.cloudflare.com/sandbox/sdk/api/tunnels/)
  distinguish temporary Quick Tunnels from named tunnels for SSE.

No code, remote services, DNS records, tunnels or user SSH configuration changed
during design preparation. Design approval remains pending.
