# Private v0.1.0 MVP Release Plan — Local and Shared Hosted

> **For agentic workers:** Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` when implementation is authorized. Track the checkboxes below. The current request is planning only: do not implement, commit, publish, deploy or distribute artifacts during this task.

**Goal:** Deliver a private read-only pilot with both a customer-installed stdio server and one shared Releem-hosted HTTPS MCP service for all participating customers.

**Architecture:** One codebase and diagnostic core with two profiles: local stdio and shared hosted Streamable HTTP. The hosted service validates the supplied Releem API key and resolves its effective access scope for each request. Customers share the deployment, not credentials or request state. Separate per-customer deployments are not the target.

**Tech stack:** Existing digest-pinned Python 3.12 Docker image, locked dependencies, official MCP SDK, pytest, Ruff and mypy. Reuse the HTTP/validation stack for the API-key pilot; review any added dependency. No new login system or OAuth implementation is required for this MVP.

**Prepared:** 2026-11-11T05:48Z; revised 2026-11-11T06:10Z. **Audience:** private pilot, explicitly selected by the owner. **Status:** plan, not release/deployment approval. Shared hosting is now a required MVP capability; this supersedes the earlier local-only boundary.

## Owner-confirmed v0.1.0 deliverables

Confirmed 2026-11-11T06:45Z: **hosted MCP is part of the first MVP**, not a
post-release extension. The release has two supported delivery profiles:

| Deliverable | Required result |
|---|---|
| Local MCP | Package/Docker stdio deployment with the existing read-only core |
| Hosted MCP | One shared HTTPS `/mcp` endpoint for all invited customers, using Streamable HTTP |
| Hosted authentication | Existing customer Releem API key in a configured authorization header, validated before protected requests |
| Isolation | Each request uses only that key's authorized data and credentials; concurrent customers cannot cross |
| Client onboarding | Tested local and hosted Claude configuration, including key rejection/revocation and a diagnostic workflow |
| Release evidence | Reproducible checks, CI configuration, verified artifacts and separate local/hosted quickstarts |

Hosted implementation and deployment are still pending. Adding this requirement
to the plan does not authorize remote deployment or release distribution. Browser
OAuth, separate MCP-key issuance and per-customer deployments are outside this
pilot scope.

## Recommendation and evidence

Stop expanding diagnostic coverage. The repository already implements ten tools,
26 planned diagnostic GET operations, four prompts and a static reference.
The last recorded verification is 193 passing tests, lint/type checks and
successful Docker/package builds. Claude Code 2.1.70 registration and connection
health passed in an isolated project. A complete interactive diagnostic workflow
has not yet been verified. These are receipts from the previous implementation
batch, not fresh test results for a release candidate.

Sources: [implementation receipts](../../implementation-status.md),
[API check scope](../../api-checks-2026-11-11.md),
[client setup and remaining gates](../../clients/local-setup.md),
[original architecture](../../plans/2026-11-10-mcp-releem.md).

The critical first task is **confirming existing Releem API-key validation and effective permissions**, then implementing authenticated shared HTTP and verifying the same diagnostic journey through both profiles. Existing HTTP tests are synthetic: production CLI HTTP, authentication and tenant isolation are not implemented. Private pilot means restricted enrollment, not one deployment per customer.

## MVP boundary

| Decision | Private v0.1.0 scope |
|---|---|
| Primary user journey | Select a server, inspect findings and explain an existing recommendation |
| Transport | Local stdio plus authenticated shared HTTPS Streamable HTTP |
| Distribution | Local reviewed Docker artifact plus one shared hosted service URL; no public registry required |
| Primary client | Claude Code; record the exact tested build |
| Other clients | Cursor instructions remain experimental until actually tested; not a release blocker |
| Architecture support | Existing verified image is Linux ARM64. Verify AMD64 before distributing to an AMD64 pilot user; do not claim untested support |
| API | Owner-approved `https://api2.dev.releem.com`; describe it explicitly as the pilot target, not certified production/self-hosted parity |
| Credentials | Existing customer API key; local credential configuration or hosted HTTPS authorization header. Validate with authoritative Releem authentication/permissions; never use one shared privileged key plus a model-supplied customer ID |
| Hosted pilot authentication | Explicit API-key authentication for clients with configurable headers; browser OAuth and separate MCP keys are not required for the pilot |
| Sensitive reads | Disabled by default; no raw SQL, dumps, actor identities or opaque review payloads |
| Data path | Local or hosted MCP calls Releem API; selected results can reach the client's model provider |
| Existing secondary tools | Retained with documented evidence/coverage limitations; no new functionality added |
| Metric grouped windows | Document aligned-window limitation; use hourly comparisons in the primary journey. If still unreliable, mark grouped series experimental rather than guess bucket semantics |
| Publishing/license | No public publishing. Public license/registry decisions are deferred; retain dependency notices and review private distribution terms |

