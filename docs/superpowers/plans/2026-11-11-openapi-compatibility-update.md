# OpenAPI compatibility update implementation plan

> Execute the approved plan task-by-task with review checkpoints. This artifact is
> originally planning only; the user subsequently authorized implementation with
> “implement update.” Commit, publication and deployment remain unauthorized. Retain existing uncommitted work and historical evidence.

**Goal:** make the ten existing diagnostic tools correctly consume the2026-11-11
46-operation contract before releasing the private MVP.

**Architecture:** retain the shared Python diagnostic core, closed GET registry,
per-request hosted credentials/ownership, local stdio and authenticated HTTP. Adapt
only affected models, query inputs/serialization, findings presentation and contract
semantics. New GET /v1/checks is deferred; no additional MCP tool or implicit lookup.

**Tech stack:** unchanged locked Python3.12, MCP2.3.0, httpx2/Pydantic; existing
container workflow and hardened Alpine runtime. [Review](../../plans/2026-11-11-openapi-change-review.md)
and [captured contract](../../plans/evidence/releem-openapi-2026-11-11.json).

## Task1 — findings nullable results and truthful summaries (P0)

Files: `src/mcp_releem/api/models.py`, `core/check_reports.py`,
`core/diagnostics.py`; tests `tests/test_diagnostics.py`, new
`tests/test_check_metadata.py`. Extract a small findings-summary helper if needed
to keep modules<=300 relevant lines; no unrelated restructuring.

- [x] First add failing synthetic cases: full report with null and omitted
  failed/description; `/details` mixed passing/failing/null/missing statuses;
  missing/empty snapshots; unknown/decode-error security state; account failure
  with value=null; malformed bool string; unknown severity; both engine families.
- [x] Observe existing failures: nullable Check validation and all detail keys
  wrongly included in failed_summary. Use no customer fixtures or endpoints.
- [x] Extend current upstream Check model with optional nullable fields:

```python
failed: bool | None = None
value: Any = None
description: str | None = None
title: str | None = None
short_description: str | None = None
learn_more_url: str | None = None
severity: str | None = None
group: str | None = None
```

  Keep strict types/extra ignore/non-finite rejection. Unknown severity text is
  preserved/redacted with a caveat rather than inventing a severity or discarding
  a known failure. A null description does not erase the check's identity/result.
- [x] Keep `failed_summary` for client compatibility, containing only explicit
  true statuses. Preserve null/absent/malformed results in a separate unknown
  summary and mark coverage partial with fixed warnings. Old scalar-only detail
  entries must not be assumed failed or passed; use unknown/source-shape caveats.
  Correct/remove failed_summary_only warning and stale comments. No implicit
  additional health/security calls when summary-only was selected.
- [x] Present bounded allowlisted metadata, preserve check display order and
  numeric/null value rules. Discard raw learn_more_url from presentation and
  expose `documentation_reference_present`; never follow it. Apply existing
  redaction and total-output budgets. Preserve unknown/decode/stale/missing warnings
  even when metadata is missing/clipped. Oversize reports return explicit size
  errors; do not silently trim failures. No new input pagination is required yet.
- [x] Verify summary-only, full health/security and mixed-component failure cases.
  Timestamp absence/unknown check result must never become a healthy assertion.

Acceptance: passing/unknown checks never appear as failures; valid new reports
parse; unknown/absent evidence stays visible. Upstream arbitrary detail JSON stays
private. Existing report shape and ten-tool discovery remain compatible.

## Task2 — canonical query periods and explicit windows (P0)

Files: `api/operations.py`, `api/client.py`, `core/query_inputs.py`,
`core/queries.py`, `server.py`; tests `tests/test_queries.py`,
`tests/test_query_limits.py`, `tests/test_surface.py`, new
`tests/test_query_windows.py`. If server.py exceeds300 relevant lines, move query
registration cohesively to `src/mcp_releem/query_tools.py` and retain its public tool.

- [x] Add failing outbound assertions: legacy7-day input must serialize period=7d
  and no period_days; canonical10m/2h/7d/bare7; paired start/end; end without start;
  equal/reversed/over90-day windows; unsupported suffix, zero, negative, bool/int
  supplied to canonical string, excessive digits, nonzero fractional seconds,
  invalid offsets, conflicting alias/canonical inputs and view-inapplicable fields.
- [x] Introduce tool/model fields `period: str | None = None`,
  `end_date: str | None = None`; make legacy
  `period_days: Literal[1,7,14,30,60,90] | None = None`. Effective default1d remains.
  Keep period_days as a deprecated MCP-only alias, not an upstream parameter.
  Reject both non-null selectors; legacy bool/float are not valid day counts.
