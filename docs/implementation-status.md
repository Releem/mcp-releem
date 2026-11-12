# Implementation and verification

Current product version: **0.1.0**, uncommitted developer preview. Hosted backend
deployed on the authorized server; public tunnel and GitHub publication pending.

## Unified application/tunnel stack — 2026-11-12

Root Compose now defines both `mcp` and optional-profile `cloudflared` in project
`mcp-releem`, using private service DNS `http://mcp:8000`. Initial connector startup
waits for MCP health; both containers have `unless-stopped`. Token-file privacy,
loopback host binding and app-only deployment/rollback are retained. Installed
`/opt/mcp-releem/stack` operates the current release; the hidden-token helper
enables/persists the tunnel profile. This supersedes the separate-project and
host-network connector instructions in prior dated evidence.

Exact source-matched AMD64 release passed351 tests21.89s, Ruff96 files, mypy62
sources, both transport contracts, wheel/sdist and24 checksums. New synthetic
combined-stack smoke verifies service DNS, initial health dependency, connector
process-crash recovery, MCP restart and preservation of the connector on app-only
updates. Advisory gates passed29 Python packages/0 known findings and0 HIGH/CRITICAL
image findings. ShellCheck/actionlint and independent review clear. Server backend
healthy after activation, local health200/MCP401. Token absent: actual cloudflared,
public connectivity, authenticated client and host reboot remain unverified.
[Receipt](releases/evidence/2026-11-12-unified-stack.json),
[operator commands](github-deployment.md). No customer API/SQL call, commit or push.

## AMD64 server setup — 2026-11-12

Ubuntu26.04/AMD64 host40.160.8.37 now has Docker/Compose5.7.1 enabled at boot.
The verified hosted image runs nonroot/read-only on127.0.0.1:8000, with local
health200 and unauthenticated MCP401. Native security-enabled release passed350
tests22.13s, Ruff96 files, mypy62 sources, transport/package/Compose checks and23
checksums;29 audited Python packages have0 known findings and the image has0
HIGH/CRITICAL findings. Docker containerd OCI-index identity is now bound through
hashed archive descriptors to the config digest reported by Trivy; mismatches
still fail closed. This supersedes native AMD64's unverified designation below.

GitHub workflow, SSH deployment/recovery scripts, dedicated restricted public key
and pinned token-file tunnel setup are prepared. Independent review findings on
private-image/first-deployment rollback are fixed and regression-tested. No commit,
push, GHCR publication, customer API/SQL call or public tunnel activation occurred.
DNS for mcp.releem.com remains unresolved. Authenticated HTTPS/client/tenant and
revocation gates remain open. See [setup](github-deployment.md) and
[receipt](releases/evidence/2026-11-12-server-deployment.json). Earlier dated
sections retain their historical platform/gate descriptions.

## OpenAPI compatibility update — 2026-11-11

Implemented the46-operation documentation contract without expanding the ten tools
or26 GET allowlist. Findings accept nullable metadata and separate explicit failures
from unknown/missing states. Query analytics serializes canonical `period` and
`end_date`; legacy MCP `period_days` remains an alias. Explicit/effective windows
must match; malformed/lossy timestamp inputs and source bounds fail explicitly.
Configuration latest means newest state; average comparison bounds are half-open.
The new `/v1/checks` catalog remains deferred. Exact old/new captures are retained
and hashed; offline tests guard all registry paths/query keys against the active
capture. No dependencies or authentication/tenant boundaries changed.

Fresh security-enabled release **PASS** at2026-11-11T16:16Z: **343 tests19.87s**,
Ruff93 files, strict mypy61 sources, locked builds, installed wheel/stdio and
modern/legacy synthetic TCP journeys, Compose lifecycle and22 checksums. Exact
hosted image has0 HIGH/CRITICAL image findings and29 third-party Python packages
with0 known vulnerabilities. Independent spec/quality reviews clear after fixing
review-reproduced malformed-offset/submicrosecond normalization gaps. Local
synthetic demo refreshed; isolated Claude2.1.70 HTTP connection passes. Historical
272-test receipts remain preserved for the previous candidate.

