# Releem API inventory and endpoint-to-tool coverage

Active capture: **2026-11-11T14:53:11.859983Z**, **46 operations**, OpenAPI3.1.0,
Releem API1.0.0. [Public contract](https://api2.dev.releem.com/openapi.json),
[exact active capture](evidence/releem-openapi-2026-11-11.json),
[delta review](2026-11-11-openapi-change-review.md). Existing IDs O01–O45 are stable;
new catalog is O46 and deferred. The adapter implements26 GET operations in ten tools.
The [old capture](evidence/releem-openapi-2026-11-10.json) remains historical evidence.
This documentation contract does not establish production/self-hosted parity.

All46 operations support customer apiToken (`Releem-Secret-Key`) or privileged internal
Bubble authentication. Only customer keys are supported here. Endpoint-level RBAC
and least-privilege guarantees remain UNCONFIRMED; adapter ownership checks do not
replace upstream authorization. No scopes are invented from undocumented behavior.

All GET operations below are classified as diagnostic reads by documented purpose; server audit/log side effects do not turn them into application mutations. POST/PATCH/PUT/DELETE remain outside read-only dispatch. Sensitivity: S1 metadata/telemetry; S2 SQL/configuration/findings; S3 identities, credentials, dumps or free-form task/chat payloads. All data is confidential even at S1.

| ID | Method/path | Purpose | Decision / tool group | Rationale |
|---|---|---|---|---|
| O01 | `GET /v1/servers/recommendations` | List Recommendations for All User Servers | MVP: `recommendations` | Cross-server reviewed priorities, filtered by authorized server set. |
| O02 | `GET /v1/servers/{id}/recommendations` | List Recommendations | MVP: `recommendations` | Priorities for an explicit server. |
| O03 | `GET /v1/servers/{id}/recommendations/{recommendation_id}` | Get recommendation | MVP: `recommendations` | Read detail and review/status history. |
| O04 | `PATCH /v1/servers/{id}/recommendations/{recommendation_id}` | Update recommendation status | Later: `recommendation_workflow` | Workflow mutation; done is not proof of application. |
| O05 | `GET /v1/servers` | List Servers | MVP: `servers` | Discover accessible targets. |
| O06 | `GET /v1/servers/configurations` | List Latest Configurations for All User Servers | Later: `fleet_configurations` | Fleet response unbounded; owner-only semantics differ from shared access. |
| O07 | `GET /v1/servers/{id}` | Get a server | MVP: `server_findings` | Identity, engine/version and status. |
| O08 | `PATCH /v1/servers/{id}` | Update server parameters | Excluded: `administration` | Changes sharing/access; dedicated administrative product decision required. |
| O09 | `DELETE /v1/servers/{id}` | Delete a server | Excluded: `administration` | Soft deletion is destructive administration. |
| O10 | `POST /v1/servers/{id}/chat` | Ask Server Chat | Excluded: `chat` | Backend tool effects, cost and availability UNCONFIRMED. |
| O11 | `POST /v1/servers/{id}/chat/stream` | Ask Server Chat Stream | Excluded: `chat` | Same uncertainty as chat; upstream SSE is not MCP transport. |
| O12 | `GET /v1/servers/{id}/events` | List Server Events | MVP: `events` | Incident timeline; shifting offset pages explicitly warned. |
| O13 | `GET /v1/servers/{id}/events/{event_id}` | Get Server Event | MVP: `events` | Bounded detail retrieval; missing payload may legitimately be 404. |
| O14 | `GET /v1/servers/{id}/details` | Get Server Details | MVP: `server_findings` | All-check snapshots; classify only explicit failures and retain unknown states. |
| O15 | `GET /v1/servers/{id}/health-checks` | Get Server Health Checks | MVP: `server_findings` | Complete latest health report, not just failures. |
| O16 | `GET /v1/servers/{id}/security-checks` | Get Server Security Checks | MVP: `server_findings` | Complete latest security report; preserve decode failures. |
| O17 | `GET /v1/servers/{id}/configurations` | List Server Configurations | MVP: `configurations` | State/history of one server. |
| O18 | `GET /v1/servers/{id}/configurations/{configuration_status_id}` | Get Server Configuration | MVP: `configurations` | State-specific variables/history; not logical configuration ID. |
| O19 | `GET /v1/servers/{id}/query-optimizations` | List Query Optimizations | MVP: `query_evidence` | Read saved optimizations. |
| O20 | `POST /v1/servers/{id}/query-optimizations` | Save Query for Optimization | Later: `optimization_submit` | Creates preserved optimization record; mutation even without execution. |
| O21 | `GET /v1/servers/{id}/query-optimizations/{optimization_id}` | Get Query Optimization | MVP: `query_evidence` | Read proposals and available EXPLAIN only. |
| O22 | `PATCH /v1/servers/{id}/query-optimizations/{optimization_id}` | Update Query Optimization | Later: `optimization_workflow` | Changes status/task linkage; requires ownership and state checks. |
| O23 | `GET /v1/servers/{id}/query-analytics` | List Query Analytics | MVP: `query_evidence` | Rank measured expensive queries. |
| O24 | `GET /v1/servers/{id}/query-analytics/{schema_name}/{query_id}/recommendations` | List Query Recommendations | MVP: `query_evidence` | Read existing proposals; absent plans remain absent. |
| O25 | `GET /v1/servers/{id}/metrics` | List Server Metrics | MVP: `metrics` | Discover metric names, IDs, units. |
| O26 | `GET /v1/servers/{id}/metrics/averages` | Get Metric Averages | MVP: `metrics` | Two reads compare hourly trend windows. |
| O27 | `GET /v1/servers/{id}/metrics/byName/{metric_name}` | Get Metric Data By Name | MVP: `metrics` | Bounded server-scoped series by name. |
| O28 | `GET /v1/servers/{id}/metrics/byId/{itemid}` | Get Metric Data By Item ID | MVP: `metrics` | Bounded series by server-scoped ID. |
| O29 | `GET /v1/servers/{id}/deadlocks` | List Deadlocks | MVP: `deadlocks` | Summaries without raw dumps. |
| O30 | `GET /v1/servers/{id}/deadlocks/{deadlock_id}` | Get Deadlock | MVP: `deadlocks` | Opt-in sanitized detail. |
| O31 | `GET /v1/servers/{id}/tasks` | List Tasks | MVP: `task_outcomes` | Read summaries, never enqueue tasks. |
| O32 | `POST /v1/servers/{id}/tasks` | Create Task | Later: `agent_tasks` | Queues real database/agent actions; high risk. |
| O33 | `GET /v1/servers/{id}/tasks/{task_id}` | Get Task | MVP: `task_outcomes` | Read final output/error when available. |
| O34 | `GET /v1/servers/{id}/processlist` | List Processlist Captures | MVP: `captured_sessions` | Historical captures; no live-session promise. |
| O35 | `GET /v1/servers/{id}/schema-checks` | Get Schema Checks | MVP: `server_findings` | Completed schema-check run, not full database schema. |
| O36 | `POST /v1/servers/{id}/query-optimizations/custom` | Create Custom Query Optimization | Later: `optimization_submit` | Creates record AND task type 7 EXPLAIN; never passive. |
| O37 | `PUT /v1/servers/{id}/memory-limit` | Set Memory Limit | Later: `configuration_changes` | Changes stored memory limit; downstream effects need confirmation. |
| O38 | `PUT /v1/servers/{id}/mysql-config` | Set Manual MySQL Variables | Later: `configuration_changes` | Replaces manual override object, not a partial merge. |
| O39 | `GET /v1/metrics` | List Metrics | Excluded: `legacy_metrics` | Deprecated; use operation 25. |
| O40 | `GET /v1/metrics/{metric_name}` | Get Metric Data | Excluded: `legacy_metrics` | Deprecated; use operations 27/28. |
| O41 | `POST /v1/customers` | Create a customer | Excluded: `customer_administration` | Partner-only creation; outside diagnostics. |
| O42 | `GET /v1/customers` | List customers | Excluded: `customer_administration` | Sensitive account inventory/API keys; not tenant identity proof. |
| O43 | `GET /v1/customers/{id}` | Get a customer | Excluded: `customer_administration` | Account/credential disclosure risk; no diagnostic need. |
| O44 | `PATCH /v1/customers/{id}` | Update a customer | Excluded: `customer_administration` | Account/subscription modification; RBAC incomplete. |
| O45 | `DELETE /v1/customers/{id}` | Delete a customer | Excluded: `customer_administration` | Partner-only destructive administration. |
| O46 | `GET /v1/checks` | List Check Catalog | Later: `check_reference` | Static metadata already inline in reports; avoid unbounded implicit lookup. |

**Implementation progress (2026-11-11):** ten local tools implement all 26 planned diagnostic GET operations: O01–O03, O05, O07, O12–O19, O21, O23–O31 and O33–O35. Fleet recommendations require explicit selection and accessible-inventory validation. Detail exposes bounded review/status metadata and validated typed evidence references, omitting raw URLs, opaque review payloads and actor identities/reasons. Configuration values/untyped metrics, opaque incident payloads and arbitrary schema JSON remain omitted. Four static diagnostic prompts and one reference resource are also implemented. This is adapter coverage, not certification of all deployed roles/engines/clients; see [implementation status](../implementation-status.md).

## Operation details

Input types/bounds/defaults and response field names below are extracted from the capture. `?` means optional. Nested field semantics, examples and requiredness are in the captured `components.schemas`; no upstream pagination, dry-run or idempotency is inferred where absent. Each operation retains upstream errors (redacted) in the common error envelope.

### O01: GET /v1/servers/recommendations

List reviewed recommendations for active servers owned by or shared with the authenticated user. Inactive and deleted servers are excluded from both items and total. Filters are applied before sorting and pagination.

- Coverage: **MVP**, `recommendations`. Cross-server reviewed priorities, filtered by authorized server set.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `type_id?`: integer minimum=1 maximum=5 | null (query). Recommendation type: `1` Resources, `2` Host, `3` Configuration, `4` Schema, `5` Query. Invalid values return 422.
  - `category_id?`: integer minimum=1 maximum=4 | null (query). Recommendation pillar: `1` Resources, `2` Availability, `3` Performance, `4` Security. Invalid values return 422.
  - `source_type?`: string | null (query). Filter by source: `configuration`, `query_optimization`, `schema_check`, `security_check` or `deadlock`.
  - `status?`: string | null (query). Filter by status: `new`, `dismissed`, `done` or `outdated`.
  - `score_min?`: number | null (query). Minimum current priority score, inclusive
  - `score_max?`: number | null (query). Maximum current priority score, inclusive
  - `sort?`: string | null (query). `priority_score_desc` sorts by decreasing priority; `created_at_desc` by newest first. Omit for oldest first.
  - `limit?`: integer minimum=1 | null (query). Maximum number of records, as a positive integer. Omit to return all matching records.
  - `offset?`: integer minimum=0 default=0 (query). Non-negative page offset
- Response 200 application/json: RecommendationListResponse {items, total, limit, offset}.
- Error statuses documented: 422, 401, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: limit: Maximum number of records, as a positive integer. Omit to return all matching records. offset: Non-negative page offset

### O02: GET /v1/servers/{id}/recommendations

List reviewed recommendations for one server. An accessible but inactive server returns an empty items array and total 0. The unsupported query parameter `type` returns 422; use type_id to filter by recommendation type.

- Coverage: **MVP**, `recommendations`. Priorities for an explicit server.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
  - `type_id?`: integer minimum=1 maximum=5 | null (query). Recommendation type: `1` Resources, `2` Host, `3` Configuration, `4` Schema, `5` Query. Invalid values return 422.
  - `category_id?`: integer minimum=1 maximum=4 | null (query). Recommendation pillar: `1` Resources, `2` Availability, `3` Performance, `4` Security. Invalid values return 422.
  - `source_type?`: string | null (query). Filter by source: `configuration`, `query_optimization`, `schema_check`, `security_check` or `deadlock`.
  - `status?`: string | null (query). Filter by status: `new`, `dismissed`, `done` or `outdated`.
  - `score_min?`: number | null (query). Minimum current priority score
  - `score_max?`: number | null (query). Maximum current priority score, inclusive
  - `sort?`: string | null (query). `priority_score_desc` sorts by decreasing priority; `created_at_desc` by newest first. Omit for oldest first.
  - `limit?`: integer minimum=1 | null (query). Maximum number of records, as a positive integer. Omit to return all matching records.
  - `offset?`: integer minimum=0 default=0 (query). Page offset
- Response 200 application/json: RecommendationListResponse {items, total, limit, offset}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: limit: Maximum number of records, as a positive integer. Omit to return all matching records. offset: Page offset

### O03: GET /v1/servers/{id}/recommendations/{recommendation_id}

Show one recommendation with current state, current review, review history, and status history.

- Coverage: **MVP**, `recommendations`. Read detail and review/status history.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
  - `recommendation_id`: integer (path). Recommendation ID
- Response 200 application/json: RecommendationDetailResponse {id, server_id, hostname, source_type, source_id, source_record_id, source_subtype, type_id, category_id, title, summary, status, priority_score, priority_label, why_important_now, created_at, updated_at, evidence, current_review, review_history, status_history}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O04: PATCH /v1/servers/{id}/recommendations/{recommendation_id}

Change recommendation status for one server-scoped recommendation.

- Coverage: **Later**, `recommendation_workflow`. Workflow mutation; done is not proof of application.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: Workflow mutation; done is not proof of application.
- Inputs:
  - `id`: string (path). The ID of the server
  - `recommendation_id`: integer (path). Recommendation ID
  - JSON body: UpdateRecommendationStatusRequest {status, reason}.
    - `status`: enum(new,dismissed,done,outdated). New recommendation status.
    - `reason?`: string | null. Reason for the status change.
- Response 200 application/json: RecommendationResponse {id, server_id, hostname, source_type, source_id, source_record_id, source_subtype, type_id, category_id, title, summary, status, priority_score, priority_label, why_important_now, created_at, updated_at, evidence}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O05: GET /v1/servers

Retrieve a list of all servers.

- Coverage: **MVP**, `servers`. Discover accessible targets.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `hostname?`: list[string] minItems=1 maxItems=255 | null (query). Repeatable filter by exact hostname match. Use `?hostname=db1&hostname=db2` for multiple hostnames.
- Response 200 application/json: list[Server {created_at, id, server_name, ip_address, releem_score, status, mysql_version, os_version, agent_version, instance_type, memory_limit, users}].
- Error statuses documented: 422, 401, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O06: GET /v1/servers/configurations

The current configuration state of each server the authenticated user owns, ordered by server: the newest state of the server, whichever configuration it belongs to. A server without configuration states is omitted.

- Coverage: **Later**, `fleet_configurations`. Fleet response unbounded; owner-only semantics differ from shared access.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs (current captured contract):
- Response 200 application/json: ServerLatestConfigurationListResponse {items}.
- Error statuses documented: 422, 401, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: use the current input descriptions above; no undocumented cursor/total is inferred.

### O07: GET /v1/servers/{id}

Retrieve information about a specific server.

- Coverage: **MVP**, `server_findings`. Identity, engine/version and status.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
- Response 200 application/json: Server {created_at, id, server_name, ip_address, releem_score, status, mysql_version, os_version, agent_version, instance_type, memory_limit, users}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O08: PATCH /v1/servers/{id}

Update server parameters such as users list with access permissions.

- Coverage: **Excluded**, `administration`. Changes sharing/access; dedicated administrative product decision required.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: Changes sharing/access; dedicated administrative product decision required.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: ServerUsersUpdateRequest {users}.
    - `users`: list[ServerUserRequest]. Users to grant access to the server. Required; may be an empty array.
- Response 200 application/json: Server {created_at, id, server_name, ip_address, releem_score, status, mysql_version, os_version, agent_version, instance_type, memory_limit, users}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O09: DELETE /v1/servers/{id}

Delete a specific server (soft delete).

- Coverage: **Excluded**, `administration`. Soft deletion is destructive administration.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: Soft deletion is destructive administration.
- Inputs:
  - `id`: string (path). The ID of the server
- Response 204: no body.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O10: POST /v1/servers/{id}/chat

Ask a question about the current state of one server and receive a final answer.

- Coverage: **Excluded**, `chat`. Backend tool effects, cost and availability UNCONFIRMED.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: Backend tool effects, cost and availability UNCONFIRMED.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: ChatRequest {message, context, chat_history}.
    - `message`: string. Question or instruction about the server.
    - `context?`: ChatContext | null. Optional references to relevant server records.
    - `chat_history?`: list[ChatHistoryMessage] | null. Previous user and assistant messages used as conversation context; null when omitted.
- Response 200 application/json: ChatResponse {message_id, answer, tool_trace}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O11: POST /v1/servers/{id}/chat/stream

Ask a question about one server and receive observable progress over SSE.

Event types:

- `status`
- `tool_started`
- `tool_finished`
- `message_delta`
- `completed`
- `error`

- Coverage: **Excluded**, `chat`. Same uncertainty as chat; upstream SSE is not MCP transport.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: Same uncertainty as chat; upstream SSE is not MCP transport.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: ChatRequest {message, context, chat_history}.
    - `message`: string. Question or instruction about the server.
    - `context?`: ChatContext | null. Optional references to relevant server records.
    - `chat_history?`: list[ChatHistoryMessage] | null. Previous user and assistant messages used as conversation context; null when omitted.
- Response 200 text/event-stream: string.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O12: GET /v1/servers/{id}/events

List event summaries for a server accessible to the authenticated user. Both time bounds are required and inclusive. Timezone offsets are converted to UTC; timestamps without a timezone are interpreted as UTC. Time bounds have one-second precision.

Results are ordered by event time descending, then event ID descending. Pagination is applied after server and time filters. The response contains `items`, without a total count; advance `offset` until a page contains fewer than `limit` items. Offset pagination does not freeze a snapshot: new events can shift subsequent pages.

- Coverage: **MVP**, `events`. Incident timeline; shifting offset pages explicitly warned.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). Canonical positive numeric server ID
  - `start_time`: string format=date-time (query). Inclusive start time in ISO format
  - `end_time`: string format=date-time (query). Inclusive end time in ISO format
  - `limit?`: integer minimum=1 maximum=5000 default=500 (query). Maximum records per page, integer from 1 to 5000
  - `offset?`: integer minimum=0 default=0 (query). Nonnegative integer number of matching records to skip
