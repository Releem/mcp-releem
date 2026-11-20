# Develop and verify Releem MCP

For client setup, start with the [hosted quickstart](README.md#hosted-setup).

## Container checks

Run the release check from the checkout root:

```sh
bash scripts/check-release.sh
```

The script uses locked dependencies, Ruff, mypy, synthetic pytest tests, wheel
and source distribution builds, installed runtime checks, authenticated
loopback HTTP journeys and isolated Compose recovery. It leaves a checksummed
local candidate. The [CI workflow](.github/workflows/ci.yml) runs this check
on pushes and pull requests.

To run individual checks in containers:

```sh
docker build --target checks -t mcp-releem:checks .
docker run --rm --network none --read-only --tmpfs /tmp:exec mcp-releem:checks
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks ruff check --no-cache src tests
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks ruff format --check --no-cache src tests
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks mypy --cache-dir /tmp/mypy-cache src
docker build --target artifacts --output type=local,dest=dist .
```

The test container needs an executable temporary directory for the deployment
test doubles. Stdio tests use a 15-second request budget to tolerate CI
contention. The local tests supply synthetic API responses and keys. See
[transport tests](tests/test_transports.py),
[query windows](tests/test_query_windows.py),
[query results](tests/test_queries.py), and the
[authenticated local journey](tools/release/local_journey.py).

For a separately authorized security audit, the release check accepts
`RELEEM_RELEASE_SECURITY=true`. That mode uses public advisory services and
fails on incomplete coverage or high and critical container findings. Treat
offline checks and the security audit as separate release evidence.

## Implementation and documentation

The [GET-only upstream registry](src/mcp_releem/api/operations.py) defines 26
reads. The [hosted boundary](src/mcp_releem/hosted/app.py) validates caller keys
against accessible inventory. The [tool registration](src/mcp_releem/server.py)
and [static workflows](src/mcp_releem/workflows.py) define the MCP surface.
Retained upstream contracts are under [OpenAPI fixtures](tests/fixtures/openapi).

The Dockerfile pins the Python 3.12 Alpine base by digest. The shipped runtime
uses [the runtime base helper](tools/containers/runtime_base.py) to remove
unused SQLite components. Source development and checks keep their development
dependencies. Local planning notes in `docs/` and evidence under `.agent/`
are ignored. The README covers client setup and the tool reference.

## Verification evidence

| Date | Check | What it establishes |
| --- | --- | --- |
| 2026-11-11 | Codex CLI 0.167.0 parsed the loopback HTTP configuration. An isolated loopback check showed HTTP 200 liveness and HTTP 401 for a keyless MCP request. | Local configuration and denial. These were separate from a customer-authenticated client read. |
| 2026-11-11 | Claude Code 2.1.70 registered and connected to a local stdio process using a synthetic key with networking disabled. | Registration and connection for that client and transport. Interactive diagnostics and prompt/resource use need separate evidence. |
| 2026-11-12 | The published preview returned HTTP 200 from `/healthz` and 401 for an unauthenticated `/mcp` request. | Public routing, process liveness and keyless denial at the time. |
| 2026-11-12 | The owner reported Codex tool discovery. A subsequent authenticated `servers` read through the connected Releem MCP succeeded. | The observed preview supported discovery and inventory. Availability can change independently of the checkout. |
| 2026-11-19 | The migration's local release verification passed 428 tests, package builds, both protocol versions and isolated Compose recovery. | Synthetic coverage of code in the checkout. It does not establish deployment of the upstream cutover or response-field changes. |
| 2026-11-19 | Documentation review decoded the three placeholder configurations in Codex CLI 0.170.0 and exercised the quickstart's inventory and 24-hour query arguments with populated and empty synthetic responses over loopback. | The client accepts the documented configuration syntax. The fixture checks the documented tools, arguments, units and coverage. |
| 2026-11-20 | Claude Code 2.1.70 registered a user-scoped HTTP server in an isolated configuration. It stored the literal `${RELEEM_MCP_API_KEY}` reference. `claude mcp list` connected to a loopback hosted fixture with the correct synthetic environment value and failed with a wrong value. | Registration, variable expansion and connection health for Claude Code HTTP. The test substituted the loopback address and test Host header. It used neither a Releem account key nor a live MCP endpoint. |
| 2026-11-20 | Reviewed the Claude app setup against Anthropic's [custom connector instructions](https://claude.com/docs/connectors/custom/add-unlisted#authenticate-with-request-headers). | Vendor-documented UI steps and beta availability. The connector was not added in an app account. |
| 2026-11-20 | The consolidated README passed a rendered walkthrough and link and anchor checks in a clean export. Codex CLI 0.170.0 decoded the placeholder configurations. | Documentation and local configuration checks. The shared inventory and 24-hour query arguments also passed with populated and empty synthetic responses in both protocol modes. |
| 2026-11-20 | The consolidated documentation passed the offline release workflow with 428 tests, Ruff, mypy, package builds, both transports, isolated Compose recovery and 15 checksum checks. | The local release workflow passed with the consolidated README. |

Codex CLI syntax was checked against version 0.170.0 on 2026-11-19. The
[official MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) covers
`config.toml`, static headers and local subprocess settings. The
[official CLI command guide](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
covers `/mcp`.

The exact hosted inventory-to-query walkthrough with this response contract
still needs live verification. The two Claude client paths also need an
authenticated hosted read. Hosted client prompt/resource behavior, deployed
isolation, revocation, streaming and reboot recovery require separate verification.
