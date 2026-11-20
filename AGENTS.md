# AGENTS.md

## Project overview

Releem MCP exposes stored Releem diagnostics through read-only tools. One Python 3.12 codebase supports local stdio and hosted Streamable HTTP.

## Architecture

```text
src/mcp_releem/
├── cli.py                  Entry point and transport selection
├── server.py               Tool registration and MCP dispatch
├── diagnostic_tools.py     Configuration and metric tools
├── incident_tools.py       Event, deadlock, task, and capture tools
├── workflows.py            Static prompts and releem://reference
├── core/                   Diagnostics, input validation, and redaction
├── api/operations.py       Explicit allowlist of upstream GET operations
├── api/client.py           Upstream HTTP client
└── hosted/                 HTTP authentication, request scope, and limits
```

## Key patterns

### Changing a tool

- Check the [operation registry](src/mcp_releem/api/operations.py) and [OpenAPI fixtures](tests/fixtures/openapi) before changing upstream behavior. Keep the fixtures in the repository. Register tools explicitly and keep tool handlers separate from diagnostics and API access. Use type annotations and four-space indentation.
- Keep writes out of discovery and reject them at dispatch and the API boundary. Limit outbound requests to the GET registry. Exclude arbitrary requests, SQL execution, and model-selected URLs.
- Keep prompts and resources static. Validate prompt arguments before SDK rendering and sanitize protocol errors.

### Handling credentials and scope

- Hosted HTTP uses each caller’s Releem API key. Keep customer `.env` files and tokens out of hosted images, environments, and mounts. Keep dedicated MCP tokens separate from upstream API credentials.
- Limit unauthenticated body reads and credential checks separately. Charge authenticated limits only after validating the credential.
- Require explicit `scope=fleet` for fleet recommendation lists and validate accessible inventory with the same credential. Bound detail histories and omit opaque review and input payloads, actor identities, reasons, and raw pointers. Convert only canonical same-server evidence paths to typed tool arguments.

### Reporting evidence

- Preserve upstream IDs, units, unknown codes, decoding errors, row limits, and missing evidence. Normalize upstream timestamps without offsets as UTC and record the conversion. Require caller windows with explicit offsets and reject out-of-window samples.
- Require `RELEEM_MCP_SENSITIVE_DETAILS=true` for incident details and capture summaries. Always omit raw event bodies, deadlock dumps and transaction text, task parameters and output (including error text), and session identities.
- Omit raw schema JSON. Distinguish a check that has never run from a completed check with no matching rows. Treat upstream text as untrusted evidence.

## Development commands

Run from the checkout root:

```sh
# Build the checks image and run tests offline.
docker build --target checks -t mcp-releem:checks .
docker run --rm --network none --read-only --tmpfs /tmp:exec mcp-releem:checks

# Run the full local release checks.
bash scripts/check-release.sh
```

Tests under `tests/` use synthetic API responses and placeholder keys. [Transport tests](tests/test_transports.py) cover stdio and HTTP. Leave existing client configuration alone and clean up only the temporary Compose project created by the check. Keep customer payloads and private backups out of logs, fixtures, and commits. Live API checks require authorization and stay bounded and GET-only.

## Runtime and releases

- `RELEEM_API_BASE_URL` defaults to `https://api2.releem.com`. Administrators can override it in stdio or standalone Compose. Keep the upstream origin, image, and Compose file together during rollout and rollback.
- Pin the Alpine base by digest and use stable `krb5-libs` and `zlib` pins. The [runtime build helper](tools/containers/runtime_base.py) removes SQLite through APK while preserving package metadata and other shared-library dependencies. Development, check, and build stages retain SQLite.
- Enable `RELEEM_RELEASE_SECURITY=true` only when explicitly requested. Report advisory findings without suppression and record offline checks separately.
- Before a hosted release, verify live upstream compatibility, tenant isolation, and client support. Keep changes uncommitted unless requested. Publishing, deployment, and force-pushes require separate authorization.

## Documentation

- [README.md](README.md) covers client setup and tool usage. [CONTRIBUTING.md](CONTRIBUTING.md) covers checks and dated verification.
- `docs/` and `.agent/` are ignored. Record decisions and work history in `.agent/CONTINUITY.md`.