- Response 200 application/json: EventListResponse {items}.
- Error statuses documented: 422, 400, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: start_time: Inclusive start time in ISO format end_time: Inclusive end time in ISO format limit: Maximum records per page, integer from 1 to 5000 offset: Nonnegative integer number of matching records to skip

### O13: GET /v1/servers/{id}/events/{event_id}

Retrieve the payload of an event belonging to the requested server. Returns 404 when no payload is available, including when an event summary exists without a detail payload, or when the event belongs to another server.

- Coverage: **MVP**, `events`. Bounded detail retrieval; missing payload may legitimately be 404.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `event_id`: integer minimum=1 maximum=18446744073709551615 (path). Positive UInt64 event ID (1 through 18446744073709551615)
  - `id`: string (path). Canonical positive numeric server ID
- Response 200 application/json: EventDetailRecord {event_id, timestamp, event_body}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O14: GET /v1/servers/{id}/details

Server metadata with every health and security check of the latest report, passing or failing, in display order. Each check carries its result and its catalog texts: title, descriptions, documentation link, severity and group.

Recognized security findings remain available when part of a report cannot be interpreted. Unresolved entries are returned in security_checks_unknown, and security_checks_decode_error describes any interpretation error. An empty security_checks object does not establish that all checks passed: inspect these fields. When no report is available, security_checks is empty and security_checks_decode_error is null.

