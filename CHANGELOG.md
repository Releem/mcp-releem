# Changelog

## 0.1.0

- Show screened old and new setting values in configuration detail, including
  outstanding targets. Add a bounded, date-sorted view of recommended settings
  that reached their targets, with partial application and rollback evidence.

- Add `query` and `query_status` to ranked query analytics rows so clients can
  show screened, upstream-normalized SQL alongside the fingerprint and metrics,
  label truncated prefixes and explain missing text.
- Accept the API's `instance_type` code object during inventory validation,
  preserving its original id/name and legacy string values. Prevent valid keys
  from failing hosted MCP startup when the API returns the new object shape.
- Support the updated 46-operation API contract: nullable check metadata, truthful
  failure/unknown summaries, canonical query periods and explicit end bounds. Keep
  legacy MCP day-count inputs as an alias; never send removed period_days upstream.
- Validate returned query windows and use documented half-open average bounds;
  defer the new check catalog endpoint without changing the ten-tool surface.

- Introduce read-only Releem diagnostics through local stdio and request-isolated,
  existing API-key authenticated shared Streamable HTTP.
- Add bounded structured evidence, explicit missing-data warnings, static diagnostic
  workflows and minimized sensitive output.
- Add locked container release verification, installed-package/runtime checks,
  synthetic artifact audits, checksums and verification-only CI.
- Remove the previous change-execution harness. No automatic migration or execution.

- Add Compose host start/restart operations, private listener, liveness checks,
  resource/security defaults and verified unexpected-process-exit recovery.

- Replace Debian slim with pinned Python3.12/Alpine3.24; remove unused SQLite
  library/bindings and patch stable Kerberos/zlib packages while retaining OS
  package metadata and the existing Python lock/tool contracts.
