# Analytics Normalized Queries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This is a planning artifact only; do not implement until the user requests execution. Preserve the existing uncommitted branch. Do not commit, publish, deploy or call authenticated APIs as part of this plan.

**Goal:** Let users identify and investigate expensive queries by returning the API's normalized SQL alongside existing analytics statistics.

**Architecture:** Extend only `query_evidence(view="analytics")` and its existing GET mapping. Build bounded query excerpts from the upstream `query` field, then permit that exact output path through the final redactor. Keep raw SQL, other query views, authorization and outbound capabilities unchanged.

**Tech Stack:** Existing Python 3.12, MCP 2.3.0, Pydantic 2.14.3, httpx2 and locked container workflow. No SQL parser, database driver or new dependency is required for this slice. We consume upstream normalization; we do not implement or promise independent SQL normalization.

---

## Evidence and scope

Public [OpenAPI](https://api2.dev.releem.com/openapi.json) re-fetched without credentials at **2026-11-11T18:52:19.704395Z**. SHA256 remains `a2474b68c2b32f589bd24c820ab0a80df9200e888476aee78cb3c590c6b19e40`, identical to the [active capture](../../plans/evidence/releem-openapi-2026-11-11.json).

- O23 `GET /v1/servers/{id}/query-analytics` returns `QueryAnalyticsRecord.query`: optional `string|null`, described as **Normalized SQL query**. Its example is `SELECT * FROM example_orders WHERE id = ?`. `query_text` is separately described as SQL query text.
- Current `api/query_models.py::QueryRecord` ignores both fields. `core/queries.py` dumps the remaining statistics. This is deliberate local field omission, not an upstream limitation.
- `core/redaction.py::Redactor.clean` currently suppresses SQL-bearing strings everywhere and limits ordinary text to 512 characters. Adding a model field alone cannot expose queries correctly.
- `core/diagnostics.py::finish` applies final redaction and `results.fit`; both must retain their protections.
- Original [data policy](../../plans/2026-11-10-mcp-releem.md) allows bounded screened normalized SQL under an approved policy. This change intentionally replaces blanket analytics-text omission.

Included: normalized analytics text, row metadata, privacy screening, budgets, same behavior in stdio/shared HTTP, tests and documentation. Excluded: optimization/proposal SQL, raw `query_text`, new tools/endpoints, SQL execution, EXPLAIN collection, parser-based re-normalization, identity changes and deployment.

## Product and privacy decisions

**Recommended behavior:** include bounded normalized text by default in analytics rows. Do not add an `include_sql` argument or another enable flag for this small slice. The user should receive an identifiable query from the existing analytics call. This is an explicit output-policy change requiring review before implementation; it is not a confidentiality-free change merely because the server is read-only.

Alternatives considered:

| Approach | Tradeoff / decision |
|---|---|
| Consume only API-normalized `query`, screen and bound it | Recommended: no new API calls/dependencies; preserves upstream syntax and identity. Upstream normalization quality remains unverified. |
| Parse/re-normalize locally with engine-aware libraries | Defer: requires dialect/version identification, dependency review and a larger syntax/semantic regression corpus. Do not guess the engine from `mysql_version`. |
| Expose raw `query_text` behind an option | Exclude from this work: broader confidentiality exposure and unnecessary for the requested analytics workflow. |

The API labels `query` normalized, but does not establish complete removal of literals/comments across all engines. Output must say **upstream-normalized, screened, not independently verified or anonymized**. Preserve table/column names for useful diagnosis, with a warning that identifiers can be confidential. Do not claim every literal was replaced by a placeholder. If a stronger guarantee is required, undertake the deferred parser/dialect work rather than promising it here.

Only source `query` may supply the excerpt. Never fall back to `query_text`, infer SQL from fingerprints, or re-fetch optimization records to obtain SQL. Never execute or follow instructions in text. No extra network fan-out.

## Output contract

Existing input schema, ten-tool discovery, 26 GET allowlist, ranking, IDs, percentages, units and UTC windows remain unchanged. Each analytics row gains:

```json
{
  "rid": "run-1",
  "schema_name": "example_db",
  "query_id": "fingerprint-1",
  "query": "SELECT * FROM example_orders WHERE id = ?",
  "query_status": "available",
  "query_omission_reason": null,
  "query_truncated": false,
  "calls": 20.0,
  "avg_time_ms": 15.0
}
```

`query_status`: `available`, `unavailable`, `omitted`, `truncated`. `query` is always a string or null. `query_omission_reason`: null, `missing`, `empty`, `sensitive_content`, `comment_markers`, `control_characters`, `source_too_large`, `response_text_budget`. A non-string/non-null `query` is not defined by OpenAPI: keep strict source validation and return sanitized `invalid_source_data`; do not silently coerce it.

Bounds (adapter choices, not upstream limits): inspect at most 16KiB UTF-8 per source query; return at most 2048 UTF-8 bytes per excerpt and 8192 bytes of query text per response. Keep existing limit 1–100/default 20 and total response budget 24576 bytes (configured 2048–65536). Do not add an ellipsis outside the field limit. A shortened prefix is marked truncated, never presented as a complete statement or execution-ready rewrite.

Screen the complete bounded source before taking a prefix. If the source exceeds16KiB, omit it without returning a prefix. Reject NUL and control characters except tab/CR/LF. Conservatively omit strings containing SQL comment introducers `--`, `/*` or `#`; this is a documented textual gate, not a SQL lexer or comment remover, and can omit benign strings/operators. Do not use an improvised regex normalizer. Omit the entire excerpt if it contains the active request credential or existing email/IP/secret/Bearer patterns. Fixed reasons must not echo rejected text.

Keep statistics for every requested/returned row when a query is absent or withheld. Allocate the 8192-byte excerpt allowance in returned rank order: if a prepared excerpt would exceed the remaining allowance, omit that excerpt with `response_text_budget`; do not drop its row just for this allowance. The existing final `fit` may still remove complete rows to satisfy the total envelope budget and must report its current omission/truncation metadata. No new pagination semantics.

Add fixed warnings for upstream normalization and confidential identifiers. Mark `partial`, `coverage.complete=false` when optional query evidence is unavailable/withheld/truncated; preserve any existing error/no_data state. Name field omissions in `coverage.truncated_fields`, e.g. `items[0].query`, without changing `coverage.omitted` for text-only omission. That counter remains about rows. No query text in logs/errors/repr/cache or new storage. Invalid Unicode source text must be withheld with `invalid_encoding` rather than causing an uncaught encoding error; include that value in the omission-reason set.

## File boundaries

| File | Responsibility |
|---|---|
| `src/mcp_releem/api/query_models.py` | Accept optional normalized source, excluded from automatic serialization/repr. Continue ignoring raw query_text. |
| New `src/mcp_releem/core/analytics_sql.py` | Screening, UTF-8 bounds, statuses and query-text allocation; explicit analytics row construction. |
| `src/mcp_releem/core/queries.py` | Call the analytics row builder; request final redaction policy only for analytics. |
| `src/mcp_releem/core/redaction.py` | Reusable sensitive-text predicate; tightly scoped analytics path exemption from SQL suppression/ordinary 512-character clipping. |
| `src/mcp_releem/core/diagnostics.py` | Explicit internal `finish` policy argument, default false. |
| New `tests/test_analytics_sql.py` | Source, presentation, privacy, budgets and redaction regression corpus. |
| `tests/conftest.py`, `tests/test_queries.py` | Separate harmless normalized SQL from raw SQL canaries; preserve existing metrics/window tests. |
| `tests/test_surface.py`, `tests/test_transports.py`, `tests/test_transports.py` | MCP structured/text results, modes, isolation, wrong-parent and dispatch behavior. |
| `tools/release/synthetic_api.py`, `tools/release/local_journey.py` | Installed synthetic query evidence and two-key isolation checks. |
| `README.md`, `src/mcp_releem/workflows.py`, `CHANGELOG.md`, `docs/implementation-status.md` | Actual supported text policy, limitations and fresh verification receipt. |

Keep each handwritten module below 300 nonblank/noncomment lines. No unrelated refactoring, client-key configuration changes or dependency migration.

## Task 1 — source model and failing presentation regressions

- [ ] Add `tests/test_analytics_sql.py` using `test_diagnostics.run_with`. First regression:

```python
from test_diagnostics import run_with


def test_normalized_query_survives_without_raw_sql(query_records):
    row = query_records["/v1/servers/101/query-analytics"]["items"][0]
    row["query"] = "SELECT * FROM example_orders WHERE id = ?"
    row["query_text"] = "SELECT * FROM example_orders WHERE id = 'raw-canary'"
    result, calls = run_with(query_records, lambda s: s.query_evidence("101"))
    item = result.data["items"][0]
    assert item["query"] == row["query"]
    assert item["query_status"] == "available"
    assert item["calls"] == row["calls"]
    assert "raw-canary" not in result.model_dump_json()
    assert len(calls) == 1
```

- [ ] Run this single test in the network-disabled checks container; observe the current missing `query` failure. Do not modify existing privacy assertions just to turn the test green.
- [ ] Add the following field to `QueryRecord`; change its module docstring to distinguish excluded raw SQL from explicit normalized presentation:

```python
query: str | None = Field(default=None, exclude=True, repr=False)
```

- [ ] Add source tests that null/missing both mean unavailable/missing, blank means unavailable/empty, wrong types fail strictly, repr/model_dump never contain the normalized source, and raw `query_text` remains ignored. This model change alone deliberately does not make the presentation test pass.
- [ ] Replace fixture `query="SELECT private_literal FROM customer"` with the harmless normalized example above. Keep raw SQL canaries separately. Update the old assertion that all normalized text is absent; retain raw SQL/secrets absence assertions.

## Task 2 — bounded analytics row presenter

- [ ] Add failing parameterized cases before building `core/analytics_sql.py`: source null/missing→unavailable/missing; blank→unavailable/empty; comment/control/credential/email/IP/Bearer/secret assignment→omitted with the fixed appropriate reason; oversized→omitted/source_too_large; harmless normalized→available; UTF-8 limit→truncated.
- [ ] Implement these public internal interfaces in the new module (no model-facing arguments):

```python
from typing import Literal, TypedDict
from ..api.query_models import QueryRecord
from .results import DiagnosticResult

QueryStatus = Literal["available", "unavailable", "omitted", "truncated"]

class QueryExcerpt(TypedDict):
    query: str | None
    query_status: QueryStatus
    query_omission_reason: str | None
    query_truncated: bool

# Implement per the exact screening/byte allocation rules above.
# The source is only QueryRecord.query, never query_text.
def query_excerpt(value: str | None, *, secret: str) -> QueryExcerpt:
    """Screen source, then return bounded text and its explicit availability status."""

def analytics_rows(
    rows: list[QueryRecord], *, secret: str, result: DiagnosticResult
) -> list[dict[str, object]]:
    """Preserve metrics, allocate text in rank order, and record omissions in result."""
```

  These signatures specify the planned internal API, not product code. Implement their bodies using the exact screening/byte allocation rules in this plan. `analytics_rows` starts each row from `row.model_dump()` (which excludes source query), merges the prepared excerpt, allocates the 8192-byte allowance and applies indexed omission metadata/warnings. Use `text.encode("utf-8")[:2048].decode("utf-8", errors="ignore")` only after screening to obtain a valid bounded prefix; test multibyte boundaries. Never split/return a prefix of a rejected source.
- [ ] Add `Redactor.has_sensitive_text(text: str) -> bool` that checks the active credential and the existing `_EMAIL`, `_IP`, `_SECRET`, `_BEARER` patterns. Reuse it in the presenter. Do not duplicate patterns or use `_SQL` as a sensitive-data detector for this explicit path.
- [ ] Keep the existing statistics-only construction until the common `Coverage(...)` initialization has run. Immediately **after** that assignment, add the analytics-specific presentation below. This order matters: the current method overwrites coverage after branch-specific presentation, which would erase indexed truncation metadata. Do not replace coverage again afterward. Keep source/window validation before presentation and evidence handling unchanged.

```python
if isinstance(response, AnalyticsPage):
    result.data["items"] = analytics_rows(
        response.items[:request.limit],
        secret=self.context.client.settings.token.get_secret_value(),
        result=result,
    )
```
- [ ] Test that all row statistics/IDs/denominators remain identical, text-only omission does not increment row omission counts, cumulative text stays<=8192 bytes, and missing query never falls back to query_text or triggers another API call. Assert a credential beyond the 2048-byte prefix is still detected before clipping.

## Task 3 — final redaction integration without a global SQL bypass

- [ ] Add failing final-envelope tests proving Task2 excerpts would otherwise be replaced with `[SQL-bearing text omitted]` or clipped at 512 characters.
- [ ] Extend `Diagnostics.finish(result, *, analytics_queries: bool = False)`. Only `QueryDiagnostics.read` for a successfully parsed analytics response passes true; every other caller keeps false. Do not infer this capability from user-controlled field names, tool arguments or `result.scope`.
- [ ] Extend `Redactor.clean` with an explicit internal analytics policy and recursive path tracking. The **only** permitted query path is `result.data["items"][integer]["query"]`; when traversing the data itself, path is `("items", integer, "query")`. Only at that exact path and when the internal policy is true, skip `_SQL` suppression and the ordinary 512-character clipping. Keep actual-credential and sensitive-pattern screening; if a supposedly screened excerpt violates these checks, withhold it with matching row metadata rather than retaining a misleading available status. Do not exempt dictionary keys or all strings named query.
- [ ] Prefer one final shared row helper to reconcile any last-stage withholding/status updates. Re-apply indexed metadata and warnings before the existing final byte fit. Preserve redaction accounting; set `redaction.policy_version="minimal-v2-analytics"` and `analytics_query_source="upstream_normalized"` on analytics results only; ordinary tools retain their existing policy version.
- [ ] Test default redaction still suppresses SQL in recommendation text, arbitrary nested dictionaries, optimization/proposal fields, errors and unrelated tool output. Test that putting a `query` key into another response never enables the exception. Assert over 512/under 2048-byte safe queries survive only through the analytics-specific path.
- [ ] Run `tests/test_analytics_sql.py`, `tests/test_queries.py`, `tests/test_query_limits.py`, `tests/test_query_windows.py`, `tests/test_diagnostics.py` together. Initial RED must become GREEN without weakening wrong-parent, unknown-operation or query-window checks.

## Task 4 — MCP and tenant-boundary regression coverage

- [ ] Add a harmless normalized query to each fixed synthetic analytics window in `tools/release/synthetic_api.py`, using distinct server101/server202 identifiers. Keep API keys and raw SQL canaries synthetic. Match the existing fixed request/response table rather than importing production period helpers.
- [ ] Extend installed `local_journey.py` to assert normalized text/status under canonical periods, legacy period_days and explicit-end mode, in both SDK modes. Keep keyA/keyB records distinguishable. A cannot retrieve B's text; revocation and dependency failures must return no cached SQL. Do not relax existing ownership/request-scoped context checks.
- [ ] Extend stdio and authenticated HTTP tests:10 tools/26 GET operations unchanged, no new SQL input argument, structured data includes normalized query and status, raw SQL absent from serialized MCP results and captured logs/errors. Large results retain warnings and explicit dropped-row metadata.
- [ ] Prompt-injection fixtures must not enable write tools, alter the upstream origin, fetch links or cause automatic follow-up calls. SQL text remains untrusted evidence; do not claim tests can guarantee how every model interprets text.

## Task 5 — documentation and release candidate verification

- [ ] Update README analytics output examples to show `query`, status and confidentiality caveats; remove the stale blanket promise that all analytics SQL text is omitted. Keep raw SQL/optimization/proposal omissions accurate.
- [ ] Update the query workflow/static reference to use normalized text plus fingerprint, schema and metrics to identify a query. Tell clients not to treat a truncated prefix as a complete statement, not to infer unavailable SQL and not to execute it. No new live resource or automatic SQL request.
- [ ] Update changelog, current implementation status and source register. Explicitly record additive output fields/default privacy change and normalization provenance. Do not describe the change as independently anonymizing SQL. Do not repeat actual customer text in documentation or receipts.
- [ ] Build/check in containers using the commands below. Format/lint/mypy/offline tests and both transport modes must pass; fix new failures rather than updating old canary expectations indiscriminately. No host installs or real DB operations.
- [ ] Run the full security-enabled release script to bind new package/images/source fingerprint to the changed output policy. The previous 343-test candidate is historical. Record the actual new test count, checksums, image IDs and scan outcomes. Do not invent an expected final count or reuse the old receipt.
- [ ] Finish with a reviewable uncommitted change and updated `.agent/CONTINUITY.md`. Use synthetic fixtures for release checks. Optional later live checks must remain within the existing authorized bounded-GET scope without printing or retaining customer SQL; this planning task performs none. No publication/deployment/commit.

## Verification commands for implementation

From the checkout root; `mcp-releem:checks` is built from that checkout, not an old runtime image:

```bash
docker build --target checks -t mcp-releem:checks .
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks \
  pytest -q -p no:cacheprovider tests/test_analytics_sql.py tests/test_queries.py \
  tests/test_query_limits.py tests/test_query_windows.py tests/test_diagnostics.py
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks \
  ruff format --no-cache --check src tests tools/release tools/containers
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks \
  ruff check --no-cache src tests tools/release tools/containers
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks \
  mypy --strict --cache-dir /tmp/mypy src tools/release tools/containers
RELEEM_RELEASE_SECURITY=true bash scripts/check-release.sh
```

For formatting fixes use the existing checks image with a writable repository mount and `ruff format`; do not install tooling on the host. Release builds/advisory checks can fetch public dependencies; offline tests use `--network none`.

## Acceptance and effort

- An ordinary analytics call shows a useful normalized query from `query`, linked to unchanged query_id/schema/metrics, without a new client option.
- Raw `query_text` never appears in results, repr, logs, errors or fixtures copied from customers. No fallback or new upstream request exists.
- Source-normalization provenance, retained identifiers, withheld text and incomplete prefixes are explicit; no claim of complete literal removal, anonymity or execution safety.
- Credential/comment/control/size cases have fixed omission reasons; metrics survive optional-text omission. Total envelope budgeting and material warnings remain enforced.
- Generic SQL suppression, GET-only dispatch, explicit server scope, tenant isolation, expiry/revocation behavior and both transports remain intact.
- No changes to Codex key configuration, HTTP identity, dependencies or runtime base.

Estimate **1–2 engineering days** for presentation/redaction integration, synthetic privacy/budget regressions, transport checks and full release revalidation. Assumes current contract and dependency lock remain unchanged.

Review decisions before execution: approve normalized excerpts by default and the 2048/8192-byte limits; accept that upstream normalization is not independently certified; retain confidential identifiers for useful diagnosis. If independent literal-removal guarantees or raw SQL are required, revise scope before implementation. No authenticated customer calls were made during this planning task.