- Coverage: **MVP**, `server_findings`. All-check snapshots; classify only explicit failures and retain unknown states.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs (current captured contract):
  - `id`: string (path). The ID of the server
- Response 200 application/json: ServerDetailsResponse {created_at, id, server_name, ip_address, releem_score, status, mysql_version, os_version, agent_version, instance_type, memory_limit, agent_up_to_date, health_checks, security_checks_score, security_checks, security_checks_unknown, security_checks_decode_error, current_task, users}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: use the current input descriptions above; no undocumented cursor/total is inferred.

### O15: GET /v1/servers/{id}/health-checks

Every health check of the server's latest report, in display order, with its result, value and catalog texts: title, descriptions, documentation link and group. MySQL/MariaDB and PostgreSQL servers have different checks. A check the catalog has no entry for is listed last with null texts.

- Coverage: **MVP**, `server_findings`. Complete latest health report, not just failures.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs (current captured contract):
  - `id`: string (path). The ID of the server
- Response 200 application/json: PublicHealthChecksResponse {timestamp, checks}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: use the current input descriptions above; no undocumented cursor/total is inferred.

### O16: GET /v1/servers/{id}/security-checks

Every security check of the server's latest security snapshot, in display order, with its result, value and catalog texts: title, descriptions, documentation link, severity and group. A check the catalog has no entry for is listed last with null texts. Check names follow the snapshot's engine: MySQL/MariaDB and PostgreSQL use separate catalogs. Account checks can fail with a null value when the producer did not include account details. Unsupported failure codes or mixed/ambiguous engine fields return `422 invalid_source_data`; they are not returned as an empty successful snapshot.

