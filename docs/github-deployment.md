# Deploy mcp.releem.com through GitHub

Target: `ubuntu@40.160.8.37` with passwordless sudo, Ubuntu26.04 AMD64.
Root SSH is disabled by this server. The application remains one nonroot container
on `127.0.0.1:8000`. Root `compose.yaml` defines both `mcp` and `cloudflared`
in the same `mcp-releem` project; the connector uses the private Docker network.
The optional `tunnel` profile is enabled once its protected token is installed.

The managed host has Docker/Compose, the combined stack, setup helpers and the
`/opt/mcp-releem/stack` wrapper installed. On 2026-11-12 the owner reported public
HTTPS health200 with `{"status":"alive"}` and unauthenticated MCP401. This
supersedes the earlier token/DNS-pending status. The owner configured a Cloudflare
hostname at `mcp.releem.net` and custom hostname `mcp.releem.com`, while retaining
AWS DNS for `releem.com`; exact dashboard settings have not been independently
inspected. Authenticated HTTPS client, reboot recovery and GitHub publication/
environment-secret setup remain unverified.

Native AMD64 verification before the later repository cleanup passed351 tests
and synthetic two-service recovery checks; see the [unified receipt](releases/evidence/2026-11-12-unified-stack.json).
The subsequent cleanup passed347 tests locally. These are separate receipts from
the owner's public HTTPS checks.

## One-time Cloudflare setup

Skip this section if the existing tunnel and public checks already pass.

1. Open the Cloudflare account managing the tunnel. Go to **Networking →
   Tunnels**, create a **cloudflared** tunnel named `releem-mcp-production`.
   Some accounts show the same flow under Zero Trust → Networks → Connectors.
2. Copy only the tunnel token from its connector installation command. Do not run
   the token-bearing command, paste it into chat, or store it in GitHub.
3. On the server, run the staged setup helper from an interactive terminal:

   ```bash
   ssh -t ubuntu@40.160.8.37 \
     'sudo bash /opt/mcp-releem/setup/start-tunnel.sh --dry-run'
   ssh -t ubuntu@40.160.8.37 \
     'sudo bash /opt/mcp-releem/setup/start-tunnel.sh --apply'
   ```

   Enter the token at the hidden prompt. The helper stores it only in
   `/opt/mcp-releem/secrets/tunnel-token`, owned by container UID65532 with0400
   permissions under a root-only directory. The container receives a read-only
   file mount, not a token command argument or environment variable.
4. In the tunnel's **Routes / Published application routes**, add:

   | Setting | Value |
   | --- | --- |
   | Hostname | `mcp.releem.com` |
   | Service type | HTTP |
   | Service URL | `mcp:8000` |
   | HTTP Host Header | `mcp.releem.com` |

   Leave the path unset so both `/mcp` and `/healthz` reach the app. The connector
   reaches `mcp` through Docker service DNS. Inside the connector,127.0.0.1 refers
   to the connector itself: use `mcp:8000`, superseding the old host-network route.
   Keep a final404 catch-all ingress. If `releem.com` uses Cloudflare DNS, let
   Cloudflare create the tunnel CNAME; inspect any existing record first. For the
   AWS DNS/custom-hostname arrangement, use the settings below. Do not add an A
   record pointing to40.160.8.37 or open public port8000.
5. Confirm the connector is **Healthy**. Ensure `/mcp` has no caching, HTML/browser
   challenges or interactive Access login; preserve Authorization and streaming.
   Scope any exception to this hostname/path, not the whole zone. Existing Releem
   API-key authentication remains enforced by the application.
6. Verify public liveness and authentication denial:

   ```bash
   curl --fail --max-time 15 https://mcp.releem.com/healthz
   curl --max-time 15 -o /dev/null -w '%{http_code}\n' \
     -X POST -H 'Content-Type: application/json' --data '{}' \
     https://mcp.releem.com/mcp
   # Expected: health200, MCP401.
   ```

Then run an actual MCP client against `https://mcp.releem.com/mcp` with its existing
Releem API key, following [client setup](clients/local-setup.md). Liveness/401 alone does
not verify authenticated upstream access, revocation, isolation or streaming.

