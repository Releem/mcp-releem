# Local release validation plan

Goal: complete reviewable local portions of release gates1,3,4. User selected
synthetic accounts on2026-11-11. No real customer/model data, remote deployment,
API writes, key revocation, publication or Git push. Preserve uncommitted state
until candidate review; final release revision/remote CI remains a separate gate.

- [x] Independent security review of actual source and container/release boundaries;
  reproduce findings, add regression first, fix important issues.
- [x] Audit exact runtime dependencies with pinned pip-audit2.10.1 in a temporary
  container; inventory licenses/notices from installed metadata. Never label
  skipped/unknown packages or failed advisory queries as a clean scan.
- [x] Add installed-runtime local TCP journey covering two synthetic accounts,
  findings/missing evidence/recommendation explanation, prompts/reference, foreign
  ownership rejection, invalid/revoked keys and upstream failures. Run both SDK
  protocol modes. No fixture control endpoints in production source.
- [x] Test exact installed Claude configured-header connection in an isolated
  temporary config/workspace; attempt synthetic tool workflow only if usable
  client authentication is available. Record application versus SDK evidence.
- [x] Strengthen artifact/source provenance and package/Compose installation checks;
  verify checksum corruption fails and clean local image load/rollback behavior.
- [x] Full locked container checks/builds/Compose lifecycle and local journeys;
  document evidence and unresolved actual-host/real-account/release-commit gates.

Local engineering tasks complete with evidence in docs/releases/evidence/.
Release gate is not complete: image OS advisories remain unapproved; isolated
Claude model login, actual-host TLS and remote CI/release revision remain open.
No customer key rotation claimed, commit/publish/deploy performed.
