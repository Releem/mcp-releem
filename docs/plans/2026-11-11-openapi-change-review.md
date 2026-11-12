# Releem OpenAPI update review — 2026-11-11

**Recommendation:** update the existing findings and query tools before the private
MVP release. Keep the ten-tool catalog, shared hosted/local core, read-only boundary
and current dependency pins. The new check-catalog endpoint is useful later but
is not needed to fix compatibility because server reports already embed its texts.

## Evidence and scope

Fetched public [OpenAPI](https://api2.dev.releem.com/openapi.json) at
**2026-11-11T14:53:11.859983Z**. Swagger UI was fetched separately and still points
to `/openapi.json`. The browser document reader could not open this origin; direct
HTTPS fetch succeeded without credentials. No authenticated API/customer endpoint,
model, database operation or remote change was used. Temporary synthetic container
probes exercised existing code; no product source or tests were changed.

| Identity | Baseline | Current |
| --- | --- | --- |
| Capture | [2026-11-10](evidence/releem-openapi-2026-11-10.json) | [2026-11-11](evidence/releem-openapi-2026-11-11.json) |
| Raw HTTP-body SHA256 | `dd6f9ae69c1bcd7e96e5d2cb4a004721d17eed0183dc98cb132442a2d0fa45d2` | `a2474b68c2b32f589bd24c820ab0a80df9200e888476aee78cb3c590c6b19e40` |
| OpenAPI / title / API version | 3.1.0 / Releem API / 1.0.0 | Unchanged |
| Operations | 45 | 46; one addition, no removal |
| Existing operations changed directly | — | 7, including 6 of our 26 diagnostic reads |
| Schema definitions changed/added | — | 4 changed, 2 added |

Complete [machine diff](evidence/releem-openapi-2026-11-11.diff.json),
[fetch metadata](evidence/releem-openapi-2026-11-11.metadata.json) and
[synthetic reproduction receipt](evidence/releem-openapi-2026-11-11.probes.json).
The unchanged API version does not identify the contract; use its content hash.
Documentation is evidence of the contract, not proof of deployed behavior or
self-hosted/agent/engine parity.

## Changes and implementation impact

### P0: findings can reject valid reports or label passing checks as failures

Affected: O14 `GET /v1/servers/{id}/details`, O15 `/health-checks`, O16
`/security-checks`. Schemas: ServerDetailsResponse, PublicHealthChecksResponse,
PublicSecurityChecksResponse and shared ServerHealthCheckResult.

`failed` and `description` in a check are now optional and nullable. New optional
nullable metadata: title, short_description, learn_more_url, severity and group.
The current `api.models.Check` requires bool/string, so valid null/omitted values
fail validation of the report. Extra metadata is ignored by its field allowlist.
Synthetic examples `{}` and `{"failed":null,"description":null}` validated against
the new named schema and were both rejected by the current adapter.

The `/details` description now promises **all** passing/failing checks rather than
only failed checks, in display order. Current `Diagnostics.findings` simply lists
all dictionary keys under `failed_summary` and emits `failed_summary_only`.
Reproduction: passing=false, failing=true and unevaluated=null were all reported
as failing, with result status `ok`. This is an actual local interpretation defect.

Fix nullable modeling and derive failure sets only from explicit `failed is True`.
Retain unknown/null/malformed states separately; neither unknown nor an empty/absent
snapshot proves health. Missing descriptions mean unavailable catalog text, not a
healthy result. Preserve security unknown/decode errors and existing 422 handling.
Recognized account checks can still fail with null values. Keep engine applicability
explicit and preserve upstream display order.

Expose bounded, redacted title/description/severity/group metadata through existing
findings. Keep raw documentation URLs omitted for MVP, with an availability flag;
do not fetch them. All upstream text remains untrusted. Existing global byte limits
and explicit size errors remain in force; test large enriched reports instead of
silently discarding material warnings or claiming complete coverage.

### P0: query analytics no longer documents period_days

Affected O23 `GET /v1/servers/{id}/query-analytics`. Response schema unchanged.

- Removed query parameter `period_days` (integer day presets).
- Added `period` string: positive integer with optional m/h/d; bare numbers are
  days, default1 day. Example10m. No upstream maximum is documented.
- Added optional `end_date`: requires start_date, must be later, overrides period;
  period must still be valid. All modes are half-open and use second precision.
- Explicit offsets override the timezone used for offset-free start/end dates.
- Error documentation replaces invalid_period_days with invalid_period and adds
  invalid_end_date; invalid_time_range/timezone/sort/order/filter remain documented.

Current QueryInput, server signature and QueryDiagnostics.parameters always send
period_days; the API allowlist has no period/end_date. A synthetic7-day call emits
period_days=7 and no period. Behavior of the deployed API on this undocumented
parameter is UNCONFIRMED: it may reject it or ignore it and use default1 day.
The current adapter does not verify requested duration against the returned end.
Do not claim a live silent-fallback reproduction.

Recommended compatibility: introduce canonical period/end_date; preserve existing
MCP period_days as a deprecated local alias mapped to `period="7d"`, never sent
upstream. Reject simultaneous non-null period and period_days. Keep UTC and
explicit-offset input policy; no timezone/identity redesign. Bound duration locally
to90 days and bounded period-text length, clearly labeling this as an adapter cap.
Validate whole-second bounds, explicit end precedence and effective response window.
Rolling windows retain actual upstream boundaries; do not compare end to an exact
local clock instant. Add fixed sanitized query-error mappings, never backend text.

### P1: current configuration means newest state across configurations

O17 `GET /v1/servers/{id}/configurations?latest=true` now describes the server's
newest state (first history row), rather than the current state of its newest
logical configuration. Same correction applies to O06 `GET /v1/servers/configurations`.
No input/response shape changed; our O17 wire request already uses latest=true.
Correct wording and test an older logical configuration receiving a newer state.
Continue distinguishing configuration_status_id from configuration_id and actual
applied database state. O06 remains deferred: owner-only/unbounded fleet coverage
is not equivalent to accessible-server inventory.

### P1: metric-average windows are explicitly half-open

O26 `GET /v1/servers/{id}/metrics/averages` now documents inclusive start/exclusive
end and non-finite values converted to null. Parameter names/types/requiredness,
366-day cap and response shapes are unchanged. Current averages models already
accept null. Replace `upstream boundary inclusion unspecified` in comparison
output/reference with `[start_time,end_time)`; keep null/zero/unit/sample caveats.
This does not resolve raw metric-series bucket anchoring; do not relax that policy.

### Optional/later: check catalog

New O46 `GET /v1/checks`; authenticated by the existing API-token scheme. Optional
`type=health|security`, `dbms=mysql|postgresql`; mysql includes MariaDB. Response
`{items:[...]}` uses CheckCatalogItem: required type/dbms/key/title/description,
nullable optional short_description/learn_more_url/severity/group. No pagination,
limit, immutable snapshot, role scope or versioning is documented. Identity is
**(type,dbms,key)**, not key alone. Rows are ordered by type/family/display order.

Do not add an MVP MCP tool or automatic enrichment request: inline server reports
already include these texts. Keep the current static reference resource static.
If later added, use a dedicated bounded read tool with explicit family/filter,
truncation and errors. Do not use this global catalog as server authorization,
identity introspection or a substitute for per-request accessible-server checks.

## Unchanged boundaries

Authentication/security schemes, root identity/base URLs and all write/chat/admin
contracts are unchanged. No new upstream identity integration or permission claim
is justified. Recommendations, saved optimizations/proposals, metric series/catalog,
events, deadlocks, captures, tasks and schema findings are structurally unchanged.
Twenty of26 implemented reads have no changed operation definition. No dependency,
transport, Docker/Cloudflare or write-capability change is required by this update.

## Complete operation delta/coverage inventory

Baseline O01–O45 IDs remain stable; append O46. The baseline inventory supplies
unchanged per-operation details. Current change analysis above supersedes its
outdated findings/query/window/configuration wording.

| ID | Method/path | Existing scope / recommendation | Contract delta |
| --- | --- | --- | --- |
| O01 | `GET /v1/servers/recommendations` | MVP: `recommendations` | Unchanged |
| O02 | `GET /v1/servers/{id}/recommendations` | MVP: `recommendations` | Unchanged |
| O03 | `GET /v1/servers/{id}/recommendations/{recommendation_id}` | MVP: `recommendations` | Unchanged |
| O04 | `PATCH /v1/servers/{id}/recommendations/{recommendation_id}` | Later: `recommendation_workflow` | Unchanged |
| O05 | `GET /v1/servers` | MVP: `servers` | Unchanged |
| O06 | `GET /v1/servers/configurations` | Later: `fleet_configurations` | Changed — see analysis |
| O07 | `GET /v1/servers/{id}` | MVP: `server_findings` | Unchanged |
| O08 | `PATCH /v1/servers/{id}` | Excluded: `administration` | Unchanged |
| O09 | `DELETE /v1/servers/{id}` | Excluded: `administration` | Unchanged |
| O10 | `POST /v1/servers/{id}/chat` | Excluded: `chat` | Unchanged |
| O11 | `POST /v1/servers/{id}/chat/stream` | Excluded: `chat` | Unchanged |
| O12 | `GET /v1/servers/{id}/events` | MVP: `events` | Unchanged |
| O13 | `GET /v1/servers/{id}/events/{event_id}` | MVP: `events` | Unchanged |
| O14 | `GET /v1/servers/{id}/details` | MVP: `server_findings` | Changed — see analysis |
| O15 | `GET /v1/servers/{id}/health-checks` | MVP: `server_findings` | Changed — see analysis |
| O16 | `GET /v1/servers/{id}/security-checks` | MVP: `server_findings` | Changed — see analysis |
| O17 | `GET /v1/servers/{id}/configurations` | MVP: `configurations` | Changed — see analysis |
| O18 | `GET /v1/servers/{id}/configurations/{configuration_status_id}` | MVP: `configurations` | Unchanged |
| O19 | `GET /v1/servers/{id}/query-optimizations` | MVP: `query_evidence` | Unchanged |
| O20 | `POST /v1/servers/{id}/query-optimizations` | Later: `optimization_submit` | Unchanged |
| O21 | `GET /v1/servers/{id}/query-optimizations/{optimization_id}` | MVP: `query_evidence` | Unchanged |
| O22 | `PATCH /v1/servers/{id}/query-optimizations/{optimization_id}` | Later: `optimization_workflow` | Unchanged |
| O23 | `GET /v1/servers/{id}/query-analytics` | MVP: `query_evidence` | Changed — see analysis |
| O24 | `GET /v1/servers/{id}/query-analytics/{schema_name}/{query_id}/recommendations` | MVP: `query_evidence` | Unchanged |
| O25 | `GET /v1/servers/{id}/metrics` | MVP: `metrics` | Unchanged |
| O26 | `GET /v1/servers/{id}/metrics/averages` | MVP: `metrics` | Changed — see analysis |
| O27 | `GET /v1/servers/{id}/metrics/byName/{metric_name}` | MVP: `metrics` | Unchanged |
| O28 | `GET /v1/servers/{id}/metrics/byId/{itemid}` | MVP: `metrics` | Unchanged |
| O29 | `GET /v1/servers/{id}/deadlocks` | MVP: `deadlocks` | Unchanged |
| O30 | `GET /v1/servers/{id}/deadlocks/{deadlock_id}` | MVP: `deadlocks` | Unchanged |
| O31 | `GET /v1/servers/{id}/tasks` | MVP: `task_outcomes` | Unchanged |
| O32 | `POST /v1/servers/{id}/tasks` | Later: `agent_tasks` | Unchanged |
| O33 | `GET /v1/servers/{id}/tasks/{task_id}` | MVP: `task_outcomes` | Unchanged |
| O34 | `GET /v1/servers/{id}/processlist` | MVP: `captured_sessions` | Unchanged |
| O35 | `GET /v1/servers/{id}/schema-checks` | MVP: `server_findings` | Unchanged |
| O36 | `POST /v1/servers/{id}/query-optimizations/custom` | Later: `optimization_submit` | Unchanged |
| O37 | `PUT /v1/servers/{id}/memory-limit` | Later: `configuration_changes` | Unchanged |
| O38 | `PUT /v1/servers/{id}/mysql-config` | Later: `configuration_changes` | Unchanged |
| O39 | `GET /v1/metrics` | Excluded: `legacy_metrics` | Unchanged |
| O40 | `GET /v1/metrics/{metric_name}` | Excluded: `legacy_metrics` | Unchanged |
| O41 | `POST /v1/customers` | Excluded: `customer_administration` | Unchanged |
| O42 | `GET /v1/customers` | Excluded: `customer_administration` | Unchanged |
| O43 | `GET /v1/customers/{id}` | Excluded: `customer_administration` | Unchanged |
| O44 | `PATCH /v1/customers/{id}` | Excluded: `customer_administration` | Unchanged |
| O45 | `DELETE /v1/customers/{id}` | Excluded: `customer_administration` | Unchanged |
| O46 | `GET /v1/checks` | Later: optional catalog lookup | Added; no MVP tool needed |
