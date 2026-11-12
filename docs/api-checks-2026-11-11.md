# Configuration and metric API check receipt

Checked **2026-11-11T04:14:19Z** using the owner-authorized development API origin
and credential supplied in `.env`. Read-only container execution; the key was
mounted read-only and not placed in commands, images or logs. Only aggregate
results were retained. No customer identifiers, names, configuration values,
telemetry payloads or fixtures are stored here.

The current public OpenAPI capture was rechecked on 2026-11-11. Raw SHA-256
`dd6f9ae69c1bcd7e96e5d2cb4a004721d17eed0183dc98cb132442a2d0fa45d2`
matches the [2026-11-10 capture](plans/evidence/releem-openapi-2026-11-10.json):
OpenAPI 3.1.0, Releem API 1.0.0, 45 operations.

Eight bounded GETs exercised one sampled accessible server:

| Check | Observed result |
|---|---|
| Inventory | Authentication and server listing validated |
| Configuration history, limit 2 | Two state rows; partial, no total/cursor assumed |
| Configuration state detail | Matching state/server; partial because sensitive values and untyped metrics were omitted |
| Metric catalog, limit 1 | One retained row; truncation explicit |
| Series, one-hour window, 5-minute average | Rejected as invalid source time; no samples returned to the model |
| Comparison, current and previous one-hour windows | Partial: missing hourly trend data retained, null delta reason visible |

Three additional GETs isolated the series mismatch without printing source data:
inventory, server metric catalog, and a single series. The selected metric name
and point count matched, and its 13 returned timestamps were all **naive** (no
timezone offset). The JSON model otherwise validated. This conflicts with the
OpenAPI date-time example carrying `Z`. Unlike the averages response, the series
timestamp description does not explicitly establish UTC for naive values.

At that point the adapter returned sanitized `metric_timezone_unconfirmed`.
This historical limitation is superseded by the owner-confirmed UTC semantics
and subsequent verification below. Interval bucket anchoring remains unspecified.

Initial total: **11 GETs**, no retries, API writes, database operations, customer fixtures
or persisted payloads. This sample does not certify all metrics, engines, roles,
agents, sharing rules, deployments or hosted tenant isolation.

## UTC confirmation and incident continuation

On 2026-11-11 the owner explicitly confirmed the timezone is UTC. The adapter
normalizes naive upstream series timestamps to UTC and adds
`source_timezone_utc`; caller boundaries still require explicit offsets.

At **2026-11-11T04:30:01Z**, nine additional bounded GETs checked one sampled
accessible server. Sensitive detail was enabled only in the in-memory test
configuration; `.env` was not edited. Raw payloads were neither printed nor saved.

| Check | Observed result |
|---|---|
| Inventory/catalog | Validated for explicit sampled server |
| UTC series with aligned one-hour window and 5m average | **ok**, 12 points; timezone provenance warning retained |
| Event list, limit 2, preceding hour | **no_data**; pagination warning retained |
| Deadlock list, limit 2, preceding hour | **no_data**; bounded-history warning retained |
| Task list/detail | Two summaries and one matching detail; privacy omissions explicit |
| Latest captured sessions | One historical aggregate; session details omitted |

Populated event/deadlock detail coverage remains synthetic. Grouped series were
verified only with aligned boundaries; an upstream bucket label outside the exact
window still fails explicitly. No bucket anchoring convention is inferred.
Current public OpenAPI was rechecked and its hash remains unchanged.

Cumulative checks for this receipt: **20 GETs**. No API writes, capture creation,
task submissions, automatic retries, database operations or customer fixtures.

## Schema snapshot continuation

At **2026-11-11T04:43:49Z**, three additional bounded GETs read the inventory,
one sampled server's schema snapshot, and the same snapshot filtered by canonical
`unused_index`. Both schema reads returned a null completed-run timestamp and no
rows. The adapter returned **partial**, `state=not_run`, incomplete coverage and
`schema_snapshot_absent`; it did not infer a healthy schema. No customer values,
identifiers or raw payloads were printed or retained. Populated schema checks,
filtered-empty completed runs, decode errors, unknown flags and scope attacks
remain covered by synthetic tests.

Cumulative checks for this receipt are now **23 GETs**. Static workflow prompts
and `releem://reference` were verified offline and make no upstream calls.

## Recommendation detail and explicit fleet continuation

At **2026-11-11T05:10:56Z**, five additional bounded GETs sampled server
inventory, one server recommendation page, matching detail, then independent
inventory validation and an explicit fleet page. No linked evidence URL was
fetched. Lists validated and returned one row each. Detail retained a current
review, one historical review and two status events; it was **partial** because
opaque review/input payloads and actor identity/reason text were omitted. Its
source reference mapped to a validated typed read. Naive source times were
normalized to confirmed UTC with warnings. No customer identifiers, payloads,
URLs, review text, SQL or credentials were printed or retained.

The current public OpenAPI was fetched again and retains the original raw
SHA-256 and 45-operation identity. Cumulative authorized customer GETs in this
receipt: **28**. No mutations, follow-up evidence reads, database operations,
automatic retries, customer fixtures or model calls were performed.

## Hosted authentication prerequisite

On 2026-11-11, three additional bounded `GET /v1/servers` probes returned 401
without a key, 401 with a synthetic invalid key, and 200 with the configured valid
key; the successful inventory validated. No response records, IDs or secrets were
printed or retained. Cumulative authorized customer API checks: **31 GETs**.
This verifies current missing/invalid/valid behavior only. Real key revocation,
propagation timing, role granularity and two-account isolation remain UNCONFIRMED;
revocation and concurrent customer tests use synthetic responses offline.
