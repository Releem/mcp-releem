# Source register — mcp-releem

Research date: **2026-11-10**. Research began at **2026-11-10T15:00:08Z** (local UTC clock). Public documentation and unauthenticated public repository/registry reads only; no customer API calls. Registry versions are observed candidates, not a resolved, installed or security-audited dependency set.

| Source | Identity / observation | How used / limitation |
|---|---|---|
| [Swagger](https://api2.dev.releem.com/docs#/) and [OpenAPI](https://api2.dev.releem.com/openapi.json) | OpenAPI 3.1.0; title Releem API; version 1.0.0; 45 operations; `servers=[{"url":"/","description":"Current API server"}]` | Initially a documentation-only source; the user subsequently approved this origin as the API base URL (see clarification below). Deployed behavior, self-host parity, agent matrix and complete endpoint RBAC remain unverified. [Exact capture](evidence/releem-openapi-2026-11-10.json). |
| Captured OpenAPI integrity | Raw HTTP response body SHA-256 `dd6f9ae69c1bcd7e96e5d2cb4a004721d17eed0183dc98cb132442a2d0fa45d2` | Hash is of curl's downloaded body, not transport framing. |
| Preparation evidence cross-check | Python `json.dumps(parsed_contract)` SHA-256 `a238fd1b7d787da7a9af7888d4ea8f36c5f1d60c140228c033fde2f2eb42af38` | Matches supplied preparation evidence using default Python JSON serialization; not a raw-byte hash. Contract publication/change date absent. |
| [jamesbrink/mcp-coroot](https://github.com/jamesbrink/mcp-coroot/tree/b089b7208bdce6c776b09b5221adb14db7ca0600) | HEAD rechecked: `b089b7208bdce6c776b09b5221adb14db7ca0600`, committed 2026-09-27T06:38:19Z; project version 1.0.0 | Assumed meaning of “same approach.” Actual cloned source inspected: CLI, config, app, error guard, compacting, secrets, tools, base client, prompts/resources, dependency metadata and license. |
| [Reference dependency metadata](https://github.com/jamesbrink/mcp-coroot/blob/b089b7208bdce6c776b09b5221adb14db7ca0600/pyproject.toml) | `mcp>=2.1,<3`, `httpx2>=2.5,<3`, `pydantic>=2.12,<3`; Python >=3.11 | These are ranges, not verified compatible pins for our project. |
| [Reference license](https://github.com/jamesbrink/mcp-coroot/blob/b089b7208bdce6c776b09b5221adb14db7ca0600/LICENSE) | MIT; copyright 2025 James Brink | Preserve copyright and permission notice if copying substantial code. This planning session copies no runtime source. |
| [Coroot native MCP](https://docs.coroot.com/mcp/overview/) | Official native `/mcp` integration documented separately | Distinct from the community Python adapter; its OAuth/Coroot identity behavior is not a Releem API capability. |
| [Latest MCP specification](https://modelcontextprotocol.io/specification/latest) | Redirects to **2026-07-28**, rechecked | Target revision; do not assume legacy handshake/session behavior. |
| [Streamable HTTP binding](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) | 2026-07-28; request-scoped responses, protocol sessions removed | HTTP transport and Origin checks. Upstream Releem chat SSE is independent. |
| [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Current revision | Protected-resource metadata, OAuth discovery/resource indicators, audience checks and separation from upstream credentials. |
| [Python SDK](https://github.com/modelcontextprotocol/python-sdk), [v2 changes](https://py.sdk.modelcontextprotocol.io/whats-new/), [PyPI metadata](https://pypi.org/pypi/mcp/json) | `mcp==2.3.0`, release uploaded 2026-10-02T22:06:52.119073Z; `mcp-types==2.3.0` dependency; source HEAD `77001c96f9507be0f4d009b83210a384a5e08bda` | v2 `MCPServer`; async transports. Metadata says Python >=3.10 while current main README says >=3.11: choose Python 3.12 and validate the pinned release. Main docs may run ahead of the release. |
| [TS SDK](https://github.com/modelcontextprotocol/typescript-sdk), [server registry](https://registry.npmjs.org/@modelcontextprotocol/server/latest), [client registry](https://registry.npmjs.org/@modelcontextprotocol/client/latest), [Node adapter](https://registry.npmjs.org/@modelcontextprotocol/node/latest) | Current v2 split: server/client **2.4.0**, Node adapter **2.1.2**, engines >=20, Apache-2.0; HEAD `919bb8ea88b6e10e72c2f8b6218fad4cfdc40b2c` | Current alternative. Old `@modelcontextprotocol/sdk` latest 1.32.2 is legacy v1, not current v2. Do not recommend it accidentally. |
| [httpx2](https://pypi.org/pypi/httpx2/json), [Pydantic](https://pypi.org/pypi/pydantic/json), [uv](https://pypi.org/pypi/uv/json) | 2.16.0 / 2.14.3 / 0.13.7 | Observed candidates. SDK uses httpx2, so prefer a single async HTTP stack after compatibility spike. |
| [pytest](https://pypi.org/pypi/pytest/json), [Ruff](https://pypi.org/pypi/ruff/json), [mypy](https://pypi.org/pypi/mypy/json), [Hatchling](https://pypi.org/pypi/hatchling/json) | 9.2.0 / 0.17.4 / 2.4.1 / 1.33.0 | Candidate test/lint/type/build tools; locked container resolution and dependency/license checks are Phase 0 acceptance gates. |
| [Claude Code MCP](https://code.claude.com/docs/en/mcp) | Docs confirm local stdio, remote HTTP and browser OAuth | Documentation-level compatibility; exact installed client version and 2026-07-28 protocol support UNCONFIRMED. |
| [Cursor MCP](https://cursor.com/docs/mcp) | Docs confirm stdio/HTTP, OAuth, env interpolation and client-specific callbacks | Register actual supported callback URIs; no universal client auth guarantee. |
| Existing local harness | Repository commit `4295c76`; branch `mcp-releem`; clean before cleanup | Inspected `server.py`, `context/releem_api.py`, `executors/releem.py`, `pyproject.toml` and guidance. Header auth and server/task reads are reusable ideas; engine/executor not inherited. Historical assessment at supplied path was absent. |

Evidence collection used Python's installed standard library and curl/git only; no system package installation. Temporary reference checkout and downloaded SDK docs are under `/tmp/mcp-releem-research`. That directory and the old-work backup are not durable release artifacts. The public OpenAPI capture is retained in this branch; the source links above pin the key reference. Live customer behavior remains UNCONFIRMED.

Phase 0 continuation (2026-11-10): the OpenAPI raw bytes/hash were rechecked and are unchanged. Candidate dependencies were resolved into a hash lock and installed in a separate digest-pinned Python 3.12.16 container for synthetic SDK interoperability tests. See [compatibility scope and results](../clients/compatibility.md); this supersedes the earlier no-installation statement only for isolated container tooling. No host dependencies were installed.

User clarification, 2026-11-10T19:21Z: API base URL confirmed as `https://api2.dev.releem.com`, the same origin as Swagger. This resolves the earlier missing-URL decision; approval comes from the user, not the development OpenAPI. It does not establish deployed behavior or self-hosted/agent parity.

Query slice research (2026-11-10): public OpenAPI raw bytes/hash rechecked and unchanged. Added pinned [python-dotenv 1.2.4](https://pypi.org/pypi/python-dotenv/json), using its parser without interpolation for explicit `--env-file` loading. Selected existing plan fields were checked against [PostgreSQL 18 EXPLAIN documentation](https://www.postgresql.org/docs/18/using-explain.html) and [MySQL 8.0 EXPLAIN documentation](https://dev.mysql.com/doc/refman/8.0/en/explain-output.html). This supports narrow field interpretation, not cross-engine/version certification. Subsequent authorized live API reads are scoped separately in [the API check receipt](../api-checks-2026-11-10.md).

Recommendation/client continuation (2026-11-11T05:16Z): current OpenAPI raw hash
rechecked unchanged; detail review/evidence/history shapes and explicit fleet
semantics verified against that contract. Installed Claude Code2.1.70 registration
and health were tested in an isolated temporary project, without model calls;
Cursor3.25.6 remains documentation-only onboarding. Official
[Claude MCP](https://code.claude.com/docs/en/mcp),
[configuration isolation](https://code.claude.com/docs/en/env-vars), and
[Cursor MCP](https://cursor.com/docs/mcp) documentation was checked; current web
features may exceed installed versions. Exact receipts and limitations are in
[local setup](../clients/local-setup.md); no dependency pins were changed.

## OpenAPI update review — 2026-11-11T14:53Z

Public Swagger still references /openapi.json. Current raw capture has46 operations,
OpenAPI3.1.0/Releem API1.0.0 unchanged, SHA256
`a2474b68c2b32f589bd24c820ab0a80df9200e888476aee78cb3c590c6b19e40`.
One added GET /v1/checks, seven changed existing operations, four changed/two added
schemas; authentication/writes unchanged. Direct HTTPS succeeded when the browser
reader could not open this origin. No authenticated API/customer/model calls.
[Current capture](evidence/releem-openapi-2026-11-11.json),
[metadata](evidence/releem-openapi-2026-11-11.metadata.json),
[review and complete delta inventory](2026-11-11-openapi-change-review.md),
[implementation plan](../superpowers/plans/2026-11-11-openapi-compatibility-update.md).
The2026-11-10 capture and source observations above remain historical evidence.

### Implemented compatibility reference — 2026-11-11

The 2026-11-11 raw capture is now the active offline compatibility baseline for
26 allowlisted reads; immutable old capture is retained. Check schemas, current
query period/end parameters and all registry query keys are guarded offline.
The newly documented `/v1/checks` catalog remains deferred. Source provenance
hashes both captures; no API/dependency/identity behavior is inferred from the
unchanged 1.0.0 version string. No authenticated calls were used for this update.

## Hosted startup incident — 2026-11-12

Bounded authorized inventory reads with the client's existing key returned200,
but the adapter rejected `instance_type` objects during hosted authentication.
Only field/type validation failures were retained; no customer payloads or keys
were saved. Public `/openapi.json` independently documents `Server.instance_type`
and `ServerDetailsResponse.instance_type` as nullable `CodeValue` objects, with
strict integer-or-string `id` and optional nullable string `name`. Original code
identities and unknown codes must be preserved.

The targeted inventory fix accepts that selected shape alongside the earlier
string form. Synthetic hosted authentication reproduces503 before the fix and
passes after it. The retained 2026-11-11 contract remains the broader baseline;
this incident does not establish compatibility for every newer API schema.