## Prioritized work

Execute P0.0 first to settle hosted prerequisites, then the candidate/release checks,
client verification and handoff. Keep diagnostic feature expansion frozen.

### P0.0 — Shared HTTP with existing Releem API-key authentication

**Deliverables:** `docs/decisions/0002-hosted-identity.md`, permission/validation
contract and hosted integration tests. Expected modules:
`src/mcp_releem/hosted/{config,app,context,limits}.py`. Refine against existing SDK/core interfaces; keep local behavior
stable and modules within the 300-line limit.

- [ ] Confirm the authoritative validation contract for existing Releem keys: owner/access scope, invalid/revoked-key behavior, available read-only permissions and revocation timing. Do not invent an introspection endpoint; identify an existing backend validation facility or document the required upstream change.
- [x] Accept the customer key through an HTTPS authorization header, never tool arguments, URL parameters or model prompts. Treat this as explicit API-key authentication, not an OAuth access-token flow.
- [x] Validate credentials before every protected MCP request, including discovery/prompts/resources. An existing authorized GET may establish current API access where appropriate, but a successful request alone must not fabricate account membership or human-user identity.
- [x] Derive the request's effective access from the validated key. If a key is account-wide, disclose account-wide access; do not claim individual user permissions/auditing that the key cannot establish. Releem's authorization remains authoritative for each upstream operation.
- [x] Pass that request's key to the fixed, administrator-configured Releem API as Releem-Secret-Key. Never fall back to a global privileged key or a caller/model-supplied customer ID. Reject upstream redirects and arbitrary destinations.
- [x] Create isolated request services/clients. Never mutate a shared client's authorization headers to switch customers. Keep any necessary client/session/cache state isolated by verified identity/credential context; use a non-reversible identifier for internal partitioning, not a raw key in logs or cache names.
- [x] Avoid persistent customer-key storage and result caching in the MVP. Keys remain request-scoped and must not appear in logs, error text, traces, artifacts or model output. If validation is cached, explicitly define the revocation delay and invalidate on upstream auth failure.
- [ ] Add explicit HTTP configuration with fail-closed authentication, allowed Origin/Host policy, HTTPS deployment guidance, metadata-only health/audit output, quotas, concurrency limits, timeouts and cancellation. Keep one shared application deployment and preserve local stdio.
- [x] Test missing/malformed/invalid/revoked keys; unauthorized server/child IDs; concurrent customer A/B calls; credential/session reuse; static endpoint authentication; errors/redaction; quotas and cancellation. Failed authentication must not expose customer data or totals.
- [ ] Test configured-header authentication in the exact Claude/Cursor versions claimed supported. Do not promise browser OAuth or compatibility with clients that cannot supply the key securely.

**Acceptance:** customers A and B use the same URL with their own existing keys,
and receive only the data those keys authorize. Missing/revoked keys fail,
request credentials cannot cross, and no unauthenticated listener or global-key
fallback is exposed. Key validation/permission semantics remain an upstream fact
to confirm before implementation; this plan does not invent stronger key scopes.

