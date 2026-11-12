# Client and protocol compatibility — Phase 0

Research date: **2026-11-10T17:31:56Z**. Separate protocol interoperability from
application onboarding. Do not advertise universal client compatibility.

| Component | Observed version | Evidence / status |
|---|---|---|
| Python in pinned container | 3.12.16 | `python --version` inside digest-pinned image |
| Official Python MCP SDK | 2.3.0 | Hash-locked container install; synthetic tests |
| Modern protocol | 2026-07-28 | SDK client/server typed read calls over stdio and HTTP |
| Legacy protocol | 2025-11-25 | SDK client forced legacy mode over both transports |
| Claude Code application | 2.1.70 | Local `claude --version`; actual tool onboarding and OAuth NOT TESTED |
| Cursor application | 3.25.6 | Local application bundle version; actual tool onboarding and OAuth NOT TESTED |
| Codex / other applications | UNCONFIRMED | Outside this initial client check |

The [historical experiment](../phase0-status.md) built a
synthetic tool, validates its argument/structured-result schemas and read-only
annotations, and checks that a guessed mutation tool is rejected. No API
adapter or hosted authorization is involved. This does not prove read-only
upstream enforcement for the future product.

The SDK's [documented legacy behavior](https://py.sdk.modelcontextprotocol.io/run/legacy-clients/)
and inspected **v2.3.0 release source** establish that one HTTP app routes both
protocol eras. A separate custom compatibility adapter should not be planned
unless a concrete client test shows it is necessary. Configure
`stateless_http=True` for this read-only experiment: legacy reads work without
persistent sessions. Default stateful legacy operation creates an in-process
session and requires affinity if multiple processes serve one endpoint. An
event store provides resumability, not a shared session registry. Any future
stateful compatibility session must still be bound to and reauthorized against
the authenticated principal; it is never authentication.

Application release gates remain open:

1. Onboard each exact client build to a synthetic adapter without altering the
   user's existing MCP configuration. Confirm tool discovery, typed calls,
   structured results, errors, cancellation and process shutdown.
2. In an approved hosted test environment, verify metadata discovery, browser
   authorization/PKCE, callback registration, audience, expiry and revocation.
3. Record actual negotiated protocol and transport, current/stale client
   behavior and any legacy-affinity limitations. SDK-to-SDK success cannot
   replace this receipt.

No model calls, client login flow, OAuth tokens or real Releem credentials were
used for these protocol experiments. Locally reading an application's version
is not an onboarding test.

Subsequent first-slice implementation adds product-level SDK tests for discovery, structured results and rejected writes under modern/legacy stdio and HTTP. HTTP remains a synthetic loopback test surface; the product CLI only serves stdio; explicit `--env-file` supports the user's `RELEEM_SECRET_KEY` credential name. Exact client application/OAuth onboarding remains unverified. See [implementation status](../implementation-status.md).

2026-11-11 continuation: product transport fixtures also verify prompt discovery,
static prompt retrieval and `releem://reference` resource reads over modern and
legacy stdio and synthetic loopback HTTP. Separate offline tests cover all four
prompts, strict arguments and sanitized dispatch errors. This establishes SDK
protocol behavior, not prompt/resource UI support in the above applications.

2026-11-11T05:11Z continuation: Claude Code 2.1.70 isolated project registration
and `mcp list` connection health passed against the local Docker stdio runtime
with a synthetic key and networking disabled. This supersedes the table only for
registration/handshake; interactive tool/prompt/resource UI and OAuth remain
unverified. Cursor bundle remains 3.25.6; no application onboarding was performed.
See [exact setup, primary sources and remaining gates](local-setup.md).

## Authenticated hosted implementation — 2026-11-11

Supersedes the earlier stdio-only product status: the CLI now supports authenticated
stateless Streamable HTTP. Both SDK protocol modes (legacy and 2026-07-28) pass
handshake, discovery, structured reads, prompts/reference and write denial using
API-key headers over synthetic ASGI HTTP. Concurrent customer/revocation and
boundary tests use the same shared endpoint. These are SDK tests, not interactive
Claude/Cursor application or deployed TLS receipts. Browser OAuth is intentionally
deferred; the existing API key is a custom configured-header credential. The
earlier OAuth application gate applies only if that future capability is added.
See [hosted setup](../hosted-pilot.md).

2026-11-12 cleanup: retired the separate Phase 0 experiment and duplicate HTTP
SDK handshake cases. `tests/test_transports.py` keeps modern/legacy stdio checks
and runs the authenticated TCP journey from `tools/release/local_journey.py`.
Direct ASGI tests retain authentication, preauth limits and tenant boundaries.
