# Authorized API check scope — 2026-11-10

The user supplied `RELEEM_SECRET_KEY` in `.env` and explicitly authorized API
testing. The credential was loaded only from a read-only secret-file mount; no
value was printed, put in command-line arguments, copied into an image, or saved
in a fixture. The approved origin was enforced as `https://api2.dev.releem.com`.

Two bounded sampling passes made **nine GET requests total**:

| Operation | Scope and result |
|---|---|
| Server inventory | Authentication succeeded in both passes; accessible entries returned. |
| Server metadata/details/full health/security reports | One inventory entry sampled. Responses validated; findings remained partial because of old evidence and privacy-omitted check values. |
| Server recommendations | A bounded page validated successfully. |
| Query analytics | One active inventory entry sampled, one-day window, limit 2. Valid empty response; tool returned `no_data`. |
| Saved query optimizations | Same query-test server, limit 2. Valid empty response; tool returned `no_data`. |

No query/proposal IDs were available in that sample, so proposal and optimization
detail views were **not live tested**. Their populated records, scope checks,
units, plan extraction, omission metadata and error behavior use synthetic
fixtures. This is not evidence of absent queries across the account or of
compatibility across roles, engines, providers or agent versions.

No POST/PATCH/PUT/DELETE request, optimization submission, task creation, chat,
EXPLAIN execution or database operation was performed. No raw server/query
response was retained. Only operation-level status and validation outcomes are
recorded here; customer names, IDs, SQL, plans, addresses and inventory counts are omitted.

The current public contract remains Releem API 1.0.0, 45 operations, raw SHA-256
`dd6f9ae69c1bcd7e96e5d2cb4a004721d17eed0183dc98cb132442a2d0fa45d2`.
