# D022: maintained Alpine runtime with no unused SQLite

2026-11-11. Applies to shipped Docker local/hosted profiles; Python package
users retain their own Python installation. Product remains Python3.12 and the
same locked runtime dependencies/tool contracts. No CVE exception is introduced.

## Reason and evidence

The Debian13 slim runtime had47 HIGH package/advisory records across11 IDs with
no fixed trixie versions available. Debian bookworm also remained vulnerable for
sampled SQLite/ncurses IDs. The supported official Python3.12 Alpine3.24 candidate
built all locked native dependencies and passed the original268 offline tests.

Alpine alone was insufficient: SQLite3.53.4 was still affected by119373/119374/119379,
though Alpine's scanner feed did not report those entries. Stable APKBUILD enables
FTS5/session and does not patch those fixes. We did not accept scanner silence as
resolution. Original source: [APKBUILD](https://gitlab.alpinelinux.org/alpine/aports/-/raw/3.24-stable/main/sqlite/APKBUILD),
[SQLite advisory](https://security-tracker.debian.org/tracker/CVE-2026-119379).

## Implementation

Pin official `python:3.12-alpine` at multiarchitecture manifest digest
`sha256:e064671ca452259bab50e8e2c7bd896e39e9a343bb06ca25234adf6fe18d0fc7`.
Observed native image: Python3.12.16/Alpine3.24.4, linux/arm64. Alpine3.24 main
support is listed through2028-06-01. [Python images](https://hub.docker.com/_/python),
[Alpine support](https://www.alpinelinux.org/releases/).

Development/check/build stages retain the official base SQLite because mypy2.4.1
uses it for its type-cache metadata. The runtime stage alone is trimmed before
product dependencies are installed. These development images are not distributed
as the product; their tools operate only on trusted source/synthetic test data.

The stdlib-only build helper reads the official `.python-rundeps` dependencies,
registers every non-SQLite shared-library dependency in `.mcp-python-rundeps`, then
uses APK to remove the old virtual package and sqlite-libs. It physically removes
Python's unused SQLite wrapper/extension. It retains the real APK database and
all other required Python shared libraries. Unexpected dependency/module layout
fails the build, rather than silently skipping removal. No edge repositories,
forced dependency deletion, package-database stripping or source suppression.

Stable repository packages are explicitly pinned to krb5-libs1.22.3-r0 and
zlib1.4-r0. The baseline candidate had16 newly detected HIGH Kerberos records;
the patched version removes them. [Alpine vulnerability database](https://secdb.alpinelinux.org/v3.24/main.json).

## Disposition of original11 advisory IDs

| IDs | Resolution in exact runtime |
| --- | --- |
| CVE-2026-119373/119374/119379 | SQLite package, shared library and Python binding removed; not used by MCP |
| CVE-2026-54369 | acl/acl-libs absent |
| CVE-2026-16742 | systemd/libsystemd/libudev components absent |
| CVE-2026-9538 | Perl/perl-base absent |
| CVE-2026-76642/78408/78409/78410 | Only libuuid from util-linux remains;2.42.3-r1 meets Alpine secdb fixed revisions |
| CVE-2025-69720 | ncurses6.6_p20260516 exceeds upstream fix6.5-20251213 |

Independent review verified candidatefc0c8ece3364 metadata37OSpackages, component
absence, fixed versions, nonroot installed checks and four helper regressions.
Final full security-enabled release receipt must still bind all checks to its
exact image/archive. No deployment or claim of universal vulnerability absence.

## Compatibility and maintenance

Alpine uses musl rather than glibc. Existing uv.lock includes musllinux wheels;
all native dependencies/build/runtime/client/transport checks must pass. Customer
CA/proxy behavior is unchanged; public documentation HTTPS was checked with system
CA and no credential. No customer API read or database operation was performed.

Docker intentionally has no sqlite3/_sqlite3 standard-library module. Our MCP
adapter reads HTTP JSON and exposes no SQLite or arbitrary SQL operations. The
package distribution does not remove modules from customers' Python installations.
Keep this constraint visible and reassess if future SDK/features require SQLite.
If pinned OS versions disappear from stable mirrors, rebuild must fail until a
reviewed version update and complete audit; do not silently fall back. AMD64 is
not certified by native arm64 evidence. Preserve prior reviewed image for rollback,
but do not deploy the superseded vulnerable candidate as a fresh customer release.

Compatibility checks also exposed an offline DNS difference: with Docker networking
disabled, Alpine can reach the existing10s API timeout rather than immediately
reporting a connection failure. The installed smoke accepts the two documented
explicit failures (`timeout`/`dependency_unavailable`) and records the actual code.
It still rejects success/empty healthy output and does not change product retries,
network timeouts, authorization or error handling. Synthetic successful reads,
cancellation, denials and EOF remain separately required.