Official sources checked2026-11-12: [named tunnels](https://developers.cloudflare.com/tunnel/get-started/),
[token handling](https://developers.cloudflare.com/tunnel/reference/tunnel-tokens/),
[origin parameters](https://developers.cloudflare.com/tunnel/reference/origin-parameters/).

### Custom hostname with AWS DNS

Cloudflare for SaaS can serve `mcp.releem.com` while its authoritative DNS remains
in Route53. This is a separate setup from paid partial DNS; SaaS custom hostnames
are available on the Free plan. In the Cloudflare zone serving `mcp.releem.net`:

- Configure the tunnel-backed fallback origin and confirm its status is Active.
- Add `mcp.releem.com` under **SSL/TLS → Custom Hostnames**; complete the provided
  ownership/certificate validation records and confirm both statuses are Active.
- In Route53, create a CNAME for `mcp.releem.com` to `mcp.releem.net` when that is
  the provider hostname configured for this setup.
- Ensure tunnel routing matches the incoming custom hostname `mcp.releem.com`
  and forwards to `http://mcp:8000`. A DNS alias does not rewrite the HTTP Host.

A CNAME by itself does not configure custom-hostname TLS or origin routing.
See Cloudflare's [SaaS setup](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/start/getting-started/),
[Tunnel fallback architecture](https://developers.cloudflare.com/reference-architecture/design-guides/extending-cloudflares-benefits-to-saas-providers-end-customers/)
and [plan availability](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/plans/).

### Replace an incorrect tunnel token

Run on the managed server. This removes only the connector container and its old
token; the MCP service keeps running. The helper prompts privately for a new token:

```bash
sudo /opt/mcp-releem/stack --profile tunnel rm --stop --force cloudflared
sudo rm -f /opt/mcp-releem/secrets/tunnel-token
sudo bash /opt/mcp-releem/setup/start-tunnel.sh --dry-run
sudo bash /opt/mcp-releem/setup/start-tunnel.sh --apply
```

Paste only the token at the hidden prompt. Recheck connector logs and public
health/authentication denial after startup.

## GitHub setup

The local workflow `.github/workflows/deploy.yml` must be reviewed and published to
the repository's default branch before GitHub can run it. This task does not commit
or push the existing workspace. The workflow is manually dispatched initially;
it automates verification, publication, deployment and local/public checks.

In **Releem/mcp-releem → Settings → Environments**, create `production`.
Restrict it to the default branch and configure reviewers if desired. Add:

| Environment secret | Content |
| --- | --- |
| `DEPLOY_SSH_KEY` | Dedicated unencrypted automation private key; never your personal passphrase-protected key |
| `DEPLOY_KNOWN_HOSTS` | Full verified ED25519 known_hosts line for40.160.8.37, not just its fingerprint |

For this setup a dedicated key has already been generated locally at
`.agent/deploy/github_ed25519`, with public fingerprint
`SHA256:pHt2c8s5/W8IN24up3FgdBf8colfLo7ehJYbaZQtwgM`. Its restricted public key is
installed on the server. Add the private file contents to `DEPLOY_SSH_KEY` through
GitHub's secret UI; use `.agent/deploy/known_hosts` for `DEPLOY_KNOWN_HOSTS`.
These ignored local files must never be committed or pasted into chat.

Verified fingerprint: `SHA256:vUhcic9+BnLGbikRaBg0ocgyPa5ixjmyIyYmOJ5wN7A`.
Use the verified local `.agent/deploy/known_hosts` line after independently checking
the fingerprint. Never use `StrictHostKeyChecking=no` or trust a CI-time keyscan.

Generate an automation-only key locally with `ssh-keygen -t ed25519 -N '' -f
<private-path>` and install its public key under ubuntu's authorized_keys with
`restrict` (no forwarding/PTY). Add the private part through GitHub's secret UI,
then keep/remove the local copy according to your credential policy. Do not paste
it into chat. This key still grants command execution and sudo on the deployment
account: treat it as host-administrator access. A forced-command deployment broker
is a separate hardening step, not a property of this workflow.

The workflow uses GitHub's ephemeral `GITHUB_TOKEN` for GHCR push and pull, so no
long-lived registry password is needed on the server. Verify organization package
creation policy permits the repository to publish `ghcr.io/releem/releem-mcp-server`;
the workflow does not change package visibility. Customer API keys and tunnel
tokens are never GitHub secrets.

If GHCR login succeeds but the final image push returns `denied`, check package
permissions before changing tokens. In **Releem → Packages → releem-mcp-server →
Package settings → Manage Actions access**, grant repository **Releem/mcp-releem**
the **Write** role. Connect the package to that repository as well; an existing
package does not necessarily inherit permissions just because it is linked later.
The workflow already requests `packages: write`. If the package does not exist,
check the organization's package-creation policy. See GitHub's
[workflow package access guidance](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility#ensuring-workflow-access-to-your-package).

The image's `org.opencontainers.image.source` label must identify the current
repository, `https://github.com/Releem/mcp-releem`. The registry package name stays
`ghcr.io/releem/releem-mcp-server`; it need not equal the repository name. Publish
metadata corrections and start a new workflow run so it builds the updated image.
The temporary Docker credentials-file warning after login is not a push denial;
the workflow removes that file through its exit trap, including on failure.

Go to **Actions → Deploy MCP production → Run workflow**, selecting the default
branch. Concurrent deploys serialize; in-progress runs are not cancelled. Deployment
does not run on PRs or arbitrary branches. Verification runs in native AMD64 Docker,
including locked dependencies, Ruff, mypy, offline tests, both transport contracts,
wheel/sdist, Compose lifecycle and public package/image advisory scans. Only that
verified image is tagged/pushed, then referenced by registry digest. See
[GitHub's GHCR documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

For secret-upload commands and the optional default-branch `push` trigger, follow
the [README deployment steps](../README.md#deploy-the-hosted-server-and-enable-github-deployment).
The checked-in workflow remains manual until that trigger is explicitly added.

Registry login is temporary under the upload directory and removed after the run.
SSH private keys exist only in the runner's temporary directory and are removed
after deployment. `activate.sh` uses only named administrator environment settings;
no source checkout, dotenv or customer key is transferred by GitHub.

## Failure recovery

Application releases live under `/opt/mcp-releem/releases`, with `current` and
`previous` symlinks. A deployment lock rejects overlapping manual runs. Failed
local health/auth checks recover the preceding release and verify its health/auth.
On first-deployment failure the failed candidate stops. Failed public checks also
attempt the previous application image, but do not change Cloudflare routes;
an ingress failure may still need Cloudflare repair. The workflow remains failed
even if application rollback succeeds. Images/releases are retained for review;
there is no automatic prune. Inspect a stale lock before removing it.

Manual rollback after inspecting the target release:

```bash
sudo sh /opt/mcp-releem/setup/activate.sh --dry-run \
  <previous-immutable-image> /opt/mcp-releem/previous/compose.yaml
sudo sh /opt/mcp-releem/setup/activate.sh --apply \
  <previous-immutable-image> /opt/mcp-releem/previous/compose.yaml
```

Application updates/rollbacks target only service `mcp`, leaving the connector
running in the same project. The tunnel helper persists `COMPOSE_PROFILES=tunnel`
in the administrator environment file; future application activations preserve it
when the token exists. Token values never enter that file. Both services use
`unless-stopped`; enabled Docker provides reboot startup. Compose waits for MCP's
health on initial startup, but Docker restart policies do not enforce dependency
ordering at reboot: cloudflared reconnects while MCP comes up. Health failures
alone do not restart a process. Single-container updates can interrupt requests;
clients must reconnect. A real reboot/HTTPS test remains necessary.

Operate the single stack on the server:

```bash
sudo /opt/mcp-releem/stack ps
sudo /opt/mcp-releem/stack up -d --no-build --pull never --wait
sudo /opt/mcp-releem/stack restart
sudo /opt/mcp-releem/stack logs --tail 50
```

The stable wrapper always selects the current release's Compose/environment files
and the fixed `mcp-releem` project. Deliberately stopped containers stay stopped
after reboot; `up` starts them again. Do not use `down` unless you intend to remove
both services. The old separate tunnel project is rejected by the setup helper;
if one exists, plan its migration before starting a duplicate connector.
