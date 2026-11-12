#!/usr/bin/env bash
# Network-enabled public advisory checks; never mounts a customer env or Docker socket.
set -euo pipefail
cd "$(dirname "$0")/.."
image="${1:?Pass the exact installed runtime image}"
archive="${2:?Pass its Docker image archive}"
output="${3:?Pass an existing output directory}"
root="$PWD"
archive_dir="$(cd "$(dirname "$archive")" && pwd)"
archive_name="$(basename "$archive")"
output="$(cd "$output" && pwd)"
# Invalidate only this helper's previous success marker before any fallible step.
rm -f "$output/security-report.json"
docker image inspect --format '{{.Id}}' "$image" > "$output/scanned-image-id.txt"
docker run --rm --user 0:0 --network none --read-only --tmpfs /tmp \
  -v "$archive_dir:/candidate:ro" -v "$root/tools/release:/release:ro" \
  --entrypoint python "$image" /release/image_identity.py \
  "/candidate/$archive_name" "$(cat "$output/scanned-image-id.txt")" > "$output/scanned-config-id.txt"
docker run --rm --user 0:0 --network none --read-only --tmpfs /tmp \
  -v "$archive_dir:/candidate:ro" --entrypoint python "$image" -c \
  'import hashlib,sys; f=open(sys.argv[1],"rb"); print(hashlib.file_digest(f,"sha256").hexdigest())' \
  "/candidate/$archive_name" > "$output/scanned-archive-sha256.txt"
docker run --rm --user 0:0 --read-only --tmpfs /tmp:rw,exec,nosuid,mode=1777 \
  -e UV_TOOL_DIR=/tmp/uv-tools -e PIP_CACHE_DIR=/tmp/pip-cache \
  -v "$output:/evidence" --entrypoint uv "$image" \
  tool run --cache-dir /tmp/uv-audit --from pip-audit==2.10.1 \
  pip-audit --cache-dir /tmp/audit-cache --path /opt/venv/lib/python3.12/site-packages \
  --format json --output /evidence/pip-audit.json
docker run --rm --network none --read-only --tmpfs /tmp \
  -v "$root/tools/release:/release:ro" --entrypoint python "$image" \
  /release/dependencies.py > "$output/licenses.json"
docker run --rm --read-only --tmpfs /tmp:rw,exec,nosuid,mode=1777 \
  -v "$archive_dir:/candidate:ro" -v "$output:/evidence" \
  aquasec/trivy@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb \
  image --cache-dir /tmp/trivy --quiet --scanners vuln --severity HIGH,CRITICAL \
  --exit-code 1 --format json --output /evidence/trivy.json --input "/candidate/$archive_name"
docker run --rm --user 0:0 --network none --read-only --tmpfs /tmp \
  -v "$root/tools/release:/release:ro" -v "$output:/evidence" \
  --entrypoint python "$image" /release/security_report.py /evidence
