# Compose hosting implementation plan

Goal: operate the approved single shared hosted Docker service using Compose.
User authorized implementation and start/restart management; remote deployment,
Cloudflare account changes, publication and commits remain excluded.

Architecture: root compose.yaml builds the existing hosted target or uses a pinned
operator image. Publish127.0.0.1 only; host-managed Cloudflare Tunnel forwards the
public Host unchanged. Explicit administrator environment only, no env_file mount
or customer credential forwarding. Nonroot/read-only, tmpfs, bounded resources/logs,
unless-stopped restart policy and static liveness independent of upstream API.
Health status alone does not restart a hung process; document monitoring/manual
restart. Configuration updates use up/recreate, not restart.

- [x] Add actual-loopback health tests and observe missing module failure.
- [x] Add stdlib HTTP health probe with configured public Host, timeout, bounded
  response and fixed sanitized failures; no API read, redirect or proxy discovery.
- [x] Add compose.yaml and deploy/hosted.env.example with placeholder public URL,
  explicit environment, private port, restart/health/resource/security settings.
- [x] Add repository-owned Compose smoke: isolated project/ephemeral loopback port,
  health and401 checks, manual restart, unexpected process exit recovery, inspect
  environment/security/limits, cleanup only its own project. No customer API calls.
- [x] Update hosted runbook/quickstart/README/release checklist/AGENTS/continuity.
- [x] Run container format/lint/type/tests/build release checks; run Compose smoke
  against exact verified hosted image; record receipts and outstanding remote gates.

Verification receipt: docs/implementation-status.md;254 offline tests plus isolated
Compose lifecycle pass. Remote deployment/TLS/client/real-account gates unchanged.