- Coverage: **MVP**, `server_findings`. Complete latest security report; preserve decode failures.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs (current captured contract):
  - `id`: string (path). The ID of the server
- Response 200 application/json: PublicSecurityChecksResponse {timestamp, security_checks_score, failed_checks, checks}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: use the current input descriptions above; no undocumented cursor/total is inferred.

### O17: GET /v1/servers/{id}/configurations

Every configuration state of one server, applied or not, newest first — the list Releem Platform shows. Each row is one state of a configuration, so a configuration that was applied or rolled back appears once per state; `configuration_id` groups them. All states are returned unless `limit` is given. With `latest=true` only the server's current state is returned — its newest state, the first row of the full list — or an empty list when the server has none.

- Coverage: **MVP**, `configurations`. State/history of one server.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs (current captured contract):
  - `id`: string (path). The ID of the server
  - `limit?`: integer | null (query). Maximum states to return, at least 1; all when omitted
  - `latest?`: boolean; default=False (query). Return only the server's current (newest) configuration state; `limit` is ignored
- Response 200 application/json: PublicConfigurationListResponse {items}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: use the current input descriptions above; no undocumented cursor/total is inferred.

### O18: GET /v1/servers/{id}/configurations/{configuration_status_id}

Retrieve a configuration state with its variables, evaluation metrics, application period and available analysis history. Use the configuration_status_id returned by the configuration list.

- Coverage: **MVP**, `configurations`. State-specific variables/history; not logical configuration ID.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `configuration_status_id`: integer (path). ID of the configuration state, from the list endpoint
  - `id`: string (path). The ID of the server
- Response 200 application/json: PublicConfigurationDetail {configuration_status_id, configuration_id, server_id, timestamp, applied_status, applied_timestamp, required_restart, is_first, variables, source_variables, history, configuration_timestamp, rollback_timestamp, recommendations_changes, variables_orig, configuration_metrics, configuration_metrics_before, configuration_metrics_after, change_metrics, period}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O19: GET /v1/servers/{id}/query-optimizations

List query optimization records for one server, newest first. The `schema_name` filter is applied before `limit`, so a filtered page is never cut short by non-matching records.

- Coverage: **MVP**, `query_evidence`. Read saved optimizations.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
  - `schema_name?`: string | null (query). Filter by schema name
  - `limit?`: integer minimum=1 maximum=5000 default=500 (query). Maximum records to return, 1-5000
- Response 200 application/json: PublicQueryOptimizationListResponse {items}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: limit: Maximum records to return, 1-5000

### O20: POST /v1/servers/{id}/query-optimizations

Save a query from query analytics, with its metrics before optimization, as a query optimization record with `status` `11`.

