# D018: Existing API keys for shared private pilot

2026-11-11, owner-approved API-key authentication; implemented developer preview.

A shared stateless HTTPS MCP endpoint accepts an existing customer Releem API key
as Bearer on every request. This is intentional custom API-key authentication,
not OAuth access-token forwarding. It supplies only Releem-Secret-Key toward a
fixed administrator origin. No shared privileged key plus caller tenant ID is used.
GET /v1/servers is the validation/inventory read; missing and invalid keys returned
401 and a configured valid key returned200 in three authorized checks. Full results
and limits: [API receipt](../api-checks-2026-11-11.md).

The key's upstream access is authoritative. The adapter does not claim a human
identity, granular roles or memberships from inventory. Scoped request clients
reject foreign server IDs and inventory/fleet rows. No credentials/results/sessions
are cached. Validation repeats on all protected requests; upstream must authorize
every resource read. Key changes during an in-flight request remain dependent on
upstream enforcement. Revocation propagation, read-only key availability and
production/self-hosted compatibility remain UNCONFIRMED.

One worker with bounded process-local quotas is the smallest pilot. Horizontal
scaling requires ingress-wide admission controls. API outages fail closed; no write
capabilities, OAuth metadata, token enrollment or browser login are invented.
Static reference URI errors are validated before SDK handling to avoid echoed
caller content. See [deployment and threat boundaries](../hosted-pilot.md).

OAuth support, signed scoped MCP tokens and stronger identity integration can be
added later if required by supported clients; they are not implemented prerequisites
for this explicitly configured-header private pilot.
