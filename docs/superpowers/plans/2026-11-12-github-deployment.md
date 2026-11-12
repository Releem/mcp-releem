# GitHub deployment implementation plan

**Goal:** Deploy the hosted MCP service to 40.160.8.37 behind mcp.releem.com.
**Architecture:** GitHub verifies the AMD64 release, publishes that exact image
to GHCR, transfers an allowlisted Compose bundle over pinned-host SSH, and runs
transactional activation with rollback. A separately managed named cloudflared
tunnel connects to loopback. No application credential or tunnel token in GitHub.
**Tech stack:** Docker Compose, Bash, GitHub Actions, cloudflared.

- [x] Add failing deployment tests for dry-run, immutable references and rollback.
- [x] Implement host activation and SSH bundle delivery; validate in containers.
- [x] Add manually dispatched default-branch GitHub workflow with release/security
  checks, same-image GHCR publication and production environment deployment.
- [x] Add digest-pinned tunnel Compose and mcp.releem.com administrator settings.
- [x] Document exact GitHub environment secrets, registry access and Cloudflare UI.
- [x] Install Docker on inspected Ubuntu host, stage managed deployment files and
  deploy a verified AMD64 image if release validation passes.
- [x] Check loopback health/auth; report HTTPS/tunnel separately until owner creates
  the tunnel and installs its token. Preserve all existing unrelated services.

Owner approved hostname/design and confirmed host fingerprint on 2026-11-12.
SSH login must use ubuntu with sudo; root login is disabled by the host.
No commits/pushes are authorized; GitHub workflow activation awaits publishing the
reviewed workspace. All implementation stays in the existing dirty feature branch.

Delivered2026-11-12:350 native AMD64 tests, security-enabled release, inspected
archive/scan identity binding, local health/auth and independent review pass.
Actual GitHub run/GHCR publication and public tunnel/client checks remain pending.