- Coverage: **Later**, `optimization_submit`. Creates preserved optimization record; mutation even without execution.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: Creates preserved optimization record; mutation even without execution.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: CreateQueryOptimizationRequest {schema_name, query_id, query_text, query_simple_text, before_rid, before_timestamp, before_calls, before_avg_time_ms, before_sum_time_ms, before_sum_time_perc_total}.
    - `schema_name`: string. Database schema name.
    - `query_id`: string. Query fingerprint identifying a normalized query.
    - `query_text`: string. SQL query text.
    - `query_simple_text`: string. Normalized SQL query text with literal values replaced by placeholders.
    - `before_rid`: string. Identifier of the analysis run supplying the before-optimization measurements.
    - `before_timestamp`: integer minimum=0.0. Before-optimization measurement time, as a Unix timestamp in seconds.
    - `before_calls`: integer minimum=0.0. Query execution count before optimization. Must be nonnegative.
    - `before_avg_time_ms`: number minimum=0.0. Average query execution time in milliseconds before optimization. Must be nonnegative.
    - `before_sum_time_ms`: number minimum=0.0. Cumulative query execution time in milliseconds before optimization. Must be nonnegative.
    - `before_sum_time_perc_total`: number minimum=0.0. Percentage of total query execution time before optimization. Must be nonnegative.
- Response 201 application/json: PublicQueryOptimizationWriteResponse {id, server_id, status, timestamp_status_ms, schema_name, query_id, query_text, query_simple_text, before_sum_time_perc_total, before_calls, before_avg_time_ms, before_sum_time_ms, after_sum_time_perc_total, after_calls, after_avg_time_ms, after_sum_time_ms, custom_query, error_message, task_id, explain_task_id}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O21: GET /v1/servers/{id}/query-optimizations/{optimization_id}

Retrieve a query optimization record and all proposals from its linked analysis run, ordered by type, title and SQL. Each proposal includes the analysis time and execution plan when available. Missing execution plans do not exclude proposals.

- Coverage: **MVP**, `query_evidence`. Read proposals and available EXPLAIN only.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `optimization_id`: integer (path). Query optimization record ID
  - `id`: string (path). The ID of the server
- Response 200 application/json: PublicQueryOptimizationDetail {id, server_id, status, timestamp_status_ms, schema_name, query_id, query_text, query_simple_text, before_sum_time_perc_total, before_calls, before_avg_time_ms, before_sum_time_ms, after_sum_time_perc_total, after_calls, after_avg_time_ms, after_sum_time_ms, custom_query, error_message, query_explain, reason, recommendation, before_timestamp, after_timestamp, timestamp_detected_apply, optjob_id, task_id, error_code, error_apply_message, error_apply_code, recommendations}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O22: PATCH /v1/servers/{id}/query-optimizations/{optimization_id}

Set the record's `status` (any code) and/or `task_id`. Only the fields given change.

- Coverage: **Later**, `optimization_workflow`. Changes status/task linkage; requires ownership and state checks.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: Changes status/task linkage; requires ownership and state checks.
- Inputs:
  - `optimization_id`: integer (path). The query optimization record ID
  - `id`: string (path). The ID of the server
  - JSON body: UpdateQueryOptimizationRequest {status, task_id}.
    - `status?`: integer | null. Query optimization status code. Known codes: `0` queued, `1` collecting query plan, `2` analyzing, `3` analysis failed, `4` generated, `5` ready, `6` discovered, `7` application detected and awaiting evaluation, `8` evaluated with improvement, `9` evaluated without improvement, `10` completed, `11` preserved, `100` dismissed. Clients must tolerate additional numeric codes. Updating this field does not change the status timestamp.
    - `task_id?`: integer minimum=1.0 | null. Agent task identifier belonging to this server. At least one of status or task_id is required.
- Response 200 application/json: PublicQueryOptimizationWriteResponse {id, server_id, status, timestamp_status_ms, schema_name, query_id, query_text, query_simple_text, before_sum_time_perc_total, before_calls, before_avg_time_ms, before_sum_time_ms, after_sum_time_perc_total, after_calls, after_avg_time_ms, after_sum_time_ms, custom_query, error_message, task_id, explain_task_id}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O23: GET /v1/servers/{id}/query-analytics

Retrieve query execution statistics for a time window. The window is `[start_date, start_date + period)`, `[start_date, end_date)`, or the last `period` up to now without `start_date`. The start is included and the end is excluded in every mode. An explicit `end_date` requires `start_date` and overrides `period`; it must be later than the start. Bounds use second precision. Percentages are relative to every query that passes the filters, so with `schema_name` they are shares of that schema. The period is a positive integer optionally followed by `m` (minutes), `h` (hours), or `d` (days); a bare integer means days. Other suffixes are rejected.

- Coverage: **MVP**, `query_evidence`. Rank measured expensive queries.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs (current captured contract):
  - `id`: string (path). The ID of the server
  - `period?`: string; default=1 (query). Positive integer with optional m (minutes), h (hours) or d (days). A bare integer means days. Default: 1 day. An explicit end_date overrides this duration; the period must still be valid.
  - `start_date?`: string | null (query). Inclusive start, ISO date or datetime
  - `end_date?`: string | null (query). Exclusive end, ISO date or datetime. Requires start_date, must be later, and overrides period.
  - `timezone?`: string; default=UTC (query). IANA time zone for start_date and end_date without an offset; explicit offsets take precedence
  - `sort_by?`: string; default=sum_time_perc_first (query). `sum_time_perc_first`, `calls`, `avg_time_ms` or `sum_time_perc_total`
  - `order?`: string; default=desc (query). `desc` or `asc`
  - `schema_name?`: string | null (query). Only queries of this schema
  - `query_filter?`: string | null (query). RE2 regular expression matched against the normalized query
  - `limit?`: integer; default=200 (query). Number of top queries, 1-200
- Response 200 application/json: QueryAnalyticsResponse {start_time, end_time, items}.
- Error statuses documented: 422, 400, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: use the current input descriptions above; no undocumented cursor/total is inferred.

### O24: GET /v1/servers/{id}/query-analytics/{schema_name}/{query_id}/recommendations

Retrieve proposals for one query from the latest analysis run containing proposals. Execution plans are included when available. Multiple plans do not duplicate proposals. Returns an empty items array when no proposals exist.

- Coverage: **MVP**, `query_evidence`. Read existing proposals; absent plans remain absent.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `schema_name`: string (path). Database schema name.
  - `query_id`: string (path). Query fingerprint identifying a normalized query.
  - `id`: string (path). The ID of the server