Candidate `mcp-releem-release.YhWQ26sM`; hosted image `59b55cb9…eeb9dba8`;
source fingerprint `62a4840d…c16a19ed7`. The [exact update receipt](releases/evidence/2026-11-11-openapi-update.json)
records hashes, checks and limitations. Native arm64 only; actual-host TLS,
remote CI/AMD64 and model-directed onboarding remain separate release gates.
[Review](plans/2026-11-11-openapi-change-review.md),
[implementation plan](superpowers/plans/2026-11-11-openapi-compatibility-update.md).
No authenticated API calls, database operations, commit, publication or deployment.

## Runtime security blocker resolved — 2026-11-11

- Shipped images now use digest-pinned Python3.12.16/Alpine3.24.4. Existing Python
  lock/dependency versions and tool contracts are unchanged. SQLite library and
  Python bindings are physically removed from runtime/hosted images; build/check
  stages keep SQLite required by mypy caches. Real APK metadata is retained.
- Original11 OS advisory IDs have independent reviewed dispositions: removal/
  absence for SQLite/acl/systemd/Perl; fixed libuuid/ncurses versions. Stable
  krb5/zlib packages explicitly pinned to repaired versions. No edge repositories,
  package-database stripping, severity downgrade or CVE exception/suppression.
- Exact final security-enabled release **PASS**:272 tests17.79s,Ruff88 files,
  strict mypy59 sources, installed stdio/TCP workflows/Compose lifecycle/wheel and
  source fingerprint pass;22 candidate checksums verified. Trivy identified37 OS
  packages plus Python and Rust components with0 HIGH/CRITICAL findings. Exact29
  third-party runtime Python packages have0 known vulnerabilities; notices retained.
- Public documentation HTTPS/system CA probe returned200 without a credential.
  No customer API/database operation, remote deploy/publish or commit performed.
- Local synthetic demo upgraded at the same loopback URL; isolated Claude HTTP
  connection rechecked. Full model-driven onboarding, actual-host TLS/Cloudflare,
  native AMD64/remote CI and reviewed release revision remain separate gates.
- Candidate: `/var/folders/r_/s99frfmn3psbyhxx28wkdz_80000gn/T/mcp-releem-release.6JREwacl`.
  [Security evidence](releases/evidence/2026-11-11-runtime-security.json),
  [runtime decision](decisions/0003-hardened-runtime.md). This supersedes the prior
  failed Debian runtime gate, not its historical evidence or other release gates.

## Reviewed local release candidate — 2026-11-11T10:08Z

- Independent source review found unauthenticated-body work-slot starvation and
  protocol-method echo; both fixed with reproduced regressions. Separate32/3s body
  and8/5s validation stages precede authenticated quotas. Follow-up review verified
  counter/context cleanup; ingress source limits remain a deployment gate.
- Added installed real TCP synthetic two-account workflows in both SDK modes,
  covering explicit selection, findings/missing evidence, recommendation list/
  detail/explanation, prompts/reference, foreign-target rejection, simulated key
  revocation and dependency failures. Actual Claude Code2.1.70 configured-header
  HTTP connection passed; its isolated profile lacks model login, so model-driven
  onboarding remains unverified. User chose synthetic accounts; no real API calls.
- Exact runtime Python audit:29 third-party packages, zero known vulnerabilities;
  all bundled license notices inventoried. Zlib patch installed in container from
  Debian security repository. Exact image scan still reports47 HIGH package records
  across11 advisory IDs, zero CRITICAL/no fixes reported. Strict security gate is
  failed; these findings have not been suppressed or accepted.
- Release helpers now fingerprint explicit inputs before/after checks, verify
  checksums/tampering, retain license notices and bind security success to image/
  archive digest. Fixed Linux0700 verifier permissions and stale-success handling.
