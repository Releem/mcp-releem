# Private MVP security and local-client review

**Superseded runtime findings:** the final hardened Alpine runtime passed the
security-enabled release check on2026-11-11. All11 original advisory IDs are
resolved by actual component removal/absence or verified fixed versions. No
exceptions or suppressions. [Resolution](../decisions/0003-hardened-runtime.md),
[exact-image evidence](evidence/2026-11-11-runtime-security.json). Historical
Debian scan findings and earlier failed gates remain below for provenance.

Date2026-11-11 UTC. Local testing only, synthetic accounts chosen by owner. No
customer key/data read or sent to models, real key revocation, database operation,
Cloudflare change, publication or Git push. Credential rotation remains UNCONFIRMED.

## Source review

Independent review inspected hosted auth/context/admission, API registry/client,
redaction/ownership, MCP presentation and Docker/Compose/release boundaries.
No tenant crossover or mutation path was demonstrated. This is not a formal
penetration-test certification or proof of absence of defects.

One important finding was reproduced:16 unauthenticated slow bodies using invented
keys consumed all shared work slots; a valid customer received429 before any API
read. Fixed by separate bounded body reception (32 slots/3s) and inventory validation
(8 slots/5s), with customer work admission only after successful authentication.
Invalid keys no longer charge customer quotas. Timeout/cancellation releases stage
counters. Sustained unauthenticated floods can still saturate preauthentication;
Cloudflare ingress request/source limits remain a public deployment requirement.

A lower-severity finding: unknown JSON-RPC method names were echoed by the SDK.
The boundary now validates the protocol-method allowlist and returns a fixed error.
Caller tool inputs/resources/prompts remain prevalidated; no permission is inferred
from annotations. Regression tests cover both findings. Independent follow-up
review and synthetic cancellation/timeout probes found no new important blocker.

## Dependency/advisory evidence

Pinned pip-audit2.10.1, obtained from PyPI in a temporary container, reported zero
known vulnerabilities for all29 third-party runtime Python packages. First-party
mcp-releem0.1.0 is not on PyPI and was excluded explicitly, with source reviewed
separately. No other skipped package is accepted by the report validator. License
metadata and bundled notices were present for all29; release bundles now include
licenses.json. No community adapter runtime code was copied. This inventory is
not a blanket legal opinion or an OS/package-manager inventory.

Sources: [pip-audit](https://github.com/pypa/pip-audit),
[version metadata](https://pypi.org/pypi/pip-audit/2.10.1/json).

Trivy0.76.2 image digest
`sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`
scanned the prior hosted image archive without a Docker socket. It detected
Debian13.7 and49 HIGH package/advisory records, zero CRITICAL. Multiple package
records share the same source advisory; these are not49 independent vulnerabilities.
These49 records represent13 distinct advisory IDs. Two records affect zlib1g and have a published fixed version. The Docker build
now installs Debian's signed `zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1` inside the
container while retaining the digest-pinned Python base. Final image scan evidence
must establish the actual remaining count; no finding is silently ignored.

[Debian zlib fix1](https://security-tracker.debian.org/tracker/CVE-2026-76844),
[fix2](https://security-tracker.debian.org/tracker/CVE-2026-85091).

The remaining source advisories include util-linux, acl, ncurses, SQLite, systemd
and Perl. Trivy reports no fixed trixie package for those sampled records. Some
require local filesystem/privileged utility operations not exposed as MCP tools;
nonroot, no-new-privileges, dropped capabilities/read-only root reduce such paths.
That is a mitigation/inference, not a universal non-applicability determination.
For example Debian calls CVE-2026-76642 minor/no-dsa in trixie while the scanner
rates it HIGH: [Debian assessment](https://security-tracker.debian.org/tracker/CVE-2026-76642).
No blanket exception or high-severity suppression has been approved. These remain
an explicit release risk requiring advisory-by-advisory disposition or remediation.

## Local client evidence

- Real SDK clients over TCP loopback: both legacy and2026-07-28 modes exercise
  discovery, explicit selection, missing health snapshot/security finding,
  recommendation list/detail and static explanation prompt/reference.
- Two synthetic keys use the same URL, receive distinct inventories, cannot read
  the other's server, and observe simulated revocation/invalid-key401 and dependency
  failure503. This is not evidence of Releem's real revocation propagation.
- Claude Code2.1.70 HTTP registration and configured Host/Authorization headers
  passed connection health in a temporary workspace/config directory. Existing
  user MCP configuration was untouched. Isolated profile has no model login;
  model-directed tool use/prompt UI remains unverified. Existing account credentials
  were not copied into the isolated profile. No model call was performed.

## Release gate

Run `bash scripts/check-release.sh` for offline checks/installed TCP journey and
Compose recovery; `RELEEM_RELEASE_SECURITY=true bash scripts/check-release.sh`
also queries public advisory services against the exact newly built image. Known
HIGH/CRITICAL image findings fail that gate and must not produce a successful
release receipt. Network failures/unrecognized audit coverage also fail closed.
A passing offline developer-preview receipt does not override a failed security
gate. Pinning/versions, metadata and notices are evidence, not a security guarantee.

Actual-host TLS/Cloudflare source controls, real-account/revocation tests if later
required, model/client onboarding, reviewed release commit, remote CI and supported
host architecture remain separate release gates. No private candidate is published.

## Outstanding base-OS advisory IDs

The initial scan's non-zlib IDs are CVE-2026-76642, CVE-2026-78408,
CVE-2026-78409, CVE-2026-78410 (util-linux), CVE-2026-54369 (acl),
CVE-2025-69720 (ncurses), CVE-2026-119373, CVE-2026-119374,
CVE-2026-119379 (SQLite), CVE-2026-16742 (systemd) and CVE-2026-9538
(Perl). Final-image evidence must determine whether these remain. No fixes
were reported for these versions in the initial image scan. No shell, filesystem
path, SQL, SQLite database or archive-processing tool is exposed by the MCP
allowlist. This constrains remote entry points; it does not authorize exceptions
or certify unrelated container/host attack paths.

## Follow-up helper review

Independent helper review found Linux0700 evidence-directory permissions and stale
success-marker risks in standalone reruns. Generated evidence readers/writers now
use root only inside their temporary verification containers (application remains
UID65532). A Linux-kernel permission probe confirmed nonroot denial and verifier
access. Security success is invalidated before scanning, and validated status must
match the candidate image ID and archive digest; stale/mismatched reports have
observed RED/GREEN regressions. No Docker socket is mounted into audit tools.

Final-image scan for `sha256:5a376c5374198ee733bae02c0abd889d319d7e51c90cdfc466c6d56d63d84ca9`
confirmed the two zlib records are removed. Remaining:47 HIGH package records,
11 distinct IDs listed above, zero CRITICAL, and no fixed versions reported for
those records. The strict security gate therefore remains failed, not suppressed.
Python dependency audit still covers29 third-party packages with zero known
vulnerabilities. Image findings require explicit disposition before release.