- Response 200 application/json: QueryAnalyticsRecommendationListResponse {items}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O25: GET /v1/servers/{id}/metrics

List available metrics for one server, including the server-scoped item ID needed for `GET /v1/servers/{id}/metrics/byId/{itemid}`.

- Coverage: **MVP**, `metrics`. Discover metric names, IDs, units.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
- Response 200 application/json: ServerMetricsListResponse {metrics}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O26: GET /v1/servers/{id}/metrics/averages

Average, minimum and maximum of every metric of one server over a window, computed from hourly trends in one read. A metric without trend data in the window is listed with null values. `start_time` and `end_time` are required; a reversed range is rejected with 400 `invalid_time_range` and a window longer than 366 days with 400 `time_range_too_wide`. The window includes `start_time` and excludes `end_time`, so adjacent windows do not overlap; request two windows to compare a period with the previous one. Values that are not finite numbers are returned as null.

- Coverage: **MVP**, `metrics`. Two reads compare hourly trend windows.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs (current captured contract):
  - `id`: string (path). The ID of the server
  - `start_time`: string (query). Start of the window (ISO 8601)
  - `end_time`: string (query). End of the window (ISO 8601), exclusive
- Response 200 application/json: ServerMetricAveragesResponse {start_time, end_time, metrics}.
- Error statuses documented: 422, 400, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: use the current input descriptions above; no undocumented cursor/total is inferred.

### O27: GET /v1/servers/{id}/metrics/byName/{metric_name}

Retrieve metric data for one server's metric, looked up by metric name. Unlike the deprecated `GET /v1/metrics/{metric_name}`, `start_time` and `end_time` are required and a reversed range is rejected with 400 `invalid_time_range`. Request parameters are validated before any data is read: `aggregation` must be one of the members below and applies only together with `interval` or `use_trends` (otherwise 400 `aggregation_requires_interval`); `interval` must look like `5m`, `1h` or `1d` (otherwise 400 `invalid_interval`). A window may span at most 31 days of raw samples, or 366 days with `use_trends=true` (otherwise 400 `time_range_too_wide`). Not every metric is aggregated into hourly trends; `use_trends=true` for an item that has no trend rows returns 400 `trends_not_available` rather than an empty series.

- Coverage: **MVP**, `metrics`. Bounded server-scoped series by name.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `metric_name`: string (path). The name of the metric to retrieve
  - `id`: string (path). The ID of the server
  - `start_time`: string format=date-time (query). Start time in ISO format
  - `end_time`: string format=date-time (query). End time in ISO format
  - `aggregation?`: string | null (query). Aggregation function
  - `interval?`: string | null (query). Grouping interval: a positive number followed by m, h or d (e.g. 5m, 1h, 1d)
  - `use_trends?`: boolean default=False (query). Use hourly aggregated metric data instead of raw samples
- Response 200 application/json: MetricDataResponse {data, metric_name, total_points}.
- Error statuses documented: 422, 400, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: start_time: Start time in ISO format end_time: End time in ISO format aggregation: Aggregation function interval: Grouping interval: a positive number followed by m, h or d (e.g. 5m, 1h, 1d) use_trends: Use hourly aggregated metric data instead of raw samples

### O28: GET /v1/servers/{id}/metrics/byId/{itemid}

Retrieve metric data for one server's metric, looked up by its server-scoped item ID (from `GET /v1/servers/{id}/metrics`). `start_time` and `end_time` are required, and a reversed range is rejected with 400 `invalid_time_range`. An `itemid` that belongs to a different server returns 404. Request parameters are validated before any data is read: `aggregation` must be one of the members below and applies only together with `interval` or `use_trends` (otherwise 400 `aggregation_requires_interval`); `interval` must look like `5m`, `1h` or `1d` (otherwise 400 `invalid_interval`). A window may span at most 31 days of raw samples, or 366 days with `use_trends=true` (otherwise 400 `time_range_too_wide`). Not every metric is aggregated into hourly trends; `use_trends=true` for an item that has no trend rows returns 400 `trends_not_available` rather than an empty series.

- Coverage: **MVP**, `metrics`. Bounded series by server-scoped ID.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `itemid`: integer (path). The server-scoped item ID of the metric to retrieve
  - `id`: string (path). The ID of the server
  - `start_time`: string format=date-time (query). Start time in ISO format
  - `end_time`: string format=date-time (query). End time in ISO format
  - `aggregation?`: string | null (query). Aggregation function
  - `interval?`: string | null (query). Grouping interval: a positive number followed by m, h or d (e.g. 5m, 1h, 1d)
  - `use_trends?`: boolean default=False (query). Use hourly aggregated metric data instead of raw samples
- Response 200 application/json: MetricDataResponse {data, metric_name, total_points}.
- Error statuses documented: 422, 400, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: start_time: Start time in ISO format end_time: End time in ISO format aggregation: Aggregation function interval: Grouping interval: a positive number followed by m, h or d (e.g. 5m, 1h, 1d) use_trends: Use hourly aggregated metric data instead of raw samples

### O29: GET /v1/servers/{id}/deadlocks

List deadlocks for one server, newest first, without their dumps. Without parameters, every deadlock up to `limit`. With `start_time`, those from `start_time` to `end_time` (now when omitted). `end_time` without `start_time` is a 400 `invalid_time_range`.

- Coverage: **MVP**, `deadlocks`. Summaries without raw dumps.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
  - `start_time?`: string format=date-time | null (query). Window start in ISO format
  - `end_time?`: string format=date-time | null (query). Window end in ISO format; requires `start_time`
  - `limit?`: integer minimum=1 maximum=5000 default=30 (query). Maximum records to return, 1-5000
- Response 200 application/json: PublicDeadlockSummaryListResponse {items}.
- Error statuses documented: 422, 400, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: start_time: Window start in ISO format end_time: Window end in ISO format; requires `start_time` limit: Maximum records to return, 1-5000

### O30: GET /v1/servers/{id}/deadlocks/{deadlock_id}

Show one deadlock event.

- Coverage: **MVP**, `deadlocks`. Opt-in sanitized detail.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `deadlock_id`: integer (path). Deadlock record ID
  - `id`: string (path). The ID of the server