- Latest full pipeline: **268 tests16.20s, Ruff86 files, mypy58 sources**, locked
  package/runtime/hosted builds,17 candidate checksums verified, installed TCP journey
  and isolated Compose lifecycle pass. Archive load and new→previous→new Compose
  rollback roundtrip pass; temporary rollback/lifecycle projects removed.
- Candidate: `/var/folders/r_/s99frfmn3psbyhxx28wkdz_80000gn/T/mcp-releem-release.kSiowez3`.
  Synthetic-only local demo remains on loopback for user testing; no Cloudflare/
  actual customer deployment. All source remains uncommitted; remote CI not run.
  [Evidence](releases/evidence/2026-11-11-local-validation.json),
  [review and outstanding advisories](releases/security-review-2026-11-11.md).

## Compose host operation — 2026-11-11

- Added root compose.yaml and ignored deploy/hosted.env operator configuration,
  with placeholder-only deploy/hosted.env.example. One nonroot/read-only container,
  loopback-only published port, init, dropped capabilities, tmpfs, bounded CPU/
  memory/PIDs/logs,40s shutdown grace and unless-stopped restart policy.
- New local-only health module checks bounded static liveness with public Host;
  no API key, redirect following, environment proxy or Releem read. Docker health
  status does not itself restart a hung process; documented manual recovery.
- Repository-owned Compose smoke uses a unique temporary project/random loopback
  port; verified startup health, unauthenticated401, host key not forwarded,
  private port/nonroot/read-only policy, manual restart and unexpected service
  process exit/recovery. Its project/network were removed; unrelated containers
  were not changed. No host reboot, Docker daemon restart or Cloudflare connection
  was performed. Compose5.0.2 observed; real host/AMD64 gates remain open.
- Full release check passed: **254 tests (13.66s)**, Ruff73 files, strict mypy50
  sources, locked builds/wheel and runtime checks, Compose lifecycle and final
  checksummed bundle. Source remains uncommitted, native linux/arm64.
- Receipt: `/var/folders/r_/s99frfmn3psbyhxx28wkdz_80000gn/T/mcp-releem-release.obdXY6kq/verification.json`.
  This supersedes the previous247-test receipt. See [Compose operations](compose-hosting.md).

## Shared hosted and release preparation — 2026-11-11

- One shared stateless authenticated `/mcp` app, using the existing Releem API key
  per request. Missing/invalid keys fail before MCP discovery; all protected
  requests validate current inventory. No global key, session or result cache.
- Request-local diagnostic services and clients enforce inventory server scope;
  fleet/inventory source scope also fails closed. Upstream authorization remains
  authoritative. No inferred human identity or invented granular permissions.
- Strict Host/Origin policy, bounded fixed/chunked bodies, sanitized resource
  errors, quotas/concurrency/deadlines, cancellation cleanup, header stripping,
  redirect refusal and static public liveness. TLS ingress/egress remains an
  operator deployment requirement. No browser OAuth is implemented.
- Legacy and 2026-07-28 SDK authenticated HTTP handshakes, discovery, successful
  structured read, prompts/reference and write denial pass with synthetic API
  responses. Concurrent A/B, revocation, foreign targets, outages, invalid headers,
  oversized bodies, quota and cancellation are offline regressions.
- One `bash scripts/check-release.sh` builds locked checks/runtime/hosted/artifact/
  wheel targets; verifies installed modules/CLI/nonroot runtime; audits archives;
  exports both images, wheel/sdist, SHA256SUMS and a dirty-revision receipt.
  CI is configured with read-only permissions and pinned checkout; not remotely run.
- Direct HTTP dependencies now pin installed Starlette1.10.0 and Uvicorn0.54.0;
  all previous runtime pins are retained and the lock regenerated in a container.
- Three authorized GET probes: missing key401, invalid synthetic key401, valid
  key200. No customer payload retained. Real revocation propagation, independent
  account tests and least-privilege upstream scopes remain UNCONFIRMED.

