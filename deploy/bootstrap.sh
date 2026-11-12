#!/bin/sh
# Ubuntu target only. Does not modify SSH, firewall or unrelated services.
set -eu
mode=${1:?Use --dry-run or --apply}
case "$mode" in --dry-run|--apply) ;; *) exit 2;; esac
# shellcheck source=/dev/null
. /etc/os-release
test "$ID" = ubuntu
test "$(uname -m)" = x86_64
if command -v docker >/dev/null; then
    docker compose version
    exit 0
fi
for package in docker.io podman-docker containerd runc; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        printf 'Conflicting package %s; inspect manually\n' "$package" >&2
        exit 1
    fi
done
printf 'Install Docker Engine/CLI, containerd.io, buildx and Compose from Docker stable Ubuntu repository; enable docker.service\n'
if test "$mode" = --dry-run; then exit 0; fi
test "$(id -u)" = 0
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod 0644 /etc/apt/keyrings/docker.asc
test ! -e /etc/apt/sources.list.d/docker.sources
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker compose version