- Response 200 application/json: DeadlockRecord {id, server_id, timestamp, database, table, raw, deadlock_type, txn1, txn2, max_active_time}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O31: GET /v1/servers/{id}/tasks

Agent tasks for one server, newest first, without their output.

- Coverage: **MVP**, `task_outcomes`. Read summaries, never enqueue tasks.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
  - `status?`: integer | null (query). Filter by task status. Task status code: `0` queued, `1` succeeded, `2` claimed, `3` running, `4` failed, `10` succeeded (query optimization).
  - `type_id?`: integer | null (query). Filter by task type. Task type code: `0` apply configuration manually, `1` generate configuration, `2` update agent, `3` query optimization, `4` apply configuration without restart, `5` apply configuration with restart, `6` apply schema changes, `7` query EXPLAIN, `8` roll back configuration.
  - `limit?`: integer minimum=1 maximum=5000 default=30 (query). Maximum records to return, 1-5000
- Response 200 application/json: PublicTaskListResponse {items}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: limit: Maximum records to return, 1-5000

### O32: POST /v1/servers/{id}/tasks

Queue an agent task for the server. The returned task has status `0` (queued).

- Coverage: **Later**, `agent_tasks`. Queues real database/agent actions; high risk.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: Queues real database/agent actions; high risk.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: CreateTaskRequest {tasks_type_id, details}.
    - `tasks_type_id`: integer minimum=0.0. Task type code: `0` apply configuration manually, `1` generate configuration, `2` update agent, `3` query optimization, `4` apply configuration without restart, `5` apply configuration with restart, `6` apply schema changes, `7` query EXPLAIN, `8` roll back configuration. The API accepts any nonnegative integer; execution support depends on the agent.
    - `details?`: JSON. Task parameters as any JSON value; null when omitted.
- Response 201 application/json: PublicTask {id, server_id, type_id, type, status, status_label, exit_code, status_time, details}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O33: GET /v1/servers/{id}/tasks/{task_id}

Retrieve one task. Completed tasks include agent output and error text when a final report is available.

- Coverage: **MVP**, `task_outcomes`. Read final output/error when available.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `task_id`: integer (path). Task ID
  - `id`: string (path). The ID of the server
- Response 200 application/json: PublicTaskDetail {id, server_id, type_id, type, status, status_label, exit_code, status_time, details, output, error, report_time}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O34: GET /v1/servers/{id}/processlist

`SHOW PROCESSLIST` captures for one server, newest first. Without parameters, only the latest capture. With `start_time`, the captures from `start_time` to `end_time` (now when omitted), capped by `limit`. `end_time` without `start_time` is a 400 `invalid_time_range`.

- Coverage: **MVP**, `captured_sessions`. Historical captures; no live-session promise.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
  - `start_time?`: string format=date-time | null (query). Window start in ISO format
  - `end_time?`: string format=date-time | null (query). Window end in ISO format; requires `start_time`
  - `limit?`: integer minimum=1 maximum=5000 default=30 (query). Maximum captures in a window, 1-5000
- Response 200 application/json: PublicProcesslistCaptureListResponse {items}.
- Error statuses documented: 422, 400, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: start_time: Window start in ISO format end_time: Window end in ISO format; requires `start_time` limit: Maximum captures in a window, 1-5000

### O35: GET /v1/servers/{id}/schema-checks

Schema checks from the most recent completed run for one server. A null `timestamp` means no run has completed schema checks yet. A non-null `timestamp` with an empty `items` list means the filters matched nothing in that run — which equals "the run found nothing" only when no filters were applied.

- Coverage: **MVP**, `server_findings`. Completed schema-check run, not full database schema.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the server
  - `type?`: string | null (query). Filter by schema check type. Matched on the canonical form, so `unused_index` and the stored `UNUSED_INDEX_NEW` select the same checks. The endpoint returns these check types only: `missing_primary_key`, `unused_index`, `duplicate_index`, `auto_increment`, `collation`, `character_set`, `table_engine` and `table_fragmentation`; any other value matches nothing
  - `schema_name?`: string | null (query). Filter by schema name
- Response 200 application/json: PublicSchemaCheckListResponse {server_id, timestamp, items}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O36: POST /v1/servers/{id}/query-optimizations/custom

Queue a user-supplied query for optimization: `status` `0`, `custom_query` `true`, no `query_id`. The EXPLAIN task the agent needs (task type `7`) is queued in the same operation and returned as `explain_task_id`; no separate task request is required.

- Coverage: **Later**, `optimization_submit`. Creates record AND task type 7 EXPLAIN; never passive.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: Creates record AND task type 7 EXPLAIN; never passive.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: CreateCustomQueryOptimizationRequest {schema_name, query_text, query_simple_text}.
    - `schema_name`: string. Database schema name.
    - `query_text`: string. SQL query text.
    - `query_simple_text`: string. Normalized SQL query text with literal values replaced by placeholders.
- Response 201 application/json: PublicQueryOptimizationWriteResponse {id, server_id, status, timestamp_status_ms, schema_name, query_id, query_text, query_simple_text, before_sum_time_perc_total, before_calls, before_avg_time_ms, before_sum_time_ms, after_sum_time_perc_total, after_calls, after_avg_time_ms, after_sum_time_ms, custom_query, error_message, task_id, explain_task_id}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O37: PUT /v1/servers/{id}/memory-limit

Set the server memory limit in bytes.

- Coverage: **Later**, `configuration_changes`. Changes stored memory limit; downstream effects need confirmation.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: Changes stored memory limit; downstream effects need confirmation.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: UpdateMemoryLimitRequest {memory_limit}.
    - `memory_limit`: integer minimum=0.0. Memory limit in bytes, as a nonnegative integer.
- Response 200 application/json: MemoryLimitResponse {server_id, memory_limit}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O38: PUT /v1/servers/{id}/mysql-config

Replace the server's manual MySQL configuration overrides with the supplied JSON object.

- Coverage: **Later**, `configuration_changes`. Replaces manual override object, not a partial merge.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S2. Minimize fields before model output; never emit credentials.
- Actual effects: Replaces manual override object, not a partial merge.
- Inputs:
  - `id`: string (path). The ID of the server
  - JSON body: UpdateMysqlConfigRequest {mysql_config}.
    - `mysql_config`: object. MySQL configuration variables as a JSON object. Replaces the previous configuration override.
