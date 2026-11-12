# Local client setup and verification

Checked **2026-11-11**. This release serves local stdio and authenticated hosted HTTP. No package or image is
published. Build the runtime image or install the reviewed checkout as described
in the [README](../../README.md). Replace every placeholder below; provision the
API credential outside source control and chat. The token-file path is not a token.

## Codex

Follow the [exact Compose and Codex commands](../../README.md#local-http-setup-with-codex-and-the-real-api).
The selected setup stores the key in the user's private `~/.codex/config.toml`
as `http_headers.Authorization = "Bearer <YOUR_RELEEM_API_KEY>"`, alongside a
local-only Host header. Replace the placeholder locally, restrict file access
and keep it out of Git. No environment-variable export or key prompt is needed.
Remove an old `bearer_token_env_var` for this connection when switching to static
headers, and start a new Codex session after changing credentials.

The HTTP container has no global customer credential or customer `.env` mount.
Each authenticated request supplies its own key. `url` points to the MCP server;
`RELEEM_API_BASE_URL` is a separate administrator setting for the upstream API.
Codex does not automatically load the checkout's `.env` or interpolate custom
`RELEEM_MCP_URL`/`RELEEM_MCP_CLIENT_KEY` fields in HTTP connection TOML.

An isolated CLI 0.167.0 configuration check validates the documented URL and
static Host/Authorization headers using placeholders only. This is not a real-key
handshake or model-directed client test. Static headers are supported by the
[official OpenAI MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
The synthetic demo is separate and does not call the real API.

## Claude Code

Installed CLI **2.1.70** was checked with `--version` and MCP command help.
Claude accepts an `mcpServers` configuration block; `mcp add-json` takes the inner
server object, not that wrapper. Its CLI also supports `--mcp-config` and
`--strict-mcp-config`. See the [official MCP setup documentation](https://code.claude.com/docs/en/mcp).

Package configuration:

```json
{
  "mcpServers": {
    "releem": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/ABSOLUTE/PATH/TO/CHECKOUT", "run", "--locked", "mcp-releem"],
      "env": {"RELEEM_API_TOKEN_FILE": "/ABSOLUTE/PATH/TO/TOKEN_FILE"}
    }
  }
}
```

Alternatively run the reviewed Docker image. Substitute an immutable local
image ID or registry digest after building; the token file must be readable by
runtime UID 65532 under your credential-management policy. Do not make it broadly
readable to solve a permission error. Package mode can use the current user's
restricted token file instead.

```json
{
  "mcpServers": {
    "releem": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--read-only", "--tmpfs", "/tmp", "--cap-drop=ALL",
        "-e", "RELEEM_API_TOKEN_FILE=/run/secrets/releem",
        "--mount", "type=bind,src=/ABSOLUTE/PATH/TO/TOKEN_FILE,dst=/run/secrets/releem,readonly",
        "<PINNED_IMAGE_REFERENCE>"
      ]
    }
  }
}
```

Use stdin (`-i`) without a TTY; no published port is needed. Ensure `docker` or
`uv` is on the client's PATH, or use its absolute executable path. Keep exactly
one API credential source in the inherited/client environment. An optional
explicit `--env-file /ABSOLUTE/PATH/TO/ENV_FILE` belongs in the package command's
args; it does not run a shell or interpolate variables.

## Cursor

Installed application bundle **3.25.6** was read from its plist; the Cursor CLI
was not on PATH. The same stdio object can be placed under `mcpServers` in the
project's `.cursor/mcp.json` or the user's `~/.cursor/mcp.json`. Current official
docs specify `type`, `command`, optional `args`/`env`, and document tools,
prompts/resources and several transports. Hosted custom-header HTTP is also implemented; exact Cursor onboarding remains unverified.
These are documentation-level capabilities, not an installed-app test. See
[Cursor's MCP documentation](https://cursor.com/docs/mcp).

No Cursor configuration or running application was changed during verification.
Use the explicit token-file example above; GUI environment inheritance may differ
from your shell. Keep credentials out of a shared project JSON file.

## Verification receipt and remaining gates

Claude registration and connection health passed in a new temporary project with
a dedicated `CLAUDE_CONFIG_DIR`. That setting isolates Claude configuration as
documented in its [environment reference](https://code.claude.com/docs/en/env-vars).
The test registered a project-scoped stdio entry through `claude mcp add-json`,
verified the saved JSON, and ran `claude mcp list`. It reported connected to the
local Docker runtime. The server used `--network none`, a synthetic credential
and no real API access. Normal user/project client configuration was not edited;
no login, OAuth or model call was performed.

This verifies CLI registration and handshake health, not interactive model tool
selection, prompt/resource UI, credential-file permissions or every client
release. Product SDK tests independently cover discovery/calls/structured errors,
four prompts and the static reference over modern/legacy stdio and synthetic HTTP.

Before claiming full application onboarding, verify in an isolated workspace:

1. Exactly ten read tools, four prompts and `releem://reference` appear.
2. A synthetic read returns structured evidence; invalid inputs and guessed
   mutation names fail without exposing the synthetic key.
3. Prompt/resource UI, cancellation and clean process shutdown work.
4. Configure a separately approved test account/token-file path and verify the
   client's access/permissions without posting payloads into shared logs.

For troubleshooting, run the server's redacted `--check` using the same command
environment. Resolve missing executables, wrong token-file permissions, multiple
credential sources and CA/proxy configuration before testing API access. No
production hosted URL has been provisioned; the loopback demo below is synthetic. Removing the client
entry stops registration; revoke upstream credentials separately if required.

2026-11-11 local hosted continuation: Claude Code2.1.70 configured-header HTTP
registration/connection health passed against loopback synthetic hosted API
accounts, in a dedicated temporary CLAUDE_CONFIG_DIR/workspace. This is not a
model-driven diagnostic receipt; that isolated profile has no model login. Full
synthetic TCP SDK workflows pass both protocol modes. See [review](../releases/security-review-2026-11-11.md).

## Updated query inputs

`query_evidence` advertises `period` (for example `"10m"`, `"2h"`, `"7d"`;
default `"1d"`) and offset-aware whole-second `start_date`/`end_date`. End requires
start and overrides a valid period. Local period/window bounds are90 days.
Existing `period_days` calls remain supported as a deprecated alias; do not
combine selectors. Refresh tool discovery after upgrading an existing client.

```json
{"server_id":"101","period":"10m","limit":10}
{"server_id":"101","start_date":"2026-11-11T10:00:00Z","end_date":"2026-11-11T10:10:00Z"}
```

These calls illustrate the typed contract using placeholder IDs; client health
evidence does not establish model-directed workflows or actual hosted TLS.
