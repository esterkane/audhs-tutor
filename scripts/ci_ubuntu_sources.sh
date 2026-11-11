#!/usr/bin/env bash
# Emit a Deb822 source file for the pinned GitHub runner. APT also verifies
# package hashes and signed repository metadata during update and installation.
set -euo pipefail
keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg
signed_release=$(mktemp)
trap 'rm -f "$signed_release"' EXIT
for mirror in https://archive.ubuntu.com/ubuntu https://mirrors.edge.kernel.org/ubuntu https://ftp.fau.de/ubuntu; do
    if curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --connect-timeout 4 --max-time 10 "$mirror/dists/noble-security/InRelease" -o "$signed_release" \
        && gpgv --keyring "$keyring" "$signed_release" >/dev/null 2>&1 \
        && grep -Fqx 'Suite: noble-security' "$signed_release"; then
        printf 'Types: deb\nURIs: %s\nSuites: noble noble-updates noble-security\nComponents: main restricted universe multiverse\nSigned-By: %s\n' "$mirror" "$keyring"
        exit 0
    fi
done
echo 'No Ubuntu mirror supplied a verified noble-security Release.' >&2
exit 1