- Response 200 application/json: MysqlConfigResponse {server_id, mysql_config}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O39: GET /v1/metrics

**Deprecated.** Use `GET /v1/servers/{id}/metrics` instead.

Retrieve a list of all available metrics for the authenticated user's servers.

- Coverage: **Excluded**, `legacy_metrics`. Deprecated; use operation 25.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - None.
- Response 200 application/json: MetricsListResponse {metrics}.
- Error statuses documented: 422, 401, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O40: GET /v1/metrics/{metric_name}

**Deprecated.** Use `GET /v1/servers/{id}/metrics/byName/{metric_name}` instead.
Unlike this endpoint, the replacement requires `start_time` and `end_time`
and rejects a reversed range with 400 `invalid_time_range`.

Retrieve metric data for a specific metric with optional filtering and aggregation.

- Coverage: **Excluded**, `legacy_metrics`. Deprecated; use operations 27/28.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S1. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `metric_name`: string (path). The name of the metric to retrieve
  - `server_id`: string (query). Filter by specific server ID
  - `start_time`: string format=date-time (query). Start time in ISO format
  - `end_time`: string format=date-time (query). End time in ISO format
  - `aggregation?`: string | null (query). Aggregation function
  - `interval?`: string | null (query). Grouping interval: a positive number followed by m, h or d (e.g. 5m, 1h, 1d)
  - `use_trends?`: boolean default=False (query). Use hourly aggregated metric data
- Response 200 application/json: MetricDataResponse {data, metric_name, total_points}.
- Error statuses documented: 422, 401, 404, 400, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: start_time: Start time in ISO format end_time: End time in ISO format aggregation: Aggregation function interval: Grouping interval: a positive number followed by m, h or d (e.g. 5m, 1h, 1d) use_trends: Use hourly aggregated metric data

### O41: POST /v1/customers

Create a new customer. Partner only.

- Coverage: **Excluded**, `customer_administration`. Partner-only creation; outside diagnostics.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: Partner only, explicitly documented; omitted from diagnostic product.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: Partner-only creation; outside diagnostics.
- Inputs:
  - JSON body: CreateCustomerRequest {email, name}.
    - `email`: string. Email address.
    - `name`: string. Customer name.
- Response 201 application/json: CustomerResponse {id, email, name, created_at, updated_at, api_key, subscription}.
- Error statuses documented: 422, 401, 403, 409, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O42: GET /v1/customers

List customers. Partners see all customers, customers see only their own.

- Coverage: **Excluded**, `customer_administration`. Sensitive account inventory/API keys; not tenant identity proof.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: Partners see all customers; customers only their own (documented). Excluded.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `filter?`: list[string] | null (query). Filter customers by email. Repeat the query parameter to pass multiple email values.
- Response 200 application/json: list[CustomerResponse {id, email, name, created_at, updated_at, api_key, subscription}].
- Error statuses documented: 422, 401, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O43: GET /v1/customers/{id}

Retrieve details of a specific customer.

- Coverage: **Excluded**, `customer_administration`. Account/credential disclosure risk; no diagnostic need.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: No application mutation documented.
- Inputs:
  - `id`: string (path). The ID of the customer
- Response 200 application/json: CustomerResponse {id, email, name, created_at, updated_at, api_key, subscription}.
- Error statuses documented: 422, 401, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O44: PATCH /v1/customers/{id}

Update customer details.

- Coverage: **Excluded**, `customer_administration`. Account/subscription modification; RBAC incomplete.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: UNCONFIRMED endpoint RBAC; enforce tenant and server access.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: Account/subscription modification; RBAC incomplete.
- Inputs:
  - `id`: string (path). The ID of the customer
  - JSON body: UpdateCustomerRequest {email, name, subscription}.
    - `email?`: string | null. Email address.
    - `name?`: string | null. Updated customer name.
    - `subscription?`: Subscription | null. Subscription information to update.
- Response 200 application/json: CustomerResponse {id, email, name, created_at, updated_at, api_key, subscription}.
- Error statuses documented: 422, 401, 403, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O45: DELETE /v1/customers/{id}

Delete a customer. Partner only.

- Coverage: **Excluded**, `customer_administration`. Partner-only destructive administration.
- Authentication: customer apiToken; internal Bubble alternative deliberately unsupported.
- Role constraints: Partner only, explicitly documented; omitted from diagnostic product.
- Sensitivity: S3. Minimize fields before model output; never emit credentials.
- Actual effects: Partner-only destructive administration.
- Inputs:
  - `id`: string (path). The ID of the customer
- Response 204: no body.
- Error statuses documented: 422, 401, 403, 404, 500. Do not convert missing/invalid source data into success.
- Pagination/time rules: No pagination/time controls documented. Bound response locally; do not invent an upstream cursor.

### O46: GET /v1/checks

Title, texts, documentation link, severity and group of every health and security check, ordered by type, DBMS family and display order. The texts describe the check itself and are the same for every user and server. A server's results already include them: see `GET /v1/servers/{id}/health-checks` and `GET /v1/servers/{id}/security-checks`, whose check names match `key`.

The same `key` can appear once per DBMS family with different texts, so match on `type`, `dbms` and `key` together.

- Coverage: **Later**, `check_reference`. No current registry entry, tool or live resource.
- Authentication: customer apiToken; internal Bubble alternative unsupported.
- Role constraints: endpoint RBAC UNCONFIRMED; never use catalog identity as authorization.
- Sensitivity: S1 static check descriptions; arbitrary returned text remains untrusted.
- Actual effects: no application mutation documented.
- Inputs: optional `type` health/security and `dbms` mysql/postgresql; mysql includes MariaDB.
- Response200: CheckCatalogResponse, items of CheckCatalogItem; identity is(type,dbms,key).
- Pagination/time rules: no pagination/limit documented; preserve source order if later exposed.
- Failure behavior: retain auth/validation/upstream errors; never substitute an empty healthy report.
- Raw documentation URLs must not be fetched or emitted automatically.
