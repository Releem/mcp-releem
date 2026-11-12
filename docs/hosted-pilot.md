# Shared hosted private pilot

The same ten read tools, four prompts and static reference now support stdio and
an authenticated stateless Streamable HTTP `/mcp` endpoint. One process can serve
multiple customer keys. This implementation is a developer preview; deployment,
real HTTPS client onboarding and operational release approval remain outstanding.
No database operations or write tools are available.

## Operator setup

For the approved Docker-on-our-host deployment, use the
[Compose start/restart runbook](compose-hosting.md). It includes private port
binding, health checks, bounded resources/logs and automatic exit recovery.


Build `docker build --target hosted -t mcp-releem:hosted .`, then pin the image ID
for a reviewed pilot. Configure only administrator settings:

```dotenv
RELEEM_MCP_PROFILE=hosted
RELEEM_MCP_PUBLIC_URL=https://mcp.example.invalid/mcp
RELEEM_API_BASE_URL=https://api2.dev.releem.com
RELEEM_MCP_BIND_HOST=127.0.0.1
RELEEM_MCP_PORT=8000
RELEEM_MCP_READ_ONLY=true
RELEEM_MCP_SENSITIVE_DETAILS=false
```

Run `mcp-releem --transport streamable-http --env-file /path/to/hosted.env --check`
before starting without `--check`. Do not use the local customer `.env` here:
hosted configuration rejects all global customer credential variables, even empty
ones. The hosted Docker target binds `0.0.0.0` inside the container; publish only
on a private interface reachable by the trusted TLS ingress. Never expose its
plaintext listener directly. Preserve the configured public Host through ingress;
forwarded headers are not trusted. `/healthz` is liveness only, not API readiness.
Use `/mcp` exactly; session IDs, query-string credentials, redirects and other
paths are rejected. No browser CORS or browser OAuth workflow is supplied.

Use one small container behind an existing HTTPS ingress initially. Configure
certificate renewal, egress restrictions to the approved API/proxy, read-only
filesystem, a writable ephemeral `/tmp`, restart/health policy and resource limits.
The public URL and upstream origin are administrator-controlled and fixed for all
customers. Private upstream literal addresses are disabled in hosted mode; local
stdio retains its explicit private-origin opt-in. DNS/egress policy must also
block unintended private destinations; application URL validation alone does not
prevent DNS rebinding by a compromised administrator-selected origin.

## Customer connection

Each request sends `Authorization: Bearer <RELEEM_API_KEY>` to the HTTPS `/mcp`
endpoint. This is intentionally the existing Releem API key, not an OAuth access
token or separately issued MCP token. Never put it in a URL, command argument,
Git-tracked configuration or tool argument. Configure it through the selected
client's secret/header mechanism. Only clients that support custom HTTP headers
are candidates; actual application onboarding remains a release gate. No universal
client compatibility or browser login is claimed.

The service validates the key with `GET /v1/servers` on every protected HTTP
request, including discovery and static reference requests. Invalid/revoked keys
fail closed; API outages yield errors, never authorized empty evidence. Requests
use independent clients, immutable inventory scopes and task-local diagnostics.
There are no positive auth, customer result or session caches. Server IDs outside
the same key's inventory are rejected before their endpoint is called. The API
must still authorize every subsequent read; inventory is not a substitute for
upstream authorization. Keys with account-wide access retain that scope; this
adapter does not establish human identities or add granular permissions.

The inbound credential is removed before MCP presentation and set explicitly as
`Releem-Secret-Key` only toward the fixed API origin. Redirects are refused. No
customer keys are stored at rest. The service holds request keys in process memory
until request completion; it cannot promise memory erasure. Logs must never retain
headers, bodies, SQL or query strings; ingress must follow the same policy. The
application disables access logs and sanitizes boundary errors. Operational metrics
should contain only aggregate status/latency, never credential/customer labels.

## Bounds and lifecycle

Unauthenticated reception is bounded separately:32 body slots/3s body deadline
and8 inventory-validation slots/5s validation deadline. Customer work quotas are
charged only after successful validation; invalid keys cannot consume them.
Cloudflare ingress source/rate controls remain necessary against sustained floods.

Defaults: 256KiB request bodies, 30s request deadline, 16 authenticated concurrent requests,
4 concurrent requests per key, 60 requests/minute per key and 600/minute globally.
`RELEEM_MCP_MAX_CONCURRENT_REQUESTS` (1–128),
`RELEEM_MCP_PER_KEY_CONCURRENCY` (1–16), and
`RELEEM_MCP_REQUESTS_PER_MINUTE` (1–600) are administrator overrides. The quota map
has at most 2048 HMAC fingerprints, expires inactive entries after 60s and contains
no raw credentials. Limits are process-local; deploy one worker for this pilot or
supply ingress-wide distributed limits before scaling. Stateless transport needs
no session affinity, but does not make local quotas global. Cancellation releases
admission slots and closes request clients. HTTP 429 includes Retry-After; calls
are not automatically retried. MCP SSE support and upstream chat SSE are unrelated;
chat is excluded.

Revoke/rotate keys in the authoritative Releem account system, update client secret
configuration, remove old keys from clients and verify denial. There is no newly
invented revocation API. Validation on the next request observes upstream denial;
upstream revocation propagation and in-flight semantics remain UNCONFIRMED.
A stolen API key has its original API permissions, potentially including writes
outside MCP: the MCP read-only boundary does not reduce the key's upstream scope.
Use the least-privileged available credential; read-only upstream key availability
is UNCONFIRMED. Do not log a key to diagnose authentication.

Customer telemetry travels from Releem API to hosted MCP to the selected client
and potentially its model provider. Local stdio also calls the cloud API and can
send results to a remote model. Neither profile promises air-gapped processing.

For failure triage record version, timestamp, HTTP/tool error code and sanitized
steps. 401: verify the key outside the model; 403: verify its account/server access;
429: wait; 503: check API/CA/proxy/egress. Never replace failures with healthy results.
Rollback by redeploying the previously verified image/configuration and rechecking
key isolation; no stored schema migration is needed. Uninstall by stopping/removing
the pilot service and client entry, then revoke credentials as appropriate.
