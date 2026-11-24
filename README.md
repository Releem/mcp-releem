# Releem MCP

Releem MCP gives developers, DevOps engineers, and database administrators read-only access to Releem diagnostics from their AI assistant. Use it to:

- **Review recommendations.** See what Releem recommends for a server, why it matters, and what evidence supports it.
- **Explore database performance.** Compare collected metrics across time windows or find the queries that accounted for the most execution time.
- **Investigate incidents.** Build a timeline from recorded events, configuration changes, and metrics to narrow down possible root causes.

The [quickstart](#connect-a-client) uses Releem data to find the five queries with the most cumulative execution time over the past 24 hours and show their normalized SQL when available.

<a name="detailed-guides"></a>

- [Connect a client](#connect-a-client) to start an investigation.
- [Look up a tool](#tools) to check arguments, units, limits, or permissions.

## Connect a client

### Hosted setup

Use your Releem Portal **Profile** API key to connect to `https://mcp.releem.com/mcp`. The hosted service reads diagnostics within that key’s permissions. Results reach your client and may reach its model provider. 

Choose [Codex CLI](#connect-codex), [Claude Code](#connect-claude-code), or the [Claude app](#connect-the-claude-app). For Docker or stdio, see [local setup](#local-setup).

<a name="1-connect-codex"></a>

#### Connect Codex

On macOS or Linux, run `mkdir -p ~/.codex`, then open or create `~/.codex/config.toml`. Add this entry, replacing any existing `releem` table and its nested settings.

```toml
[mcp_servers.releem]
url = "https://mcp.releem.com/mcp"

[mcp_servers.releem.http_headers]
Authorization = "Bearer <YOUR_RELEEM_API_KEY>"
```

Replace the placeholder in your private config, keeping the `Bearer ` prefix. On macOS or Linux, restrict file access and start a fresh Codex session.

```sh
chmod 600 ~/.codex/config.toml
codex
```

Check for `releem` under `/mcp`, then [list your servers](#list-your-accessible-servers). [Codex MCP settings](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

#### Connect Claude Code

Register Releem once in your private user settings. Keep the single quotes so Claude Code reads the key from its environment at launch.

```sh
claude mcp add --transport http --scope user releem https://mcp.releem.com/mcp \
  --header 'Authorization: Bearer ${RELEEM_MCP_API_KEY}'
```

If replacing a user entry, first run `claude mcp remove --scope user releem`. A same-named project or local entry takes precedence there.

Use your secret manager or private environment configuration to make `RELEEM_MCP_API_KEY` available to Claude Code.

Check for `releem` under `/mcp`, then [list your servers](#list-your-accessible-servers). [Claude Code MCP settings](https://code.claude.com/docs/en/mcp)

#### Connect the Claude app

This setup requires the **Request headers** beta. Organization connectors share one key across users. For individual permissions, or if the field is missing, use [Claude Code](#connect-claude-code).

1. In Claude, open **Customize → Connectors → Add → Add custom connector**. For a Team or Enterprise connector, an Owner uses **Organization settings → Connectors → Add → Custom** and selects **Web** if asked for a connector type.
2. Name the connector `Releem` and enter `https://mcp.releem.com/mcp`. Select **Continue** if prompted.
3. Under **Authentication**, choose **No sign-in**. Find **Request headers**, under **Advanced** if needed. Add `Authorization` with the value `Bearer <YOUR_RELEEM_API_KEY>`, substituting the actual key in the connector dialog. Make the header **Required**, then select **Add**.
4. If Releem shows **Connect** in **Customize → Connectors**, select it first.
   In your chat, open **+ → Connectors** and enable **Releem** for the
   conversation. Check access with the [first inventory read](#list-your-accessible-servers).

[Claude app request-header instructions](https://claude.com/docs/connectors/custom/add-unlisted#authenticate-with-request-headers)

### List your accessible servers

> List up to five servers I can access in Releem. Show their IDs and wait for me to choose one.

Reply with one returned server ID to select your target. An authenticated inventory can be empty. If it is, check which servers your account can see in Releem.

### Rank queries on the selected server

> For the server I selected, show the five queries with the most cumulative execution time over the past 24 hours. Show normalized SQL beside each fingerprint, with calls, total time and time share. Label partial prefixes. If text is missing, keep the row and explain why. Include the returned window, units, coverage and any evidence or freshness warnings.

Read `sum_time_sec` for total execution time, `avg_time_ms` for the average per execution, and `calls` for the execution count. Percentages cover all matching queries in the returned UTC window.

Check coverage and warnings. A top-five result can have `status=ok` and still be incomplete. An empty result means Releem returned no rows for that server and window. [Query reference](#query-investigation)

## Troubleshooting

| What you see | What to check |
| --- | --- |
| `401` during connection or a tool read | Check that your client sends the intended, valid key and the `Bearer ` prefix. Reload your client configuration after changes. A keyless probe to `/mcp` is expected to return `401`. |
| `400 invalid_host` on the public endpoint | Remove any `Host` header left over from local HTTP testing and check the configured URL. |
| `503 upstream_unavailable` | The server could not validate inventory with the upstream API. A healthy `/healthz` only confirms process liveness. |

<a name="other-ways-to-connect"></a>

## Local setup

Choose local HTTP for a loopback service that accepts a key from each client, or stdio for a subprocess that reads a local credential. Both use the Releem API and return diagnostics to your client.

<a name="local-http-setup-with-codex-and-the-real-api"></a>

### Local HTTP with Docker

From the checkout root, use Docker, Docker Compose with `up --wait`, and Codex CLI. This recipe connects to the real Releem API.

#### 1. Start the local HTTP server

```sh
export RELEEM_MCP_PUBLIC_URL=https://mcp.example.invalid/mcp
export RELEEM_API_BASE_URL=https://api2.releem.com
export MCP_RELEEM_HOST_PORT=58000
export MCP_RELEEM_IMAGE=mcp-releem:local-http

docker compose --env-file /dev/null -p releem-local-http build mcp

docker compose --env-file /dev/null -p releem-local-http up \
  -d --no-build --pull never --wait --wait-timeout 90
```

The server listens on `127.0.0.1:58000`. The local `Host` header must match `mcp.example.invalid`, which requires no DNS setup. Each client supplies its own key. Keep customer credentials out of the container environment and mounts. The Compose commands skip the checkout’s `.env`.

#### 2. Save the Codex connection and key

Use the private configuration and file permissions described under [Connect Codex](#connect-codex). Replace its `releem` entry and nested tables with this local configuration.

```toml
[mcp_servers.releem]
url = "http://127.0.0.1:58000/mcp"

[mcp_servers.releem.http_headers]
Host = "mcp.example.invalid"
Authorization = "Bearer <YOUR_RELEEM_API_KEY>"
```

Keep the `Bearer ` prefix when entering the key. Remove any old `bearer_token_env_var` setting for this connection.

#### 3. Launch Codex and test

Start a fresh `codex` session, check `/mcp`, then [list your servers](#list-your-accessible-servers).

#### Restart or stop

Run these commands from the checkout root with the exports from step 1.

**Restart the service**

```sh
docker compose --env-file /dev/null -p releem-local-http restart mcp
```

After a rebuild or settings change, repeat the `up` command from step 1.

**Stop and remove the local service and network**

```sh
docker compose --env-file /dev/null -p releem-local-http down
```

<a name="troubleshooting-local"></a>

#### Troubleshoot local HTTP

Check liveness without an API key:

```sh
curl --fail --silent --show-error \
  -H 'Host: mcp.example.invalid' http://127.0.0.1:58000/healthz
```

A healthy MCP process reports `alive`. To check upstream access, list your servers in the client.

| Problem | Action |
|---|---|
| Connection refused | Check Docker and `docker compose --env-file /dev/null -p releem-local-http ps`. |
| `400 invalid_host` | Keep the Host header in step 2 matched to the URL identity in step 1. |
| `401` or `upstream_auth_failed` | Check the `Authorization` header, its `Bearer ` prefix and the key's validity. |
| `403` | Check account permissions and any Origin restriction. |

<a name="alternative-local-stdio-installation"></a>

### Local stdio from source

Use stdio when your MCP client will launch the server as a local subprocess.
You need Python 3.12 or newer, uv, this checkout and an existing Releem API key.

Before starting the server, save the key in a private file outside the checkout.
Give the client process read access to that file and restrict other access. Set
exactly one credential source. Prefer `RELEEM_API_TOKEN_FILE`. The other
supported sources are `RELEEM_API_TOKEN` and `RELEEM_SECRET_KEY`.

From the checkout root on macOS or Linux, replace the private file path:

```sh
chmod 600 /absolute/path/to/releem-token
export RELEEM_API_TOKEN_FILE=/absolute/path/to/releem-token
uv sync --locked
uv run --locked mcp-releem --check
```

The check validates configuration offline. In the [private Codex config](#connect-codex), replace the `releem` entry with the following and set both paths.

```toml
[mcp_servers.releem]
command = "uv"
args = ["--directory", "/absolute/path/to/checkout", "run", "--locked", "mcp-releem"]

[mcp_servers.releem.env]
RELEEM_API_TOKEN_FILE = "/absolute/path/to/releem-token"
```

Start a fresh Codex session, check `/mcp`, and [list your servers](#list-your-accessible-servers).

Alternatively, supply local settings explicitly from a private dotenv file with a single credential source.

```sh
uv run --locked mcp-releem --env-file .env --check
uv run --locked mcp-releem --env-file .env
```

The CLI loads dotenv files only with `--env-file`. Inherited variables take precedence by name. Multiple credential sources are rejected. [Example settings](.env.example)

<a name="docker"></a>

### Local stdio in Docker

Build the nonroot local stdio runtime:

```sh
docker build --target runtime -t mcp-releem:local .
docker run --rm -i --read-only --tmpfs /tmp --cap-drop=ALL \
  -e RELEEM_API_TOKEN_FILE=/run/secrets/releem \
  --mount "type=bind,src=/absolute/path/to/releem-token,dst=/run/secrets/releem,readonly" \
  mcp-releem:local
```

The mounted file must be readable by container user 65532 under the customer's
secret-management policy. Do not use a TTY, publish a port or copy tokens into
the image. Append `--check` to run the redacted configuration check. Release
instructions should pin the built image digest rather than a floating tag.

### Upgrade or remove local setup

Review the new revision, sync its lockfile or rebuild the container, and
start a new client session. For HTTP, recreate the service with the earlier
`up` command so Compose applies configuration changes.

To remove the integration, delete the client entry, remove its local
credential configuration, and stop the local Compose project if you used one.
Revoke the key separately if required.

## Tools

Choose a server from your accessible inventory before asking about its diagnostics.

| Question | Tool |
| --- | --- |
| Which servers can I access? | `servers` lists IDs and metadata. Filter by exact `hostname` values or set `limit` (1–100, default 20). |
| Which queries used the most time? | [`query_evidence`](#query-investigation) ranks queries, shows available normalized SQL and retrieves existing proposals and plans. |
| What has Releem flagged? | [`server_findings`](#health-and-security-findings) reads health and security checks and optional [schema findings](#schema-findings). |
| Why did Releem recommend a change? | [`recommendations`](#recommendation-evidence-and-fleet-scope) returns rationale, review history and available evidence. |
| What changed in configuration or performance? | [`configurations` and `metrics`](#configuration-states-and-metrics) show recorded states, metric series and comparisons. |
| What happened during an incident? | [`events`, `deadlocks`, `task_outcomes` and `captured_sessions`](#incident-investigation) return recorded evidence for the selected server. |

For a guided investigation, see [diagnostic prompts](#diagnostic-prompts-and-reference).

### Query investigation

`query_evidence` supports four typed views:

| View | Inputs / bounds | Evidence |
|---|---|---|
| `analytics` (default) | Use a `period` such as `30m`, `24h` or `7d` (default `1d`, maximum 90 days). For explicit bounds use whole-second, offset-aware `start_date` and optional `end_date`. Limit 1–100, default 20. | Upstream normalized SQL (`query`), its `query_status`, fingerprint (`query_id`), calls, average latency, cumulative execution time and share of total time. |
| `proposals` | `schema_name` and `query_id` required; limit 1–100 locally | Existing proposals from the latest analysis containing them; no new analysis is created. |
| `optimizations` | Optional schema filter; limit 1–100 | Newest saved optimization records, workflow status IDs and before/after measurements with original units. Unknown statuses retain their code. |
| `optimization` | `optimization_id` required; no list filters | One same-server record, up to 20 matching linked proposals, existing plan availability and selected facts. |

For ranked answers, read `structuredContent.data.items` and show `query` beside `query_id` and the measurements. Releem normalizes the SQL upstream, so identifiers can remain visible. Only this normalized field supplies excerpts. Raw `query_text` is omitted. Use the row’s `schema_name` and `query_id` to look up existing proposals.

| `query_status` | What to show |
| --- | --- |
| `available` | The normalized statement. |
| `truncated` | The returned prefix, labeled as partial. Each excerpt is limited to 2,048 UTF-8 bytes. |
| `unavailable` | The fingerprint and metrics. Releem supplied no normalized text. |
| `withheld` | The fingerprint and metrics. The statement did not pass screening. |
| `budget_exhausted` | The fingerprint and metrics. The excerpt did not fit the space left in the ranking’s shared 8,192-byte text allowance. |

Optimization status timestamps use Unix seconds. A zero `timestamp_status` means the time is unavailable.

The returned UTC window includes its start and excludes its end. Use `sum_time_perc_total` descending to rank by cumulative execution time. Other sort fields are `sum_time_perc_first`, `calls` and `avg_time_ms`. Lists are capped and have no pagination cursor.

Plans expose selected access types and numeric fields. Raw SQL, predicates, object names from plans, and full plan text are omitted. Planner cost is an estimate. Use the reported measurement units when comparing before and after.

### Health and security findings

Only explicit `failed=true` checks enter the failed summary. Check snapshot timestamps, coverage, and warnings for unknown states or missing reports.

### Schema findings

By default, `server_findings` returns summary, health and security checks. Include `schema` in `sections` to use `schema_name`, `check_type` or `schema_limit` (1–100, default 20). Select each section once.

Supported check types are `missing_primary_key`, `unused_index`, `duplicate_index`,
`auto_increment`, `collation`, `character_set`, `table_engine` and
`table_fragmentation`. Schema name filtering happens upstream.

A missing snapshot timestamp means `not_run`. A completed check with an empty list means `no_matches` with filters or `no_findings_in_completed_run` without them. For a size error, narrow the filters or reduce `schema_limit`. Raw SQL and object details are omitted.

### Recommendation evidence and fleet scope

Supply `server_id` for a server list or detail. For a list across accessible active servers, use `scope=fleet` and omit `server_id`. Lists accept `limit` 1–100 (default 20) and `offset` 0–10000. Concurrent updates can shift pages.

For detail, supply the server and recommendation IDs. The result includes the available rationale, score and review/status histories. A `done` status records workflow progress. Check independent evidence to establish whether the change was applied or improved performance.

`history_limit` controls entries per history (1–20, default 10). Reduce it for oversized responses. When present, `evidence_reference` gives a tool and typed arguments for a separate read on the same server. Schema references point to the latest run.

### Configuration states and metrics

Use `configurations` with `history` (default, limit 1–100, default 20), `latest`, or `detail`. Detail requires the state’s `configuration_status_id`. A logical configuration can have several recorded states. The result includes application periods and restart status. Variable values and raw configuration are omitted.

Start with the `metrics` catalog to find metric names, IDs and units (limit 1–100, default 20).

- **Series.** Supply one `metric_name` or server-scoped `itemid`. The default window is the previous hour. Explicit windows need paired timestamps with offsets. Raw series cover up to 31 days and hourly trends up to 366 days. Use `interval` in minutes, hours or days (such as `5m`), with `avg`, `sum`, `min` or `max`. Aggregation requires an interval or `use_trends=true`. Use aligned windows and narrow the request if it exceeds 500 points or the output budget.
- **Compare.** Supply 1–4 unique `metric_names`. By default, the previous hour is compared with the hour before it. You can supply current and baseline windows of up to 366 days each. The reported average is the mean of hourly averages. Missing values, incompatible units or a zero baseline can leave a delta unavailable.

### Incident investigation

`events`, `deadlocks` and `task_outcomes` default to `view=list`, limit 20
(1–100). Detail requires the corresponding record ID and forbids list filters.
Every call requires an explicit server; returned parent/record IDs must match.
Event IDs remain strings, including UInt64 values larger than JavaScript's safe
integer range. No tool creates tasks, captures, EXPLAIN plans or database changes.

Events and deadlocks default to the previous hour. Explicit windows require paired timestamps with offsets and span up to seven days. Events include both whole-second boundaries. Event pages accept `offset` 0–10000 and can shift as records arrive. Narrow the window if output limits remove the next offset. Deadlock lists are capped. A duration of `-1` or null means unknown.

Filter tasks by nonnegative `status` or `type_id`. The returned type is an object with `id` and `name`, or null. A successful task status alone cannot establish a performance improvement.

Use `captured_sessions` with `mode=latest` for the most recent stored capture, or `mode=window` for a paired window up to 24 hours (limit 1–20, default 5). Check the capture time. Aggregates include command counts and maximum observed duration in seconds from up to 500 examined rows per capture.

#### Sensitive reads

Event, deadlock and task detail, plus all captured-session reads, require an administrator to set `RELEEM_MCP_SENSITIVE_DETAILS=true`. The default returns `sensitive_detail_disabled`. Even with access enabled, raw incident payloads, SQL and task output are omitted. An event-detail 404 can mean the summary has no stored payload.

### Diagnostic prompts and reference

Four MCP prompts provide static guidance for existing read tools:

| Prompt | Arguments | Workflow |
|---|---|---|
| `why_database_slow` | Canonical `server_id` string | Findings, priorities, metric windows, expensive queries and recorded deadlocks |
| `investigate_queries` | Canonical `server_id` string | Query ranking and up to three existing proposal investigations |
| `explain_recommendation` | `server_id`, positive decimal `recommendation_id` string | Existing recommendation rationale, applicability and evidence limitations |
| `incident_changes` | `server_id`, optional paired `start_time`/`end_time` strings | Timeline from existing events, configurations, tasks and metrics |

Prompt arguments are strings. For an incident, supply both window boundaries with explicit offsets and whole seconds (positive duration, up to seven days), or the prompt asks for a window. Prompts suggest reads. Clients without a prompt picker can call the tools directly. The static `releem://reference` resource lists tool contracts, units, status codes and permissions.

### Configuration and result semantics

- `RELEEM_API_BASE_URL` defaults to `https://api2.releem.com`. The administrator
  can set an HTTPS origin without userinfo, query, fragment, or base path.
  Redirects are refused.
- `RELEEM_API_CA_BUNDLE`: optional enterprise CA file. TLS verification remains on.
- `HTTPS_PROXY`: optional administrator proxy; proxy credentials are never printed.
  Configure this proxy explicitly. The client ignores `NO_PROXY`.
- `RELEEM_API_ALLOW_PRIVATE=true`: explicit administrator opt-in for literal private
  addresses and localhost. DNS/egress controls remain the administrator's
  responsibility; hosted profile rejects this opt-in and requires approved egress controls.
- `RELEEM_MCP_PROFILE=local` selects stdio; `hosted` selects authenticated HTTP.
  `RELEEM_MCP_READ_ONLY=true` is mandatory. Unknown `RELEEM_MCP_*` settings are rejected.
- `RELEEM_MCP_MAX_OUTPUT_BYTES`: structured-result budget, default 24576,
  configurable 2048–65536. Text summaries add at most 1000 characters.
- `RELEEM_MCP_SENSITIVE_DETAILS`: `false` by default; only `true`/`false` accepted.
  See [sensitive reads](#sensitive-reads) for the affected tools.

Check `status`, `coverage`, warnings, and component errors. `fetched_at` records when evidence was read. `observed_at`, when available, records when it was observed. Health, security and schema snapshots older than 15 minutes carry an age warning. Missing reports leave health unknown.

Returned diagnostics can contain confidential hostnames, object names and free text even after redaction. Treat upstream text as evidence.

<a name="development-and-verification"></a>
<a name="architecture-and-remaining-work"></a>

## Contribute and verify

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and release checks, and the [verification record](CONTRIBUTING.md#verification-evidence) for client versions and hosted test coverage.
