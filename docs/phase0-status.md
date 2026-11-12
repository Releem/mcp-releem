# Phase 0 progress — 2026-11-10

Status: **offline SDK compatibility evaluation complete; Phase 0 release gates
remain open**. Verification completed at `2026-11-10T17:37:40Z`.

## Verified

- Public development OpenAPI is byte-identical to the retained capture: 45
  operations; SHA-256
  `dd6f9ae69c1bcd7e96e5d2cb4a004721d17eed0183dc98cb132442a2d0fa45d2`.
- Candidate dependencies resolve and install with hashes in the pinned Python
  3.12.16 container; no host package installation.
- Nine offline synthetic tests pass in 12.33s: typed structured read results,
  annotations, invalid arguments, absent mutation tool, modern/legacy stdio,
  modern/legacy HTTP, stateful/stateless legacy session headers and invalid
  Origin rejection. Parametrized transport tests account for six test cases;
  session headers account for two; Origin accounts for one.
- Ruff lint passes; both Python files pass formatting and mypy.
- Container image build passes. Local experiment image ID:
  `sha256:11648df359c716463a326d234a766e1e051d00ea1ccbea9af20ecca3730b6047`.
  This is a local image ID, not a published registry digest.
- Checks ran with `--network none --read-only --tmpfs /tmp`; HTTP used container
  loopback. No database, Releem account, credential, model call or deployment.

## Decisions refined

Use the official SDK's existing current/legacy HTTP behavior; no custom legacy
adapter is justified. Stateless mode suffices for the synthetic read contract.
Stateful legacy sessions are process-local and require affinity across workers;
modern requests do not have protocol sessions. Request authorization still must
be independent of either transport behavior.

See [decision 0001](decisions/0001-shared-python-core.md),
[client scope](clients/compatibility.md) and the
[current verification commands](../README.md#development-and-verification).
The separate experiment was retired on 2026-11-12; current product transport
coverage is in `tests/test_transports.py` and `tools/release/local_journey.py`.

The user subsequently confirmed `https://api2.dev.releem.com` as the API base
URL on 2026-11-10 (same origin as Swagger). The endpoint-selection gate is resolved;
this adds no live API verification receipt.

## Open gates

- API owner review of cloud/self-host scope, read-only
  credentials, endpoint roles and agent/engine/provider compatibility.
- Trusted hosted identity-to-tenant-to-credential integration and revocation
  design; no endpoint or delegated identity flow is assumed.
- Actual Claude Code 2.1.70 and Cursor 3.25.6 onboarding (including OAuth) in
  isolated client/test configurations; reading installed versions is not a pass.
- Dependency/license/security review for the eventual product lockfile and
  API-owner acceptance of the complete operation classifications.

Superseded implementation state: the user later authorized the first local
product slice; see [implementation status](implementation-status.md). These
Phase 0 experiments alone do not establish
Releem read-only enforcement, tenant isolation or end-to-end client support.
