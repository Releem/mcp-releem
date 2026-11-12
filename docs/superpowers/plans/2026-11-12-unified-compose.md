# Unified Compose implementation plan

**Goal:** One Compose project operates MCP and its Cloudflare connector.
**Architecture:** Add profile `tunnel` to root compose.yaml. Both services share
the default private bridge; Cloudflare routes to http://mcp:8000, and the host
port remains127.0.0.1-only. Token stays in a read-only mounted file. Initial
connector startup waits for MCP health; Docker restart policies and connector
reconnects handle reboot recovery, not Compose dependency ordering at boot.

User explicitly approved combination and requested exact execution commands.
No commit/push, public routing, token retrieval or server reboot is requested.

- [x] Add failing tests for combined Compose service/profile/dependency and
  activation targeting MCP only while preserving the connector profile.
- [x] Add cloudflared to compose.yaml and remove the separate tunnel file.
- [x] Update activate.sh/start-tunnel.sh and add a stable stack command wrapper;
  record COMPOSE_PROFILES=tunnel when the protected token exists. Keep application
  deployment and rollback scoped to service mcp. Reject duplicate legacy project.
- [x] Exercise the shared Docker network with a synthetic connector, application
  and connector crash recovery, startup health ordering and app-only updates.
- [x] Run container checks/build/lint/typecheck/tests/transport and package checks;
  validate scripts/YAML and request independent review.
- [x] Stage the updated Compose/helpers on the authorized host, preserve its exact
  verified runtime image, check health401/200 and stage hidden-token command.
- [x] Update operator docs/provenance/continuity and show exact user commands.

Fresh native security-enabled candidate fhh1zJOv passed351 tests21.89s/24checksums;
the new verified image97c9a8...b1db59 replaces the prior verified candidate, while
retaining it for rollback. Source fingerprint matches the local export exactly.

Cloudflare token absent at preflight; connector cannot be started authentically
without owner input. No claims of public connectivity or reboot proof follow
from synthetic connector tests.
