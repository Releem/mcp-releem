# Test the private MVP locally with synthetic data

No real Releem key or database is needed. The synthetic fixture injects responses
into the installed production diagnostic core; it cannot call the Releem API.
Use it only on host loopback. It is test tooling, not the production entrypoint.

The current session's demo is `http://127.0.0.1:55670/mcp`, container
`mcp-releem-local-demo`, using the reviewed patched image. Its temporary client
configuration is `/tmp/mcp-releem-client-cdfjl3b4/.mcp.json`. This URL/config is
session-specific and will disappear when the demo is stopped.

For Claude Code, use your normal authenticated CLI with that explicit config:

```bash
claude --mcp-config /tmp/mcp-releem-client-cdfjl3b4/.mcp.json --strict-mcp-config
```

No existing user MCP configuration was changed. The isolated registration profile
used during automated checks has no model login. Authenticate through the client's
normal login UI if necessary; never paste a key into chat. Model-directed use is
not yet a recorded automated success. All evidence served here is synthetic.

For a client supporting HTTP headers, the demo configuration is:

```json
{
  "mcpServers": {
    "releem-synthetic": {
      "type": "http",
      "url": "http://127.0.0.1:55670/mcp",
      "headers": {
        "Host": "mcp.example.invalid",
        "Authorization": "Bearer synthetic-key-A"
      }
    }
  }
}
```

These are intentionally public synthetic keys. KeyA sees server101/recommendation601;
`synthetic-key-B` sees server202/recommendation602. Do not use a customer key here.

Try: “Discover the servers I can access. Investigate the findings for the returned
server, then explain its recommendation. Distinguish measured evidence from
hypotheses and point out missing evidence.” Expect missing health snapshot,
a synthetic security finding and a recommendation marked done that does not prove
any applied change. Four prompts and releem://reference are static guidance.

Then ask for the other customer's server: no foreign data should be returned.
Automatic tests cover both accounts, invalid/simulated-revoked keys, unavailable
upstream and both supported SDK protocol modes over real loopback TCP. No real
account revocation has been performed. Cursor UI is not certified by these tests.

Stop/remove only this demo when finished:

```bash
docker rm -f mcp-releem-local-demo
```

For reproducible checks run `bash scripts/check-release.sh`; it builds locked images,
executes offline synthetic tests and installed TCP journeys, tests isolated Compose
start/restart/recovery, and verifies the local artifact checksums/source fingerprint.
Builds can fetch public dependencies/images. No customer API access is required.
Security advisory checks are a separate network-enabled gate; the hardened runtime security gate now passes. See [review](releases/security-review-2026-11-11.md) and
[verification evidence](releases/evidence/2026-11-11-local-validation.json).

2026-11-11: the running demo was upgraded in place to the audited Alpine runtime
at the same port/config; isolated Claude HTTP health was rechecked. Only synthetic
records are served. See [runtime security receipt](releases/evidence/2026-11-11-runtime-security.json).