Final checks: **247 tests passed (13.11s)**; Ruff format/lint71 files and strict
mypy49 sources passed. Full pipeline succeeded; final receipt:
`/var/folders/r_/s99frfmn3psbyhxx28wkdz_80000gn/T/mcp-releem-release.PLblukz3/verification.json`.
The sibling SHA256SUMS covers both image archives, wheel/sdist and check reports.
Native architecture: linux/arm64. Source baseline4295c76 is dirty; this identifies
a verified working-tree candidate, not a committed release. Final documentation
receipt updates are outside the package build context.
All handwritten source/tests/release modules remain within300 relevant lines.
See [hosted guide](hosted-pilot.md), [release gates](releases/0.1.0.md) and
[pilot quickstart](pilot-quickstart.md). Interactive application onboarding,
deployed HTTPS/ingress, dependency advisory/license review, AMD64 verification,
clean-machine archive loading and authorized handoff remain open; these are not
implied by synthetic tests or a locally built container.

## Prior local verification receipt

Verified 2026-11-11T05:16Z. This historical local receipt is superseded by the shared
hosted implementation and final check above.

## Implemented

- Ten local stdio tools: `servers`, `server_findings`, `recommendations`,
  `query_evidence`, `configurations`, `metrics`, `events`, `deadlocks`,
  `task_outcomes` and `captured_sessions`. All twenty-six planned diagnostic GET operations:
  O01–O03/O05/O07/O12–O19/O21/O23–O31/O33–O35 from the [coverage matrix](plans/api-coverage.md).
- Recommendation lists retain explicit server scope by default; fleet scope is
  opt-in and validates every returned server against inventory from the same
  credential. List filters/pagination/identities are checked before output;
  foreign rows fail without exposing totals. Fleet excludes inactive/deleted
  servers upstream, so absence is not fleet health.
- Recommendation detail exposes current review scores/rationale and bounded
  review/status history (history_limit1–20, default10). Missing histories remain
  distinct from empty arrays; unknown actor/status categories, UTC provenance,
  truncation and omitted opaque payloads remain visible. Actor identities,
  reason text, arbitrary pointers and opaque review/input JSON are omitted.
  Verified same-server evidence paths map to typed reads; raw URLs are never
  returned or fetched. Detail history narrowing can resolve output size errors.
- Opt-in `server_findings` schema section with canonical check-type/schema
  filters and local row limit. Null snapshots, filtered-empty completed runs,
  unfiltered-empty runs, stale evidence and decode/unknown states stay distinct.
  Parent scope is checked on snapshots and rows; arbitrary JSON payloads remain
  private. Counts/flags and observed/fetched timestamps remain visible.
- Four static diagnostic prompts and release-versioned `releem://reference`:
  explicit targets, bounded read guidance, evidence caveats and no permission
  grants or automatic API calls. Prompt dispatch validates before SDK rendering
  and returns sanitized protocol errors. No customer/configuration resource.
- Stored incident list/detail reads enforce parent/record identity, bounded UTC
  windows and mode-specific arguments. Events preserve UInt64 IDs as strings,
  inclusive whole-second bounds and shifting offset pages without a total.
  Deadlock durations retain seconds and unknown values. Tasks preserve unknown
  codes and missing final reports. Captures expose historical aggregates only,
  examining at most 500 rows per snapshot and making parsing gaps explicit.
- Sensitive incident detail/capture reads require administrator
  `RELEEM_MCP_SENSITIVE_DETAILS=true`, default false, before upstream dispatch.
  Opaque event bodies, dumps/transaction SQL, task parameters/output/error text
  and processlist identities/SQL remain omitted even when enabled. No task
  submissions, capture creation, polling or execution capabilities are exposed.
- Configuration history/latest/detail preserve state IDs separately from logical
  configuration IDs and enforce parent/state identity. Application periods,
  restart status and nullable analysis summaries remain visible. Variable values,
  raw source/original configuration, JSON recommendations and untyped evaluation
  metrics are deliberately omitted with partial coverage; numeric value
  allowlists remain future work.
