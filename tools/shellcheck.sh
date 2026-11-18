#!/usr/bin/env bash
# Run ShellCheck on every tracked *.sh file of a checkout, at warning level.
#
# Usage: bash tools/shellcheck.sh <checkout>
#
# Reference-only: this tool lives in sandbox-container and is never copied.
# It checks the reference or any wrapper checkout the same way, with a pinned
# ShellCheck (0.11.0) in a container without network, and exits with
# ShellCheck's status. The checkout is mounted read-only at its own path.
set -Eeuo pipefail
image=docker.io/koalaman/shellcheck@sha256:b9389b73c8f26f710a7171cb7d8848a34a9c1e07a7865e727c9ec4ce99f9a83f
[[ $# -eq 1 ]] || { printf 'usage: bash tools/shellcheck.sh <checkout>\n' >&2; exit 2; }
command -v git >/dev/null || { printf 'git is required\n' >&2; exit 2; }
command -v podman >/dev/null || { printf 'podman is required\n' >&2; exit 2; }
checkout=$(CDPATH='' cd -- "$1" && pwd -P) || { printf 'not a directory: %s\n' "$1" >&2; exit 2; }
files=()
while IFS= read -r -d '' file; do
    files+=("$file")
done < <(git -C "$checkout" ls-files -z -- '*.sh')
((${#files[@]})) || { printf 'no tracked *.sh files in %s\n' "$checkout" >&2; exit 2; }
exec podman run --rm --network=none --volume "$checkout:$checkout:ro" --workdir "$checkout" \
    "$image" --severity=warning --format=gcc -- "${files[@]}"
