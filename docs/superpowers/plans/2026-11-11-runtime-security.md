# Resolve runtime OS security gate

Goal: eliminate the11 outstanding advisory IDs without suppressions, while retaining
Python3.12, exact locked Python dependencies and both deployment profiles.

Evidence: final Debian13 image scan failed47HIGH package/advisory records,11 IDs,
zeroCRITICAL and no fixed trixie versions for those records. Debian primary tracker
also lists bookworm vulnerable for sampled SQLite/ncurses IDs; switching between
Debian slim variants alone does not address the cause.

- [x] Inspect supported official Python/Alpine base, support dates, native wheel
  availability in lock, OS/package versions and baseline image scan.
- [x] Build a temporary candidate Dockerfile with only base-image substitution;
  verify locked dependencies (including native extensions), imports and full tests.
- [x] If compatible, pin the tested Alpine image digest in root Dockerfile and
  remove the obsolete Debian-only package patch. Do not remove package metadata
  or weaken advisory severity/coverage gates.
- [x] Verify full runtime/hosted/wheel build, stdio/HTTP/client workflow/Compose
  lifecycle, notices and exact final image/advisory audit.
- [x] Independent review and evidence update. Retain old risk receipt as historical;
  mark it superseded only after the new exact-image gate passes. No deploy/publish/
  commit or unrelated Docker cleanup; no customer API calls or database operations.

Completed: fullsecurity-enabled releasePASS272tests/22checksums;29 Python
packages0knownvulnerabilities;37OSpackages0HIGH/CRITICAL. Independent review
verifiedall11dispositions without suppressions. Exactreceipt in implementation-status.
