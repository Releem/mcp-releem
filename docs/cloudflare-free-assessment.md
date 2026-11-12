# Cloudflare Free hosting assessment

Checked 2026-11-11T09:26:58Z against current source and official documentation.
No deployment, package installation, customer API call or runtime change performed.
No Worker bundle was built; Worker compatibility/performance remains UNCONFIRMED.

## Verdict

The current hosted implementation is not deployable unchanged to Workers Free.
It is a conventional CPython Docker service with a Uvicorn listener. Cloudflare
Containers is the closest runtime match but has no Free allocation; its published
pricing requires the $5/month Workers Paid plan, with separately metered usage.
That is a minimum plan cost, not an all-inclusive monthly quote.
[Containers pricing](https://developers.cloudflare.com/containers/platform/pricing/),
updated 2026-10-05.

Cloudflare Python Workers run through Pyodide/WebAssembly and a Worker entrypoint.
Python ASGI is supported through Cloudflare's adapter, so reusing our Python core
is plausible and should be tried before considering a TypeScript rewrite. This
does not establish compatibility of the pinned MCP SDK or its lifespan handling.
[Runtime](https://developers.cloudflare.com/workers/languages/python/how-python-workers-work/),
updated 2026-07-09;
[ASGI support](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/),
updated 2026-08-28.

## Free limits versus this implementation

| Limit | Workers Free documentation | Assessment |
| --- | --- | --- |
| Incoming requests | 100,000/day, resets UTC midnight | Potentially adequate for a small pilot; count HTTP handshake, discovery, reference, tool and health requests, not only tool invocations. No traffic forecast exists. |
| CPU | 10ms/request; network waiting excluded | Main performance risk: schema generation, validation, JSON parsing/redaction and client/TLS initialization are unmeasured in Workers. Existing30s deadline is wall time, not a CPU allowance. |
| Memory | 128MB/isolate, shared by concurrent requests | Current upstream bodies can reach5MiB before decoded model/object overhead. Multiple requests can multiply this. Output truncation does not bound intermediate heap. |
| Subrequests/connections | 50 subrequests/request;6 simultaneous outgoing connections | Bounded reads are promising; inventory authentication adds one read on every protected request. Measure all tool modes and redirects/platform accounting. |
| Startup/package | 1s startup;64MiB Worker size | Neither is measured for the pinned dependency closure. Docker image size is not Worker bundle size. |
| HTTP wall time | No fixed HTTP duration while client connected | Our30s request deadline can be retained; cancellation/disconnect behavior must be tested in the actual runtime. |

Source: [Workers limits](https://developers.cloudflare.com/workers/platform/limits/),
updated 2026-10-29. These are published plan limits, not measured product capacity.

## Concrete adaptation work

1. Add a Worker/ASGI entrypoint without Uvicorn, sockets or Docker startup. Verify
   the MCP SDK lifespan/task handling on Cloudflare's ASGI implementation.
2. Verify exact package availability for mcp2.3.0, httpx2 2.16.0, Pydantic2.14.3
   and native transitive dependencies. Replace/adapt upstream I/O to supported
   Worker fetch transport; retain fixed origins, key isolation, body bounds,
   redirect refusal, timeouts and cancellation. Do not presume standard CPython
   TLS/proxy/CA configuration maps directly to Workers. Local stdio can retain it.
3. Replace reliance on in-memory quotas for globally effective limits. Current
   random-salted fingerprints, counters and semaphores are process-local and
   reset with each isolate; use an explicitly chosen platform/shared mechanism.
   Never persist raw customer keys to achieve quota coordination. Select its own
   pricing/limits separately; no additional paid dependency is assumed here.
4. Re-run both protocol/client modes and concurrent customer/revocation/redaction
   tests through the Worker boundary. Benchmark startup, package size, CPU and
   peak memory with representative maximum synthetic fixtures under concurrency.
   Narrow upstream budgets/windows where needed; do not claim safety from small
   average responses. Hosted configuration and CI need Worker-specific checks.

Python Workers support pure Python, PyEmscripten wheels and packages provided by
Pyodide; ordinary native Linux wheels are not proof of Worker support.
[Package requirements](https://developers.cloudflare.com/workers/languages/python/packages/),
updated 2026-09-18. Source inspected: `Dockerfile`, `pyproject.toml`,
`src/mcp_releem/cli.py`, `api/client.py`, `hosted/app.py`, `hosted/limits.py`.

Our stateless MCP profile and request-scoped credentials are reusable design
choices; Cloudflare documents stateless Streamable HTTP. No MCP session registry
or per-customer deployment is needed merely to host this read-only adapter.
[MCP transport](https://developers.cloudflare.com/agents/model-context-protocol/protocol/transport/).

## Smallest release path

If all application compute must be on Cloudflare Free, first do a bounded Python
Worker compatibility/performance experiment. A successful import is insufficient:
all ten tool contracts, authorization and resource budgets must pass. Do not
rewrite the diagnostics in TypeScript without first testing Python reuse. A native
TypeScript Worker remains an alternative if Python dependency or CPU constraints
block the pilot; that has substantial parity/maintenance implications.

If an existing Releem server is available, run the current single hosted container
there behind Cloudflare Tunnel/proxy. This preserves the Python implementation;
Cloudflare is the public edge, and compute still runs on our server. Verify public
Host/header forwarding, no challenge/login interruption of MCP, no caching of MCP
responses and no logged credentials. This is not entirely Cloudflare-hosted or a
claim of free origin compute.
[Tunnel architecture](https://developers.cloudflare.com/tunnel/).

A Cloudflare Containers deployment is another option if paid hosting is accepted;
CPU architecture, routing and lifecycle still need verification. No option was
deployed or selected by this assessment. Free Cloudflare-only compatibility is a
new release gate; the existing Docker verification cannot satisfy it.