- [x] Implement one normalization/validation path: canonical positive integer text
  with optional lowercase m/h/d (bare means days), no whitespace/leading-zero
  noncanonical forms, max16 characters and <=90d after conversion. These are
  explicit adapter bounds, not claims of upstream restrictions. Check period even
  when explicit end overrides it. UTC-only timezone and explicit offset-aware dates
  remain the supported subset; reuse core.diagnostic_inputs.instant for UTC/overflow
  normalization where suitable, rather than adding a competing parser.
- [x] Require end_date to have start_date, end>start, whole-second precision and
  <=90d span. End overrides period as documented; emit an override caveat when
  duration was explicitly supplied. Retain actual effective window in output.
- [x] Update registry query keys to period/start_date/end_date/timezone/sort/order/
  schema/filter/limit; remove outbound period_days. Build the serializer explicitly:
  map alias7 to period=7d, insert default1d when neither supplied, exclude aliases
  and non-analytics fields. Do not inject an implicit legacy default from the MCP
  function signature when canonical period was provided.
- [x] Validate effective response: strict requested start/end equality for explicit
  bounds, duration/end consistency for anchored periods, duration consistency for
  rolling periods without an exact local-clock end assertion. Normalize source
  naive timestamps under confirmedUTC with provenance caveat. Mismatched explicit
  windows fail with sanitized invalid_source_data; do not return a wrong-window
  ranking as successful. Counts/percentages/units and filtered denominators remain.
- [x] Add fixed sanitized mappings for documented query400 codes, including
  invalid_period/invalid_end_date/invalid_time_range. Never expose backend error
  messages/details, raw SQL/filters or credentials. No fallback retry using old
  parameters and no optimization/EXPLAIN submission.
- [x] Update advertised schema and real MCP dispatch together; test direct core,
  stdio and authenticated HTTP with canonical/legacy calls and ambiguous inputs.

Example intended calls:

```json
{"server_id":"101","view":"analytics","period":"10m","limit":10}
{"server_id":"101","view":"analytics","start_date":"2026-11-11T10:00:00Z","end_date":"2026-11-11T10:10:00Z"}
{"server_id":"101","view":"analytics","period_days":7}
```

Acceptance: current API only receives documented parameters, legacy MCP callers
retain their day duration, input/response windows cannot silently disagree.

## Task3 — documented configuration/average semantics (P1, same patch)

Files: `core/metric_comparison.py`, configuration/metric tool docstrings as needed,
`README.md`; tests `tests/test_configurations.py`, `tests/test_metrics.py`.

- [x] Add regression where an older logical configuration has the newest status
  timestamp. latest=true must preserve the API's first/newest state without sorting
  by configuration_id or claiming it is applied/effective. Keep state ownership/IDs.
- [x] Correct newest-configuration wording to server's current/newest state in
  documentation. O06 fleet configurations remains deferred; no new wire call.
- [x] Replace average comparison `window_bounds` with `[start_time,end_time)`;
  verify adjacent windows have the documented boundary convention. Keep null
  averages/null deltas/zero baseline/unit/identity checks and hourly sampling caveats.
- [x] Test finite values and nulls; keep rejecting nonstandard NaN/Infinity JSON.
  Do not generalize averages' boundary clarification into metric-series bucket
  anchoring or remove existing hour-alignment/duration bounds.

## Task4 — contract evidence and offline regression guard (P1)

Files: `docs/plans/api-coverage.md`, `docs/plans/source-register.md`,
`tools/release/provenance.py`, `Dockerfile`, `.dockerignore`, new
`tests/test_openapi_contract.py`.

- [x] Promote the captured2026-11-11 contract as the active reference; keep the old
  raw capture and diff immutable. Record both hashes and stable IDs O01–O45 plus
  O46. The new API still calls itself1.0.0; version-string-only checks are insufficient.
- [x] Update operation details for the seven changed operations and the new catalog;
  keep current implemented reads26/MCP tools10. O46 is later/reference-only and
  must not automatically enter the outbound registry or tools/resources discovery.
- [x] Add offline checks that every allowlisted GET route maps to the captured
  contract (normalize explicit path placeholder names), and allowlisted query keys
  are a subset of documented parameters. Confirm read-only dispatch still rejects
  mutation names/methods; no arbitrary route generation from OpenAPI.
