#!/usr/bin/env bash
# Check the PowerShell files of a checkout: PSScriptAnalyzer at warning level
# on every tracked or new *.ps1 file, then the shim logic tests
# (tests/windows/shim_tests.ps1) when the checkout has them.
#
# Usage: bash tools/powershell.sh <checkout>
#
# Reference-only: this tool lives in sandbox-container and is never copied. It
# checks the reference or any wrapper checkout the same way, on PowerShell 7 in
# the image built from tools/powershell.Containerfile. Building that image once
# needs the network; the checks run with --network=none and the checkout
# mounted read-only at its own path. Windows PowerShell 5.1 is validated on a
# Windows host with tools/windows-validate.ps1.
set -Eeuo pipefail
here=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ $# -eq 1 ]] || { printf 'usage: bash tools/powershell.sh <checkout>\n' >&2; exit 2; }
command -v git >/dev/null || { printf 'git is required\n' >&2; exit 2; }
command -v podman >/dev/null || { printf 'podman is required\n' >&2; exit 2; }
checkout=$(CDPATH='' cd -- "$1" && pwd -P) || { printf 'not a directory: %s\n' "$1" >&2; exit 2; }
files=()
while IFS= read -r -d '' file; do
    [[ -f "$checkout/$file" ]] && files+=("$file")
done < <(git -C "$checkout" ls-files -z --cached --others --exclude-standard -- '*.ps1')
((${#files[@]})) || { printf 'no *.ps1 files in %s\n' "$checkout" >&2; exit 2; }

# Pinned analyzer. The package is fetched here, with the host's TLS trust, and
# verified twice: before the build and inside it, which runs without network.
pssa_version=1.24.0
pssa_sha256=e86c97d44bb1bc8a1de35e753b85ea1d938f6f9f881639a181507e079bca4556
pssa_url=https://www.powershellgallery.com/api/v2/package/PSScriptAnalyzer/$pssa_version
# The image tag follows the recipe and the pin, so a change builds a new image.
recipe=$here/powershell.Containerfile
image=localhost/sandbox-tools-powershell:$( { cat "$recipe"; printf '%s %s\n' "$pssa_version" "$pssa_sha256"; } \
    | sha256sum | cut -c1-12)
if ! podman image exists "$image"; then
    command -v curl >/dev/null || { printf 'curl is required to fetch PSScriptAnalyzer once\n' >&2; exit 2; }
    context=$(mktemp -d)
    status=0
    if curl -fsSL --proto '=https' -o "$context/pssa.nupkg" "$pssa_url" \
        && printf '%s  %s\n' "$pssa_sha256" "$context/pssa.nupkg" | sha256sum --check --quiet -; then
        podman build --format docker --network=none --build-arg "PSSA_VERSION=$pssa_version" \
            --build-arg "PSSA_SHA256=$pssa_sha256" --tag "$image" --file "$recipe" "$context" >&2 || status=$?
    else
        printf 'cannot fetch or verify PSScriptAnalyzer %s\n' "$pssa_version" >&2
        status=1
    fi
    rm -rf -- "$context"
    ((status == 0)) || exit "$status"
fi

# shellcheck disable=SC2016 # PowerShell code, expanded by pwsh.
check='
$ErrorActionPreference = "Stop"
Import-Module PSScriptAnalyzer
$failed = $false
foreach ($file in @($env:PS_FILES -split "`n" | Where-Object { $_ })) {
    foreach ($finding in @(Invoke-ScriptAnalyzer -Path $file -Severity Warning, Error)) {
        $failed = $true
        [Console]::Out.WriteLine(("{0}:{1}:{2}: {3}: {4}" -f $file, $finding.Line, $finding.Column, $finding.RuleName, $finding.Message))
    }
}
if (Test-Path -LiteralPath "tests/windows/shim_tests.ps1") {
    & pwsh -NoProfile -NonInteractive -File "tests/windows/shim_tests.ps1"
    if ($LASTEXITCODE -ne 0) { $failed = $true }
}
if ($failed) { exit 1 }
'
exec podman run --rm --network=none --volume "$checkout:$checkout:ro" --workdir "$checkout" \
    --env "PS_FILES=$(printf '%s\n' "${files[@]}")" "$image" pwsh -NoProfile -NonInteractive -Command "$check"