This follows the intentional service-account API-key pattern documented by
[native Coroot MCP](https://docs.coroot.com/mcp/overview/#authentication), not the
community adapter's unauthenticated HTTP listener. A separate MCP key remains an
optional future choice. OAuth is deferred; if introduced, use audience-bound MCP
tokens rather than treating upstream OAuth tokens as interchangeable credentials.

### P0.1 — Freeze and identify the candidate

**Files:** update `docs/implementation-status.md`; create `docs/releases/0.1.0.md` and `CHANGELOG.md`; verify `pyproject.toml` and `src/mcp_releem/__init__.py` agree on `0.1.0`.

- [x] Record the supported scope above and freeze feature work.
- [ ] Review the full branch change, including removal of the previous execution harness. Keep that cleanup separate from claims about new diagnostic behavior.
- [ ] Inventory the installed runtime dependency licenses/notices and known security findings; investigate actionable findings rather than blindly upgrading the SDK.
- [ ] Record source revision, dirty/clean state, dependency lock hash, API-contract hash, image architecture and exact client build in the candidate receipt.
- [ ] Keep candidate artifacts clearly identified as uncommitted development builds until a reviewed release commit is separately authorized.

**Acceptance:** one consistent version and scope, no unsupported client/hosting/architecture claims, no unresolved critical security finding. Public license selection is not required for this private-pilot preparation.

### P0.2 — Make release verification reproducible

**Files:** create `scripts/check-release.sh`, `tools/release/installed_check.py` (consolidated on 2026-11-12), `tools/release/artifacts.py`, `tests/test_release_artifacts.py`; update `Dockerfile` and `.dockerignore` only as needed for verification tooling.

- [x] Promote the existing temporary runtime smoke checks into repository-owned tooling. Use installed package entrypoints, synthetic credentials and network-disabled containers.
- [x] Implement one fail-fast command: `bash scripts/check-release.sh`. It must run locked container builds, Ruff format/lint, strict mypy, offline pytest, wheel/sdist build, runtime smoke and artifact checks.
- [ ] Verify authenticated hosted/local parity and the P0.0 isolation tests, plus discovery of ten read tools/four prompts/reference; a bounded synthetic successful read; sanitized invalid inputs; denied mutation names; denied default sensitive reads; explicit offline dependency failure; cancellation and clean stdio shutdown.
- [x] Install the wheel into an isolated container target and verify import/version/entrypoint behavior without importing the source checkout.
- [x] Add meaningful artifact-audit regressions first: unexpected secret/config paths, old harness contents, version mismatches and missing required modules must fail. Use synthetic archives; never customer fixtures.
- [ ] Check wheel/sdist/runtime contents and build context exclude `.env`, private backups, continuity files, Git data and old execution code. Keep code modules within the repository's 300-line limit.
- [ ] Generate a machine-readable verification receipt and SHA-256 sums. Do not let a failed check produce a successful release receipt. Do not delete unrelated files or prune Docker state.

**Acceptance:** a contributor can reproduce the complete check from the checkout with Docker and no Releem credential. Every step exits nonzero on failure. No host package installation or customer API request is part of this command.

### P0.3 — Validate the actual client journey

**Files:** update `docs/clients/local-setup.md` and `docs/clients/compatibility.md`; add reusable synthetic onboarding fixtures under `tools/release/` if needed.

- [ ] Load the local candidate and connect to the authenticated shared endpoint in isolated client configurations; leave existing user/project client settings untouched.
- [ ] Complete configured-header authentication/discovery and the primary diagnostic workflow with two separate customer keys through the same URL. Confirm revoked-key and cross-customer access denial in the actual client flow.
- [ ] Confirm Claude exposes the tools, prompts and reference and can render a structured synthetic diagnostic result, not just report connection health.
- [ ] Exercise: server discovery → explicit selection → findings → recommendation explanation. Include an empty/missing snapshot and an upstream failure so neither becomes a healthy result.
- [ ] Confirm no mutation can be called and no permission setting is enabled by prompt text or tool arguments. Verify process shutdown/cancellation and bounded output in the client.
- [ ] Check token-file readability by the image's nonroot user. Fix the installation instructions or supported user mapping; do not make credentials broadly readable.
- [ ] For real-data model use, obtain explicit authorization for the test account/client/model path before sending customer evidence to a model. Otherwise finish this gate using synthetic evidence and record the limitation.
- [ ] Record exact client version, architecture, setup, observed behavior and remaining limitations. A model-assisted client run may require an authenticated account and billable model calls; an SDK test or CLI health check must not be relabeled as that run.

**Acceptance:** local and shared hosted client paths produce useful bounded answers with missing evidence visible, and hosted authentication/isolation work. If interactive verification cannot be authorized or completed, call the candidate a developer preview; do not claim full application onboarding.

### P0.4 — Add CI verification

**Files:** create `.github/workflows/ci.yml`; reuse `scripts/check-release.sh`.

- [x] Configure pull-request and branch-push verification with read-only repository permissions and a finite job timeout.
- [x] Pin third-party actions to verified immutable commits when implementing; use the existing Docker base/dependency locks.
- [ ] Run the same release check and synthetic hosted authentication/isolation tests as local development, without customer API credentials. Verify AMD64 on a native runner if that architecture is needed for the invited pilot.
- [x] Do not add publication, registry login, deployment, release creation or artifact-upload jobs in this phase.
- [ ] Validate the workflow locally where feasible and distinguish that from a remote CI run. Remote execution requires an authorized push/PR.

**Acceptance:** the workflow configuration and local checks are reviewable. A passing remote CI run is required on the eventual approved release revision before calling that revision CI-verified.

### P0.5 — Prepare the smallest usable pilot bundle

**Files:** create `docs/pilot-quickstart.md` and `docs/pilot-feedback.md`; update `README.md` and `docs/releases/0.1.0.md`.

- [ ] Write two short quickstarts: local image/credential/check/client setup, and hosted shared URL/API-key/client setup. Hosted users do not install Docker or receive another customer's key. Both lead to explicit server selection and the primary diagnostic journey.
- [ ] Document the approved API origin, architecture/client support, data/model path, no-write boundary, missing-data behavior and grouped-metric limitation.
- [ ] Include removal/credential-revocation instructions and previous-image rollback instructions for later pilot updates.
- [ ] Produce the image archive, wheel/sdist for developer use, checksum file and release receipt in the local release output directory. Record native architecture and image ID; do not claim a multiarchitecture archive.
- [ ] Test `docker load` and launch from the archive on an isolated Docker context or another pilot-compatible machine. Avoid removing or replacing unrelated images/containers in the current context.
- [ ] Supply a compact feedback template: task attempted, version/client/architecture, result/warning/error code and expected behavior. Ask for sanitized descriptions, not keys, raw SQL, dumps or customer payloads.

**Acceptance:** participants can use either version without reading architecture documents. Local artifacts have checksums; the shared service has reviewed identity, credential and operational configuration. Preparation does not authorize deployment or distribution.

### P0.6 — Release decision and controlled handoff

- [ ] Review all P0 receipts and known limitations; fix installation failures, false healthy results, scope violations, credential exposure and broken primary workflows before handoff.
- [ ] Have the owner approve the concrete local/hosted candidate and intended private recipients/channel. Commit/tag, credential or identity-provider changes, deployment and private delivery occur only when explicitly authorized.
- [ ] Rebuild and verify artifacts from the reviewed release revision; ensure the final manifest identifies that revision and checksums the exact delivered files.
- [ ] Invite a small pilot cohort, with one feedback owner and an agreed review date. These organizational choices are proposed, not already confirmed.

**Acceptance:** a clearly identified private v0.1.0 has both local and shared hosted delivery, support ownership, known limits and verification receipts. Remote deployment and delivery require explicit authorization; public publication is excluded.

## What is not a v0.1.0 blocker

Public publishing, self-service billing/enrollment, a custom identity platform,
Kubernetes, per-customer application deployments, full Cursor UI certification,
write tools, more endpoints, dashboards and exhaustive engine/provider certification
are deferred. Shared hosted API-key authentication, authoritative permissions and request
isolation are required, not deferred. Browser OAuth and separate MCP-key issuance
are deferred for this configured-header pilot. Do not weaken those boundaries to simplify
the pilot. Do not certify unconfirmed metric bucket semantics.

## Release gate and effort

The candidate is ready when P0.0–P0.5 have receipts: local and hosted primary
journeys succeed, shared customer/user isolation and credential lifecycle tests
pass, the exact local artifact installs on supported architecture, and no critical
issue remains. P0.6 is the separately authorized commit/deployment/handoff.

Estimate implementation after confirming P0.0's key-validation/permission
contract. The prior OAuth-integration estimate does not apply unchanged to this
smaller API-key pilot. Release automation, real-client verification and isolation
tests remain mandatory; deployment and private delivery remain separately authorized.

Decide first: existing key-validation mechanism and effective permission scope,
required revocation timing, supported client-header configuration, hosting
platform/region and pilot cohort. The target is one shared hosted service for all
customers plus local installation, with no new sign-in system required for the pilot.

## Implementation checkpoint — 2026-11-11

Shared API-key boundary, scoped request clients, synthetic customer/revocation
tests, both SDK HTTP modes, container verification tooling and CI configuration
are implemented. See implementation-status.md and docs/hosted-pilot.md (paths
relative to repository root). The current dev API rejects missing/invalid keys;
real revocation timing, read-only key availability and independent account tests
remain UNCONFIRMED. Exact client UI, TLS ingress, dependency audit and clean-machine
artifact handoff gates remain open. No deployment, publication or delivery occurred.