- [x] Make the active public capture available only to the checks stage: add exact
  parent/path allowances in .dockerignore and COPY the2026-11-11 JSON into the
  checks image at docs/plans/evidence/. Do not broadly include docs, env files,
  raw customer fixtures or release evidence in runtime/build context. The current
  Docker context excludes docs, so tests cannot simply read it without this step.
- [x] Validate representative new Check instances against the captured named schema
  as well as adapter models; explicitly exercise nullable fields despite the report
  map's loose additionalProperties schema. Do not mechanically expose all response
  properties or validate only the top-level generic object.
- [x] Include the active new capture in source provenance (retain old evidence).
  Keep network fetching out of offline pytest; future drift refresh is an explicit
  documentation-fetch task, not an automatic customer endpoint call.

## Task5 — workflows, client examples and verification (P1)

Files: `workflows.py`, `README.md`, `docs/implementation-status.md`,
`docs/clients/local-setup.md`, `CHANGELOG.md`, release notes; tests
`tests/test_workflows.py`, `tests/test_workflow_surface.py`,
`tools/release/{synthetic_api,local_journey}.py` where fixtures exercise new fields.

- [x] Replace period_days-only guidance with canonical periods/explicit end mode,
  UTC/second precision/local caps and backward-compatible alias caveat. Explain
  checks' nullable status/catalog metadata and averages' half-open boundaries.
- [x] Keep static prompts/reference static; fix their existing stale stdio-only
  sentence to match the already-implemented two profiles. No live catalog resource,
  implicit lookup, engine guessing or automatic documentation URL fetch.
- [x] Add new report metadata/null states and canonical query window to synthetic
  installed journeys; use fixed expected request/response cases independent of the
  production period parser. Check two-customer ownership/revocation, invalid inputs,
  missing snapshots, redaction and output limits over both SDK protocol modes.
- [x] Run the existing full container verification, then the security-enabled gate:

```bash
RELEEM_RELEASE_SECURITY=true bash scripts/check-release.sh
```

  It must pass locked builds, format/lint/mypy, offline tests, stdio/HTTP, exact
  wheel install, Compose recovery, checksums/source fingerprint and image/Python
  advisory gates. No host dependency installation or real database operations.
- [x] Recheck isolated client discovery/typed call schemas; record CLI connection
  evidence separately from model-directed UI testing. No customer data to models.
- [x] Refresh candidate/receipt after implementation; old272-test/security receipts
  remain historical and do not certify the new contract compatibility. Keep0.1.0
  while unreleased; no commit/push/publish/deploy without separate authorization.

## Optional later catalog task — not a release dependency

Only if users need check descriptions without a selected server: design a dedicated
bounded read against O46 with explicit type/dbms and identity(type,dbms,key), source
ordering, sanitization, URL policy and truncation. It must use the caller's key,
require hosted authentication and never replace server ownership validation.
There is no upstream pagination/limit contract to rely on. Do not implement it as
part of this compatibility patch or add a generic HTTP tool.

## Order, effort and open facts

Prioritize Tasks1–2 (release blockers), then3–5 in the same reviewable compatibility
patch. Estimate1–2 engineering days including synthetic regressions and independent
review, assuming no further contract drift. No dependency/runtime migration is needed.

UNCONFIRMED: deployed treatment of period_days, rollout/backward compatibility,
maximum upstream query duration and actual size/order of new engine-specific
reports. These do not block useful implementation: serialize the documented
parameter, keep explicit local bounds, and test synthetic contracts. Any later
bounded live read uses the existing authorized test environment/secret handling;
this planning task made none. Other release/client/host gates remain separate.

## Execution checkpoint — 2026-11-11T16:13Z

Tasks1–4 implemented and independently reviewed. Task5 docs/workflows and synthetic
canonical/legacy/end-window journeys implemented;343 offline tests, Ruff and strict
mypy61 sources pass. Review-discovered malformed-offset/submicrosecond truncation
was reproduced then fixed with one shared lexical query-time parser for user/source
bounds. Full security-enabled release verification is running; no customer calls.

Completion — 2026-11-11T16:18Z: all five tasks complete. Exact full security-enabled
release passes343 tests19.87s/Ruff93/mypy61/22checksums;0 HIGH/CRITICAL image findings,
29Python packages0known vulnerabilities. Synthetic installed journeys include
canonical/legacy/explicit-end calls in both SDK modes; isolated Claude HTTP health
passes against refreshed demo. [Receipt](../../releases/evidence/2026-11-11-openapi-update.json).
No customer API/model/DB operations, commit, publication or deployment.
