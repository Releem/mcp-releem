#!/usr/bin/env bash
# Local verification only: never publishes, deploys, reads .env or calls customer APIs.
set -euo pipefail
cd "$(dirname "$0")/.."
export BUILDX_CONFIG="${BUILDX_CONFIG:-${TMPDIR:-/tmp}/mcp-releem-buildx}"
root="$PWD"
output="$(mktemp -d "${TMPDIR:-/tmp}/mcp-releem-release.XXXXXXXX")"
run_id="$(basename "$output")"
checks="mcp-releem:${run_id}-checks"
runtime="mcp-releem:${run_id}-runtime"
hosted="mcp-releem:${run_id}-hosted"
wheel="mcp-releem:${run_id}-wheel-check"
printf 'Release verification output: %s\n' "$output"
# Existing images/artifacts are retained; a failed command leaves no verification.json.
docker build --target checks -t "$checks" .
docker run --rm --network none -v "$root:/checkout:ro" --entrypoint python "$checks" \
  /checkout/tools/release/provenance.py /checkout > "$output/source-manifest.json"
docker run --rm --network none "$checks" ruff format --no-cache --check src tests tools/release tools/containers
docker run --rm --network none "$checks" ruff check --no-cache src tests tools/release tools/containers
docker run --rm --network none "$checks" mypy --strict --cache-dir /tmp/mypy src tools/release tools/containers
docker run --rm --network none "$checks" pytest -q -p no:cacheprovider
docker build --target runtime -t "$runtime" .
docker build --target hosted -t "$hosted" .
docker build --target artifacts --output "type=local,dest=$output" .
# The wheel-check target installs the exact build output over locked runtime deps.
docker build --target wheel-check -t "$wheel" .
docker run --rm --network none -v "$root/tools/release:/release:ro" \
  --workdir /tmp --entrypoint python "$wheel" \
  /release/installed_check.py 0.1.0 > "$output/wheel-check.json"
docker run --rm --network none -v "$root/tools/release:/release:ro" \
  --workdir /tmp --entrypoint python "$runtime" \
  /release/installed_check.py 0.1.0 > "$output/installed-check.json"
docker run --rm --network none -v "$root/tools/release:/release:ro" \
  --workdir /tmp --entrypoint python "$hosted" \
  /release/local_journey.py > "$output/local-journey.json"
docker run --rm --network none -v "$root/tools/release:/release:ro" \
  --entrypoint python "$runtime" /release/dependencies.py > "$output/licenses.json"
bash tools/release/compose_smoke.sh "$hosted" > "$output/compose-smoke.log"
docker image inspect "$runtime" > "$output/image-inspect.json"
docker save -o "$output/runtime-image.tar" "$runtime"
docker image inspect "$hosted" > "$output/hosted-image-inspect.json"
docker save -o "$output/hosted-image.tar" "$hosted"
docker run --rm --network none -v "$root:/checkout:ro" --entrypoint python "$checks" \
  /checkout/tools/release/provenance.py /checkout > "$output/source-manifest-final.json"
cmp "$output/source-manifest.json" "$output/source-manifest-final.json"
if test "${RELEEM_RELEASE_SECURITY:-false}" = true; then
  bash scripts/check-security.sh "$hosted" "$output/hosted-image.tar" "$output"
fi
if test -d .git || test -f .git; then
  revision="$(git rev-parse HEAD)"
  dirty=false
  if test -n "$(git status --porcelain --untracked-files=normal)"; then dirty=true; fi
else
  # An allowlisted source export has no Git history; record its supplied parent
  # revision and always mark dirty. Exact source identity is the manifest hash.
  revision="${RELEEM_RELEASE_SOURCE_REVISION:?Exported source requires parent revision}"
  [[ "$revision" =~ ^[a-f0-9]{40}$ ]] || exit 2
  dirty=true
fi
lock_hash="$(docker run --rm --network none "$checks" python -c \
  'import hashlib; print(hashlib.sha256(open("uv.lock", "rb").read()).hexdigest())')"
docker run --rm --network none --user 0:0 \
  -v "$output:/artifacts" --entrypoint python "$checks" \
  tools/release/artifacts.py /artifacts --version 0.1.0 \
  --revision "$revision" --dirty "$dirty" --lock-hash "$lock_hash"
docker run --rm --user 0:0 --network none -v "$output:/candidate:ro" \
  -v "$root/tools/release:/release:ro" --entrypoint python "$runtime" \
  /release/verify_bundle.py /candidate
printf 'Verified local and hosted candidate: %s\n' "$output"