- Metric catalog, same-server series by name/item ID and up to four named metric
  comparisons. Explicit UTC windows, raw/trend duration limits, aggregation rules,
  null/zero/unit mismatch reasons, hourly-average semantics and 500-point/byte
  limits are enforced. No automatic retries or raw-data fallback. The owner
  confirmed naive upstream times are UTC; normalization carries an explicit
  warning and live series verification passes with aligned five-minute bounds.
  Bucket anchoring remains unspecified; out-of-window labels are rejected.
- Query analytics, existing proposals, saved optimization lists and details.
  Effective UTC windows, measurement units, nulls, filtered percentages and
  unknown numeric statuses are preserved. SQL submission, optimization creation
  and EXPLAIN task creation are absent from discovery and dispatch.
- Same-server, same-record and same-query validation, including nested linked
  proposals. Only selected existing JSON plan facts are returned. Raw SQL,
  predicates, full plan text and raw upstream errors are omitted; missing or
  minimized plan evidence is explicitly partial.
- `RELEEM_SECRET_KEY` supported as an alternative upstream credential source.
  Explicit `--env-file` uses pinned python-dotenv 1.2.4 without interpolation or
  shell execution. No implicit dotenv loading; ambiguous credential sources fail.
- Existing response budgets, read concurrency limit, cancellation, sanitized
  errors and typed discovery/dispatch checks retained. CLI HTTP remains disabled
  until authenticated composition exists.

## Verification receipts

| Check | Result |
|---|---|
| Fresh locked dependency installation | Passed in dedicated Docker builds; 47 locked packages |
| Offline product tests | **193 passed**, 12.41s in the fresh checks image |
| Ruff lint / format | Passed; 58 files formatted |
| Strict mypy | Passed, 40 source files |
| Checks/runtime/artifacts Docker targets | All built and exported successfully |
| Wheel and sdist build | Passed through the Docker artifacts target |
| Packaged runtime smoke | Nonroot UID 65532; ten read tools, schema input contract, four prompts/static resource; denied writes/invalid inputs/disabled sensitive reads; explicit offline failure; clean EOF |
| Installed wheel smoke | Fresh wheel installed offline; imports from wheel target; `--check` passes without exposing the synthetic key |
| SDK transport contracts | Current/legacy stdio and synthetic loopback HTTP: tools, prompt discovery/retrieval and reference resource reads |
| Independent query review | Nested proposal scope gap fixed; targeted scope/limits checks passed; no remaining substantive findings reported |
| Independent configuration/metric review | Extreme UTC-offset overflow fixed and regression verified; no remaining actionable findings |
| Independent incident spec and quality reviews | Missing detail units and UInt64 JSON-number precision fixed with regressions; both reviews clear |
| Independent schema/workflow spec and quality reviews | Empty nonnull snapshot timestamp rejected and UTC provenance added with regressions; both reviews clear |
| Independent recommendation spec and quality reviews | List UTC handling and unknown actor indicator added with regressions; scope/evidence/history/privacy reviews clear |
| Claude Code 2.1.70 | Isolated temporary project registration and connection health pass against rebuilt network-disabled runtime; synthetic key; no model calls or existing config edits |
| Distribution hygiene | Real `.env`/continuity absent; recommendation modules present in wheel/sdist |
| Module size | All handwritten source modules remain below 300 nonblank/noncomment lines |

Earlier 37/62/97/135/167-test results are superseded by the above full-suite result. One
concurrent run timed out in a five-second CLI subprocess check while Docker builds
and mypy competed for resources; the sequential full-suite run above passed.
No host system packages were installed. Test fixtures remain synthetic.

## Authorized live API checks

The user explicitly authorized testing with the credential in `.env`. Nine
bounded GETs verified authentication, inventory, sampled findings/recommendations
and empty query analytics/optimization lists. No raw customer payloads, IDs, SQL
or credentials were retained. Populated proposals/plans were not encountered;
their coverage is synthetic. See [the API check receipt](api-checks-2026-11-10.md).
This does not certify all API roles, engines, agents or tenant isolation.

