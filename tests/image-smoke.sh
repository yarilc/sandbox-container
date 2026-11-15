#!/usr/bin/env bash
# Run through wrapper shell mode with synthetic state and the standard policy.
set -Eeuo pipefail
[[ $(id -u) != 0 ]]
for tool in openspec bash git python3 bwrap podman rg nano curl jq \
    tar bzip2 zip unzip file ps find patch diff awk xz sed grep less; do
    command -v "$tool" >/dev/null
done
# The reference image is a shell: no agent CLI is installed.
! command -v claude >/dev/null
openspec --version
python3 --version
bwrap --version
nano --version >/dev/null
[[ "$EDITOR" == nano && "$VISUAL" == nano ]]
[[ "$HOME" == /sandbox-home && "$SANDBOX_CONTAINER_CONFIG_DIR" == /sandbox-home/.config/sandbox-container ]]
[[ "$HISTFILE" == "$SANDBOX_CONTAINER_CONFIG_DIR/bash_history" ]]
[[ -w "$SANDBOX_CONTAINER_CONFIG_DIR" && -w /tmp && ! -w /usr ]]
findmnt --noheadings --output OPTIONS --target / | grep -Eq '(^|,)ro(,|$)'
for path in /tmp /run /var/tmp; do
    options=$(findmnt --noheadings --output OPTIONS --target "$path")
    for flag in nosuid nodev noexec; do
        [[ ",$options," == *",$flag,"* ]]
    done
done
# Debian package sources stay on verified HTTPS; the build-time trust bootstrap is gone.
sources=/etc/apt/sources.list.d/debian.sources
uris=$(grep -E '^URIs:' "$sources")
[[ -n "$uris" ]]
if grep -Ev '^URIs:([[:space:]]+https://[^[:space:]]+)+[[:space:]]*$' <<< "$uris"; then
    printf 'Debian package source is not HTTPS.\n' >&2
    exit 1
fi
[[ ! -e /tmp/apt-bootstrap-ca.pem ]]
[[ -s /etc/ssl/certs/ca-certificates.crt ]]
touch /tmp/sandbox-image-smoke
printf 'Image smoke checks passed.\n'
