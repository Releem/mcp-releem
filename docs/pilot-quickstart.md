# Private pilot quickstart

This is an uncommitted developer preview. No shared service is deployed yet.

## Local

1. Build/check with `bash scripts/check-release.sh`; record the printed candidate
   directory, verification.json and SHA256SUMS. This needs Docker, Bash and Git,
   not a Releem key. Use the verified native architecture only.
2. Save the Releem key in your local secret store/token file outside the checkout.
   Configure the nonroot image's file access according to your security policy.
3. Follow [local setup](clients/local-setup.md) to configure a pinned image and
   read-only secret-file mount in an isolated client entry. Append `--check` first.
   No port publishing is needed for stdio. Keep stdout reserved for MCP messages.
4. Discover servers, select an explicit returned ID, inspect findings, then read
   and explain a recommendation. Missing reports mean missing evidence, not health.

## Shared hosted

Operators: use [Compose start/restart](compose-hosting.md) and [hosted pilot setup](hosted-pilot.md) to configure the public
HTTPS origin, private listener/TLS ingress and approved API egress. Do not use a
server-global customer key. Deployment needs separate owner authorization.

Customers: once an approved URL is available, configure it as a Streamable HTTP
server and supply your Releem API key through the client's secret-backed
Authorization header. No Docker installation is required for hosted customers.
Only configured-header-capable clients are candidates; actual client onboarding
is still pending. Use the same explicit-server diagnostic journey as local.

Both versions are read-only, minimize sensitive evidence and may return partial
results. Releem cloud API calls and the selected client/model provider can move
evidence outside your infrastructure. Metric grouped windows require aligned
bucket boundaries; use documented hourly comparisons when uncertain. No
recommendation status or monitoring observation proves an applied effective change.

For updates, pin the new verified image and preserve the previous verified image
and configuration for rollback. Remove the client entry to disconnect; stop/remove
local containers or have the operator remove hosted access. Rotate/revoke the key
through Releem when required, then remove obsolete client/local secret copies.
Never include credentials or customer payloads in support reports.
