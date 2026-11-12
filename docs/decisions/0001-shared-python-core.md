# Decision 0001: shared Python diagnostic core

Status: selected for Phase 0 compatibility evaluation, **not a production release
approval**. Date: 2026-11-10.

Use Python 3.12 and official MCP SDK 2.3.0 for the first implementation candidate.
Keep one diagnostic API client/core and separate local and hosted identity and
transport composition. Do not restore the former dbharness executor or its
upstream-key-as-MCP-bearer behavior.

The reference adapter is Python, the repository/team context is Python, and the
candidate supports both required transports without a second runtime. TypeScript
v2 remains a credible alternative if measured integration constraints change;
there is no demonstrated need to maintain both implementations.

The candidate dependency set resolves in a pinned Python container. SDK
protocol tests provide evidence for selecting it; exact client application and
hosted OAuth onboarding are still separate release gates. Supporting details:
[plan](../plans/2026-11-10-mcp-releem.md),
[client compatibility](../clients/compatibility.md) and
[synthetic experiment](../phase0-status.md).

Consequences: use the official SDK's existing current/legacy handling. Prefer
stateless HTTP for bounded read-only calls. Keep authentication request-scoped
and validate it independently of transport/session state. Do not build a custom
legacy adapter or deploy a stateful multiworker service without evidence that
those choices are necessary and tested.

Cloud-first remains the planning assumption. The user confirmed
`https://api2.dev.releem.com` as the API base URL on 2026-11-10; use it as the
default with an administrator-controlled override. This supersedes the earlier
documentation-only restriction for that origin. Self-hosted API parity,
least-privilege credentials and trusted hosted identity-to-tenant credential
binding remain UNCONFIRMED. Deployed behavior still requires separate validation.