The new configuration/metric slice used **11 additional GETs**: bounded inventory,
configuration list/detail, metric catalog/series and two comparison windows,
followed by structural-only series diagnosis. Configuration records validated;
the comparison retained missing trend evidence. All 13 sampled series timestamps
were naive; initial rejection was superseded by the user's UTC confirmation.
No source payloads were retained. See the
[2026-11-11 receipt](api-checks-2026-11-11.md).

Nine further GETs validated UTC-normalized series (12 points), task list/detail
and historical capture aggregates. Sampled event/deadlock windows were empty;
populated record/detail coverage remains synthetic. Current OpenAPI raw hash is
unchanged. No raw payloads or identifiers were retained.

Three further GETs sampled inventory plus unfiltered/type-filtered schema reads.
Both schema snapshots had no completed run and returned partial `state=not_run`,
not healthy/empty success. Populated schema payloads and filtered-empty completed
runs remain covered synthetically. Static prompts/reference make no API calls.
See the [same aggregate receipt](api-checks-2026-11-11.md).

Five further GETs validated a bounded server list, matching detail with current
review/history and a safe typed evidence reference, and explicit fleet list with
independent accessible-inventory verification. No source URL was followed; detail
remained partial for privacy omissions. The public contract hash is unchanged.
See [the aggregate receipt](api-checks-2026-11-11.md). Client setup/health checks
were separate synthetic runs: [setup and verification](clients/local-setup.md).

## Docker status

**Resolved 2026-11-11T03:59Z.** With explicit user approval, `docker builder prune --all
--force` reclaimed **6.513 GB of unused build cache**. The existing images,
containers and volumes were not pruned or restarted. A direct container check
then reported 8.5 GB available on the 32 GB filesystem.

The dedicated checks and nonroot runtime images now build, and the artifacts
target exports the wheel and sdist to `dist/`. Current local image IDs (not
published registry digests):

- `mcp-releem:checks`: `sha256:36f8323df6e5c1090800693ad6b12451cbc27bf720417ad797b4e944da64caa8`
- `mcp-releem:local`: `sha256:3806bfd840bfab0817f061d85005f502b22f4f7b6622c490a0b4d10945445a8a`

Runtime verification used a synthetic credential and `--network none
--read-only`: package imports from installed site-packages, UID is 65532, and
neither `.env` nor the test tree is present in the image. An interactive stdio
smoke verified ten read-only tools, write/sensitive dispatch rejection, an explicit
network-isolated read failure and clean EOF shutdown. No customer credential was
mounted or API called during these Docker checks.

This supersedes the previous ENOSPC blocker and tmpfs-only build receipts. The
previous build-interpreter fix (`/opt/venv/bin/python`) is now verified through
the actual Docker artifacts target as well.

## Remaining work

Confirm interval bucket semantics before claiming arbitrary grouped-window
compatibility. Full interactive client onboarding and deployed hosted
credential-isolation checks remain open; Claude registration/health is
verified but tool/prompt/resource UI, Cursor onboarding and OAuth are not.
Opaque source payloads remain intentionally omitted. Large single detail results
may return a bounded size error; narrow history/list limits or sections.

No publishing, deployment, Git commit/push, remote writes, EXPLAIN execution or
database changes were performed. All branch changes remain uncommitted.

### Hosted candidate image receipt

- verified_at: `2026-11-11T07:07:38.618984+00:00`
- lock_sha256: `868280ad900a96909a4886d6e3334795046ee12cb281cae9e426ea3b80535ecc`
- image_id: `sha256:4d9f38b0ab9d42ed415b35d3e5777dcfead74c052c6341d486dd4a5e9f0775e1`
- hosted_image_id: `sha256:7fbb704718af968cfdcd22d625d5fabc9571fbb82065e842c4ef98fd3c47da23`
