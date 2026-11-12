# mcp-releem

Read-only Releem database diagnostics for MCP clients. Run locally with stdio or
as a shared authenticated HTTP service. This is a developer preview.

Start with the [hosted setup below](#hosted-setup).
For other clients or transports, see [client setup](docs/clients/local-setup.md).
To run your own local container, see [local HTTP setup](#local-http-setup-with-codex-and-the-real-api).

## Hosted setup

The hosted MCP endpoint is **`https://mcp.releem.com/mcp`**. You need an existing
Releem API key and an MCP client that supports HTTP with an Authorization header.
Each request uses your own key for authorized Releem API reads; the shared server
has no global customer key. Docker is only required when hosting the server yourself.

### 1. Connect Codex

Open `~/.codex/config.toml`. Replace the existing `releem` connection and its
nested header table with:

```toml
[mcp_servers.releem]
url = "https://mcp.releem.com/mcp"

[mcp_servers.releem.http_headers]
Authorization = "Bearer <YOUR_RELEEM_API_KEY>"
```

Replace the placeholder locally in that private file and keep the `Bearer `
prefix. Remove the local-test `Host` header and any old `bearer_token_env_var`
setting from this connection. Restrict access to the plaintext key:

```sh
chmod 600 ~/.codex/config.toml
codex
```

In the new session, use `/mcp` to check the connection, then ask:

> Use releem to list my accessible servers with limit=5. Ask me to select a server
> before inspecting its findings or query evidence.

For another client, use the same HTTPS URL and `Authorization: Bearer <KEY>`
header. The hosted preview uses API-key headers; browser OAuth is not implemented.
Diagnostics pass through the hosted service and reach your client/model provider.

### 2. Check connectivity

These checks need no API key:

```sh
curl --fail --show-error --max-time 15 https://mcp.releem.com/healthz

curl --silent --show-error --max-time 15 -o /dev/null -w '%{http_code}\n' \
  -X POST https://mcp.releem.com/mcp \
  -H 'Content-Type: application/json' --data '{}'
```

Expected: `{"status":"alive"}` and `401`. These establish public liveness and
authentication denial; the client read in step 1 verifies authenticated access.
The owner reported both public checks passing on 2026-11-12; authenticated client
and real reboot verification remain pending.

| Problem | Check |
|---|---|
| Public `404` | Tunnel route must match the public hostname, with no path restriction; verify custom-hostname/fallback settings if using Cloudflare for SaaS. |
| Public `502` | Tunnel origin must be `http://mcp:8000`; inspect MCP health and connector logs. |
| Client `401` | Check the key and `Bearer ` prefix; unauthenticated curl returning `401` is expected. |
| Client `400 invalid_host` | Remove a leftover local-test Host header; use the public HTTPS endpoint. |
| Cloudflare `403` / Error1010 | Disable Browser Integrity Check for this hostname and `/mcp` using a configuration rule; API clients cannot complete browser challenges. |
| Initialization `503 upstream_unavailable` | The server could not validate upstream inventory. Check API connectivity and response compatibility; a passing `/healthz` does not check the upstream API. |

API compatibility: inventory accepts `instance_type` as a legacy string or the
documented `{id, name}` code object. Original string/integer code identities,
unknown codes and null names are preserved; malformed objects fail validation.
This fixes the startup failure observed against the API on 2026-11-12 and must
be deployed to take effect on the hosted endpoint. It does not certify other
API contract changes introduced after the retained 2026-11-11 baseline.

## Deploy the hosted server and enable GitHub deployment

The current managed host is `ubuntu@40.160.8.37`. Its `mcp-releem` Compose stack
contains `mcp` and the optional `cloudflared` connector. The backend is bound to
loopback; Cloudflare reaches `http://mcp:8000` over the private Docker network.
See the [server and tunnel runbook](docs/github-deployment.md) for one-time setup,
token replacement, domain routing and rollback. Those host commands assume the
managed server layout has already been provisioned.

1. In **Releem/mcp-releem → Settings → Environments**, create `production`
   and restrict deployments to the repository's default branch.
2. Add the environment secrets below. The dedicated deployment public key is
   already installed on the current host. Keep these ignored files out of Git.

   | Secret | Existing local source |
   |---|---|
   | `DEPLOY_SSH_KEY` | `.agent/deploy/github_ed25519` — dedicated automation private key |
   | `DEPLOY_KNOWN_HOSTS` | `.agent/deploy/known_hosts` — verified full host-key entry |

   With an authenticated GitHub CLI, run from this checkout after creating the
   environment; the file contents are sent directly to GitHub secrets:

   ```sh
   gh secret set DEPLOY_SSH_KEY \
     --repo Releem/mcp-releem --env production \
     < .agent/deploy/github_ed25519
   gh secret set DEPLOY_KNOWN_HOSTS \
     --repo Releem/mcp-releem --env production \
     < .agent/deploy/known_hosts
   ```

   The workflow uses GitHub's ephemeral `GITHUB_TOKEN` for GHCR. Confirm the
   organization allows this repository to publish its package. Releem customer
   keys and the Cloudflare tunnel token are not deployment secrets in GitHub.
3. Review, commit and merge the application, deployment files and
   [workflow](.github/workflows/deploy.yml) into the default branch. The local
   implementation must be published along with the workflow.
4. Open **Actions → Deploy MCP production → Run workflow**, selecting that branch.
   The existing workflow is manual. It runs release/security checks, publishes
   the verified image to GHCR, deploys its immutable digest, then checks local
   and public health/authentication denial. App updates leave the tunnel running.
5. After the first manual deployment succeeds, optionally replace the workflow's
   trigger with the following to deploy on every default-branch push:

   ```yaml
   on:
     workflow_dispatch:
     push:
       branches:
         - main
   ```

   Replace `main` with the actual default branch. Commit and merge the change.
   Required environment reviewers will still pause deployment for approval;
   omit that requirement if unattended deployment is intended.
6. Confirm an authenticated client read after deployment. During a maintenance
   window, reboot the host and repeat the public checks and authenticated read
   to verify recovery. Both services use `unless-stopped`; health failures alone
   do not trigger a restart.

Inspect the deployed stack without changing it:

```sh
ssh ubuntu@40.160.8.37 'sudo /opt/mcp-releem/stack ps'
ssh ubuntu@40.160.8.37 'sudo /opt/mcp-releem/stack logs --tail 30 mcp cloudflared'
```

## Local HTTP setup with Codex and the real API

Requires Docker running, Docker Compose with `up --wait`, and **Codex CLI**.
Run the commands below from this checkout's root. This connects to the real API;
[synthetic demo instructions](docs/local-testing.md) are separate.

Save your key in Codex's private configuration. Codex sends it with each request;
MCP validates it and uses it to authenticate authorized Releem API reads.

```text
Codex -- Bearer key --> local MCP -- Releem-Secret-Key --> Releem API
```

### 1. Start the local HTTP server

```sh
export RELEEM_MCP_PUBLIC_URL=https://mcp.example.invalid/mcp
export RELEEM_API_BASE_URL=https://api2.dev.releem.com
export MCP_RELEEM_HOST_PORT=58000
export MCP_RELEEM_IMAGE=mcp-releem:local-http

docker compose --env-file /dev/null -p releem-local-http build mcp

docker compose --env-file /dev/null -p releem-local-http up \
  -d --no-build --pull never --wait --wait-timeout 90
```

The server listens only on `127.0.0.1:58000`. The `mcp.example.invalid` value
provides the expected Host header for local testing; it requires no DNS or TLS
setup. Remote hosting requires real HTTPS ingress.

**Do not put your API key in the server's environment or mount a key file.**
Compose's `--env-file /dev/null` prevents loading the checkout's `.env`; it does
not pass an environment file to MCP. Upstream calls use HTTPS to
`https://api2.dev.releem.com`, the owner-confirmed API origin.

### 2. Save the Codex connection and key

Open `~/.codex/config.toml` in your editor. Replace any existing `releem` entry
and its nested header table with this configuration:

```toml
[mcp_servers.releem]
url = "http://127.0.0.1:58000/mcp"

[mcp_servers.releem.http_headers]
Host = "mcp.example.invalid"
Authorization = "Bearer <YOUR_RELEEM_API_KEY>"
```

Replace `<YOUR_RELEEM_API_KEY>` with your actual key **locally in that file**.
Keep the `Bearer ` prefix. Remove any old `bearer_token_env_var` setting from
this connection so it uses the key you just configured.

- `url` is your local MCP endpoint.
- `Host` matches the server setting in step 1.
- `Authorization` contains your Releem API key and is sent with each request.

The key is stored as plaintext in this private client file. Keep it out of Git
and shared project configuration. On macOS/Linux, restrict file access:

```sh
chmod 600 ~/.codex/config.toml
```

Codex's [documented HTTP settings](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
support static request headers. The HTTP MCP container still has no global key
or customer `.env` mount.

### 3. Launch Codex and test

Start a new Codex CLI session:

```sh
codex
```

No environment variable or terminal key prompt is needed. In Codex, type `/mcp`
and check that **releem** is connected. Then ask:

> Use releem to list my accessible servers with limit=5. Ask me to select a server
> before inspecting its findings or query evidence.

This makes real read-only API calls with your key. Returned diagnostics reach
Codex and its model processing location. Database changes, task submission and
optimization creation are unavailable. After changing the key or configuration,
start a new Codex session to reload it.

### Restart or stop

From the checkout root, in a terminal with the four exports from step 1:

```sh
# Inspect or restart the existing service.
docker compose --env-file /dev/null -p releem-local-http ps
docker compose --env-file /dev/null -p releem-local-http restart mcp

# Stop and remove this Compose project's service/network.
docker compose --env-file /dev/null -p releem-local-http down
```

After changing server settings or rebuilding, run the `up` command again;
`restart` does not apply new configuration. See [Compose operations](docs/compose-hosting.md)
for remote hosting, pinned releases and rollback.

### Troubleshooting

Check liveness without an API key:

```sh
curl --fail --silent --show-error \
  -H 'Host: mcp.example.invalid' http://127.0.0.1:58000/healthz
```

Expected: `{"status":"alive"}`. This checks the MCP process, not upstream access.

| Problem | Action |
|---|---|
| Connection refused | Check Docker and `docker compose --env-file /dev/null -p releem-local-http ps`. |
| `400 invalid_host` | Keep the Host header in step 2 matched to the URL identity in step 1. |
| `401` or `upstream_auth_failed` | Check the `Authorization` header, its `Bearer ` prefix and the key's validity. |
| `403` | Check account permissions and any Origin restriction. |
| No telemetry or partial results | Read warnings; absent evidence does not establish database health. |

The Codex configuration was parsed with CLI 0.167.0 on 2026-11-11; loopback
liveness and unauthenticated 401 were checked without customer API calls.
See [client setup and verification limits](docs/clients/local-setup.md).

## Tools

| Tool | Inputs | Behavior |
|---|---|---|
| `servers` | Optional exact `hostname` list; `limit` 1–100, default 20 | Discover accessible IDs without choosing a target. Returns minimized metadata. |
| `server_findings` | Explicit `server_id`; optional sections `summary`, `health`, `security`, `schema` | Read metadata and latest check snapshots. Schema filters/limits are explicit; missing, unknown and decode-error states remain visible. |
| `query_evidence` | Explicit `server_id`; `view=analytics`, `proposals`, `optimizations` or `optimization` | Rank expensive queries or read existing proposals/optimization records and selected stored plan facts. Never submit SQL or queue EXPLAIN. |
| `recommendations` | Default `scope=server` requires `server_id`; explicit `scope=fleet` lists accessible active servers; detail uses `recommendation_id` | Priorities, bounded review/status history and safe typed evidence references. `done` is not proof of execution or improvement. |
| `configurations` | Explicit `server_id`; `view=history`, `latest` or `detail`; state ID for detail | Read bounded configuration state history, application periods and analysis summaries. Variable values and untyped metrics are omitted. |
| `metrics` | Explicit `server_id`; `view=catalog`, `series` or `compare` | Discover names/units, retrieve bounded samples or compare hourly trend summaries. |
| `events` | Explicit `server_id`; list window/offset or detail `event_id` string | Read incident timeline pages; no total or frozen snapshot. |
| `deadlocks` | Explicit `server_id`; list window or detail `deadlock_id` | Read recorded deadlock summaries and minimized detail, without dumps or transaction SQL. |
| `task_outcomes` | Explicit `server_id`; list filters or detail `task_id` | Read stored agent task status/report availability; never enqueue work. |
| `captured_sessions` | Explicit `server_id`; `mode=latest` or paired window | Read aggregates from stored processlist captures; never create a capture or claim live sessions. |

No write tools exist. Unknown tool names are rejected at dispatch, and the API
client has a closed GET-only operation registry. Raw SQL, task execution, schema
changes, query submission, chat and customer administration are unavailable.
Fleet scope is explicit and checked against accessible inventory. Opaque review
payloads, actor identities and status reasons remain omitted from detail.

## Alternative: local stdio installation

Python 3.12 or newer and uv are needed for the package workflow. No package has
been published; install from this checkout into an isolated environment:

```sh
uv sync --locked
uv run mcp-releem --check
uv run mcp-releem
```

Provision the API token outside chat and source control. Set exactly one of
`RELEEM_API_TOKEN_FILE` (preferred, restricted file permissions),
`RELEEM_API_TOKEN`, or `RELEEM_SECRET_KEY` in the client's environment. These are
local upstream API credential sources. Hosted callers supply their own API key per request. Multiple sources
are rejected. The CLI does not read `.env` automatically. To use a file explicitly:

```sh
uv run --locked mcp-releem --env-file .env --check
uv run --locked mcp-releem --env-file .env
```

The file parser does not execute shell code or expand `${...}`; existing
environment variables take precedence by name. Conflicting credential sources
remain an error, including conflicts between the file and environment. See [.env.example](.env.example) for settings; it contains no
credential. `--check` validates configuration and prints only redacted settings,
without contacting Releem. `--version` needs no configuration.

Local client command/args example (replace the checkout path):

```json
{"mcpServers":{"releem":{"type":"stdio","command":"uv","args":["--directory","/absolute/path/to/checkout","run","--locked","mcp-releem"]}}}
```

Configure the token-file environment variable for that client outside the
shared JSON. Environment inheritance/secret-file access differs by client;
Claude Code 2.1.70 registration/connection health passed in an isolated project
with a synthetic key and network-disabled server. Interactive tool/prompt use and
Cursor application onboarding remain unverified. Package tests verify both MCP
protocol revisions. See [client setup and verification](docs/clients/local-setup.md).

The local MCP process calls the configured Releem API. Its results reach the
MCP host and may reach that host's model provider; local installation does not
imply on-premises processing or air-gapped operation.

## Recommendation evidence and fleet scope

`recommendations` keeps explicit server selection by default. Omitting
`server_id` does not select a server or imply fleet access. Use `scope=fleet`
explicitly for a list across accessible active servers, with no `server_id` or
detail mode. Each fleet call reads inventory using the same credential, checks
every returned parent ID, then returns the bounded upstream page. Foreign rows
fail without exposing data/totals. Inactive/deleted servers are excluded upstream;
an empty fleet page does not establish fleet health. Shared HTTP additionally
validates the request key and scopes every API client to its inventory.

Both list scopes support the existing filters and limit 1–100 (default 20),
offset 0–10000. Filters are checked against returned rows. Pages are not frozen
snapshots; concurrent updates can shift them. Dates normalize to UTC and naive
source dates carry a provenance warning.

Server detail adds the current review's score/base/adjustment/rationale and
review/status histories. `history_limit` is detail-only, 1–20, default 10 per
history, retaining upstream order without assuming newest-first. Missing history
remains null/unavailable; explicit empty history remains distinguishable. Local
omission counts, unknown statuses/categories and missing current review remain
visible. Opaque review details/input snapshots, actor identities, reason text
and arbitrary evidence pointers are omitted with partial coverage. Large details
may return a size error; reduce `history_limit` to narrow the response.

Recognized source links produce `evidence_reference` with a registered tool and
typed arguments. Only canonical, same-server API paths matching the source type
are accepted; raw URLs are neither returned nor fetched. Unknown, malformed,
absolute and cross-server links are rejected as references while other detail
remains available. Schema references address the latest run, not a pinned
historical snapshot; source identities and exact analysis IDs remain distinct.
Reading a reference is a separate caller choice and still enforces tool
permissions. No status update, application or evaluation is triggered.

```json
{"scope":"fleet","view":"list","status":"new","limit":10}
{"server_id":"101","view":"detail","recommendation_id":601,"history_limit":5}
```

## Schema findings

Request `server_findings` with `sections` containing `schema`. Defaults remain
`summary`, `health` and `security`; the schema read is opt-in. Schema-only inputs
are optional `schema_name`, canonical `check_type`, and `schema_limit` (1–100,
default 20). These fields are rejected unless the schema section is selected.
Sections must be unique. At most five upstream reads occur for all four sections.

Supported check types are `missing_primary_key`, `unused_index`, `duplicate_index`,
`auto_increment`, `collation`, `character_set`, `table_engine` and
`table_fragmentation`. `check_type` maps to the upstream `type` filter. Schema
name filtering is performed upstream; arbitrary check payloads are omitted, so
the adapter cannot independently re-evaluate that filter against raw objects.

A null snapshot timestamp means `not_run`, with partial coverage. An empty list
from a completed run means `no_matches` when filters were applied, or
`no_findings_in_completed_run` when unfiltered. None establishes database health
or full schema coverage. Counts, finding flags and snapshot/fetch timestamps are
preserved; unknown types/flags, stale snapshots, decode errors, missing scope and
omitted rows remain explicit. Raw JSON payloads, SQL and object detail are omitted
even when sensitive incident detail is enabled. Large combined results fail with
a bounded size error; narrow sections/filters or reduce `schema_limit`.

```json
{"server_id":"101","sections":["schema"],"check_type":"unused_index","schema_limit":10}
{"server_id":"101","sections":["health","security","schema"],"schema_name":"example_db"}
```

## Diagnostic prompts and reference

Four MCP prompts provide static guidance for existing read tools:

| Prompt | Arguments | Workflow |
|---|---|---|
| `why_database_slow` | Canonical `server_id` string | Findings, priorities, metric windows, expensive queries and recorded deadlocks |
| `investigate_queries` | Canonical `server_id` string | Query ranking and up to three existing proposal investigations |
| `explain_recommendation` | `server_id`, positive decimal `recommendation_id` string | Existing recommendation rationale, applicability and evidence limitations |
| `incident_changes` | `server_id`, optional paired `start_time`/`end_time` strings | Timeline from existing events, configurations, tasks and metrics |

MCP prompt arguments are strings. Incident windows require explicit offsets,
whole-second boundaries, nonzero duration and at most seven days. With no window,
the prompt asks the user to select one before incident reads. Invalid arguments
and unknown prompt names return sanitized protocol errors.

Prompts do not invoke tools, grant permissions, enable sensitive reads or execute
changes. They require explicit targets, bounded reads, evidence timestamps,
missing-data/coverage caveats and a distinction between observations and
hypotheses. Client support for selecting prompts varies; manual tool calls remain
available. `releem://reference` is a static release-versioned Markdown resource
with tool contracts, units/time semantics, status codes, permissions and data-path
limitations. It contains no customer evidence or configuration/secrets.

## Query investigation

`query_evidence` supports four typed views:

| View | Inputs / bounds | Evidence |
|---|---|---|
| `analytics` (default) | `period`: positive integer string with optional m/h/d suffix (bare means days), default `1d`, maximum 90 days locally. Optional offset-aware whole-second `start_date`/`end_date`; end requires start, overrides a valid period, and span ≤90 days. Deprecated `period_days` alias: 1, 7, 14, 30, 60 or 90; cannot combine selectors. UTC timezone, schema/RE2 filter, documented sort and order; limit 1–100, default 20 | Effective upstream half-open window, query fingerprints, call counts, latency in ms, cumulative seconds and original percentages. Nulls remain null. Percentages use all queries matching filters, not only returned rows. |
| `proposals` | `schema_name` and `query_id` required; limit 1–100 locally | Existing proposals from the latest analysis containing them; no new analysis is created. |
| `optimizations` | Optional schema filter; limit 1–100 | Newest saved optimization records, numeric workflow status and before/after measurements with original units. Unknown statuses retain their code. |
| `optimization` | `optimization_id` required; no list filters | One same-server record, up to 20 matching linked proposals, existing plan availability and selected facts. |

Examples (identifiers are placeholders):

```json
{"server_id":"101","view":"analytics","period":"1d","limit":10}
{"server_id":"101","view":"proposals","schema_name":"example_db","query_id":"abc123"}
{"server_id":"101","view":"optimization","optimization_id":501}
```

Returned query windows are validated against requested bounds/duration; mismatch fails explicitly.
Check results can have null/absent status and metadata. Only explicit `failed=true` enters
failed summaries; unknown states remain visible. Documentation URLs are represented by a
presence flag and never fetched. Configuration `latest` means the server's newest state,
including a new state of an older logical configuration. Average comparison windows are
`[start_time,end_time)`; series bucket anchoring remains separately unconfirmed.

Raw SQL, rewritten SQL, predicates, table/index names from plans, raw error text
and full plan text are omitted. Existing JSON plans expose only recognized
node/access types and selected numeric fields; textual/unrecognized plans expose
availability, not invented facts. Omitted/missing plan detail and clipped linked
proposals mark partial coverage. This is a conservative field extractor, not a
complete plan parser or an engine/version compatibility guarantee. Planner cost
is not elapsed time; before/after observations and workflow status do not prove
causation or guaranteed improvement.

The query endpoints offer capped lists without a total/cursor; coverage is
explicitly incomplete and no pagination cursor is invented. The configured byte
budget still applies. A missing query list means no evidence for that window and
filter, not that the database is healthy.

## Configuration states and metrics

`configurations` defaults to `history` with limit 20 (1–100). `latest` requests
only the server's newest state, including a later state of an older logical configuration. `detail` requires
`configuration_status_id`, which differs from `configuration_id`: repeated states
of the same configuration remain separate. No total or pagination cursor is
invented. Detail preserves application/restart status, null analysis and the
documented half-open application period. Variable values, raw source/original
configuration, JSON recommendations and untyped evaluation metrics are omitted
with explicit partial coverage. State records do not prove effective settings.

`metrics` defaults to a bounded `catalog` (limit 20, maximum 100). `series`
requires exactly one `metric_name` or server-scoped `itemid`; the server catalog
provides its units and identity. Optional paired `start_time`/`end_time` must have
timezone offsets; the default is the previous hour, resolved once. Raw windows
are at most 31 days, hourly trends at most 366 days. `interval` is a positive
integer ending in `m`, `h` or `d`; `aggregation` is `avg`, `sum`, `min` or `max`
and requires an interval or `use_trends=true`. Trend failures never trigger a
silent raw-data fallback. At most 500 points are returned; larger series or byte
budgets fail explicitly so the caller can narrow the request. No silent sampling.

`compare` requires `metric_names` (1–4 unique names) and accepts paired current
and optional `baseline_start_time`/`baseline_end_time` windows, each at most 366
days. Defaults are the previous hour and its immediately preceding equal-length
window. Two upstream average reads preserve nullable average/min/max values.
The average is the **mean of hourly averages**, not a weighted raw-sample mean.
Missing evidence, unit/identity mismatch and zero baselines produce null deltas
with explicit reasons. Window inclusion and default upstream aggregation are
marked unspecified where the contract does not define them. Gaps, empty series
and before/after differences do not establish health or causation.

The owner confirmed UTC for upstream timestamps without offsets. These series
times are normalized to UTC with a `source_timezone_utc` warning; caller inputs
still require offsets. A bounded live series check passed using aligned
five-minute boundaries. Upstream interval bucket anchoring remains unspecified:
out-of-window samples fail explicitly. Use explicit aligned windows for grouped
reads. See [the live check receipt](docs/api-checks-2026-11-11.md).

Placeholder calls:

```json
{"server_id":"101","view":"detail","configuration_status_id":5}
{"server_id":"101","view":"series","metric_name":"Questions","interval":"5m","aggregation":"avg","start_time":"2026-11-09T12:00:00Z","end_time":"2026-11-09T13:00:00Z"}
{"server_id":"101","view":"compare","metric_names":["Questions"],"start_time":"2026-11-09T12:00:00Z","end_time":"2026-11-09T13:00:00Z"}
```

## Incident investigation

`events`, `deadlocks` and `task_outcomes` default to `view=list`, limit 20
(1–100). Detail requires the corresponding record ID and forbids list filters.
Every call requires an explicit server; returned parent/record IDs must match.
Event IDs remain strings, including UInt64 values larger than JavaScript's safe
integer range. No tool creates tasks, captures, EXPLAIN plans or database changes.

Events and deadlocks default to the preceding hour. Paired offset-aware
`start_time`/`end_time` windows may span at most seven days. Events use inclusive
whole-second boundaries; fractional seconds are rejected. `events.offset` is
0–10000. A full page offers a next offset, without a total count or snapshot:
concurrent arrivals can shift pages and cause duplicates/skips. Duplicates are
removed only within the fetched page. If output budgeting drops rows, the cursor
is cleared and the caller must narrow the window. Deadlocks have a cap, not a
traversal cursor; unknown duration `-1`/null is retained with seconds as the unit.

Task lists accept nonnegative `status`/`type_id` filters. Unknown numeric codes
are retained with null labels. Missing final reports, nullable exit codes and
output/error availability remain visible; successful status alone does not prove
effective settings or improved performance. There is no automatic polling/retry.

`captured_sessions` defaults to `mode=latest`, which omits upstream time bounds.
`mode=window` requires a paired window of at most 24 hours. Limit is 1–20,
default 5; latest mode retains at most one capture. Outputs state `live=false`
and show capture time. Recognized JSON processlist arrays yield only command
counts and maximum observed duration in seconds. At most 500 rows per capture
are examined. Unsupported text, missing payloads and partial decoding stay
explicit; SQL, user/host/session IDs and raw processlist rows are omitted.

**Sensitive reads are disabled by default.** Event/deadlock/task detail and all
captured-session reads require administrator configuration
`RELEEM_MCP_SENSITIVE_DETAILS=true`. Without it, dispatch returns
`sensitive_detail_disabled` before contacting the API. Model arguments cannot
enable it. Even when enabled, arbitrary event bodies, deadlock dumps/transaction
text and task parameters/output/error text are omitted, with partial coverage
and availability metadata. This local setting is not hosted authentication.
An event-detail 404 can mean that a summary has no associated payload.

Placeholder calls:

```json
{"server_id":"101","view":"list","limit":10,"offset":0}
{"server_id":"101","view":"detail","event_id":"801"}
{"server_id":"101","view":"detail","task_id":401}
{"server_id":"101","mode":"latest"}
```

## Docker

Build the nonroot local stdio runtime:

```sh
docker build --target runtime -t mcp-releem:local .
docker run --rm -i --read-only --tmpfs /tmp --cap-drop=ALL \
  -e RELEEM_API_TOKEN_FILE=/run/secrets/releem \
  --mount type=bind,src=<LOCAL_TOKEN_FILE>,dst=/run/secrets/releem,readonly \
  mcp-releem:local
```

The mounted file must be readable by container user 65532 under the customer's
secret-management policy. Do not use a TTY, publish a port or copy tokens into
the image. Append `--check` to run the redacted configuration check. Release
instructions should pin the built image digest rather than a floating tag.

Shared authenticated HTTP is available through `--transport streamable-http`
with `RELEEM_MCP_PROFILE=hosted` and an explicit HTTPS public URL. It uses the same
customer API key on each request; global customer credentials are forbidden.
See [hosted pilot setup and boundaries](docs/hosted-pilot.md). Use [Docker Compose](docs/compose-hosting.md)
for host start/restart, health checks and rollback. This is an
developer preview; public health and authentication denial were reported passing
on the managed deployment. Authenticated client onboarding, reboot recovery and
release approval remain open.

Run `bash scripts/check-release.sh` for offline container verification and a
checksummed local candidate bundle. See [v0.1.0 gates](docs/releases/0.1.0.md).

## Configuration and result semantics

- `RELEEM_API_BASE_URL`: default above; administrator-controlled HTTPS origin
  override, no userinfo/query/fragment/base path. Redirects are refused.
- `RELEEM_API_CA_BUNDLE`: optional enterprise CA file. TLS verification remains on.
- `HTTPS_PROXY`: optional administrator proxy; proxy credentials are never printed.
  Automatic environment proxy discovery and `NO_PROXY` are not used in this slice.
- `RELEEM_API_ALLOW_PRIVATE=true`: explicit administrator opt-in for literal private
  addresses and localhost. DNS/egress controls remain the administrator's
  responsibility; hosted profile rejects this opt-in and requires approved egress controls.
- `RELEEM_MCP_PROFILE=local` selects stdio; `hosted` selects authenticated HTTP.
  `RELEEM_MCP_READ_ONLY=true` is mandatory. Unknown `RELEEM_MCP_*` settings are rejected.
- `RELEEM_MCP_MAX_OUTPUT_BYTES`: structured-result budget, default 24576,
  configurable 2048–65536. Text summaries add at most 1000 characters.
- `RELEEM_MCP_SENSITIVE_DETAILS`: `false` by default; only `true`/`false` accepted.
  Administrator opt-in for minimized incident detail and capture aggregates.

Results include `status`, typed data, evidence fetch/report timestamps, coverage,
warnings and redaction policy. Errors are explicit and sanitized. Partial reads
retain component errors; absent reports cannot imply health. Reports older than
15 minutes carry an age warning, not a claim about the upstream freshness SLA.
Recommendation pagination reports upstream totals/next offset; capped inventory
is explicitly incomplete. Narrow filters when rows/text are omitted. No automatic
retries, default server selection or evidence-link fetching occur.

Default field allowlists omit users, IPs, raw evidence links, arbitrary review
payloads and non-scalar check values. Text screening removes known credential,
email and IPv4 patterns and suppresses recognized SQL-bearing text. Screening
cannot establish anonymity: hostnames/object names and unrecognized free-form
sensitive content can still be confidential. Keep model/client access restricted.
Upstream text is untrusted evidence, never an instruction to run commands.

## Development and verification

Run `bash scripts/check-release.sh` for the complete offline release check. It
runs format/lint/type checks, synthetic tests, wheel/runtime installation checks,
authenticated HTTP journeys and one isolated Compose recovery smoke. Set
`RELEEM_RELEASE_SECURITY=true` only when requesting public advisory scans.

Transport tests share the release synthetic fixtures. The separate Phase 0 SDK
experiment and duplicate HTTP handshake tests were retired; authentication,
tenant isolation, read-only enforcement and deployment recovery remain covered.

All dependency installation/checks should run in containers. The base image is
pinned by digest, uv is pinned and dependencies are locked in `uv.lock`.

```sh
docker build --target checks -t mcp-releem:checks .
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks ruff check --no-cache src tests
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks ruff format --check --no-cache src tests
docker run --rm --network none --read-only --tmpfs /tmp mcp-releem:checks mypy --cache-dir /tmp/mypy-cache src
docker build --target artifacts --output type=local,dest=dist .
```

Tests use synthetic API responses, including HTTP transport fixtures bound only
to loopback. They require no Releem credentials/network. Distribution artifacts
are a wheel and sdist under `dist/`. Buildx metadata can be redirected with
`BUILDX_CONFIG=/tmp/mcp-releem-buildx` in restricted environments.

Upgrade by reviewing changes, installing the reviewed lock/wheel or rebuilding a
pinned image and restarting the client. Uninstall by removing the client's MCP
entry/environment and local environment/container; revoke credentials separately
when required. Troubleshooting: use `--check` for configuration, check token-file
permissions, CA/proxy settings and upstream authorization; missing telemetry and
HTTP 401/403/422/429 are distinct failures, never successful empty findings.

## Architecture and remaining work

- [Implementation status and verification](docs/implementation-status.md)
- [Architecture and phased plan](docs/plans/2026-11-10-mcp-releem.md)
- [Complete API coverage matrix](docs/plans/api-coverage.md) — planned full scope,
  broader than the currently implemented tools
- [Source register](docs/plans/source-register.md)
- [SDK/client compatibility scope](docs/clients/compatibility.md)
- [Historical Phase 0 results](docs/phase0-status.md)

Remaining work includes stronger engine-aware data policies, full client application
onboarding and deployed streaming/revocation/isolation verification. API roles, agent/engine
compatibility remain unverified across deployments. Bounded live checks were
authorized and performed for this account; see [API check scope](docs/api-checks-2026-11-10.md).
Publishing and broader live testing require separate authorization; deployment
to the current managed host was separately authorized.

The previous dbharness change-execution harness is excluded from this initial
snapshot. Its history was backed up locally before replacing main; its execution
and bearer-token forwarding behavior are not inherited.

Release security: `RELEEM_RELEASE_SECURITY=true bash scripts/check-release.sh`
also audits exact runtime dependencies/image against public advisory services.
It requires network access and fails on incomplete coverage or HIGH/CRITICAL
image findings. See [current security/local-client review](docs/releases/security-review-2026-11-11.md).

Docker runtime security: the image now uses digest-pinned Python3.12/Alpine3.24,
with fixed stable OS packages. Its unused SQLite library and Python bindings are
removed; customer Python installations are unaffected. See [runtime decision](docs/decisions/0003-hardened-runtime.md).
