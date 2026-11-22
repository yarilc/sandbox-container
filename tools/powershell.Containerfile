# PowerShell check image for tools/powershell.sh. Reference-only: never copied.
# PowerShell 7.4 LTS on Ubuntu 22.04, pinned by digest, plus the pinned
# PSScriptAnalyzer package that tools/powershell.sh downloads and verifies.
# The build runs without network and checks the package hash again.
FROM mcr.microsoft.com/powershell@sha256:663a172849444279d8e7b50e19977b6e42380eae6856bdc8931ca08e2e03e92a
ARG PSSA_VERSION
ARG PSSA_SHA256
COPY pssa.nupkg /tmp/pssa.nupkg
RUN pwsh -NoProfile -NonInteractive -Command ' \
    $ErrorActionPreference = "Stop"; \
    $package = "/tmp/pssa.nupkg"; \
    if ((Get-FileHash -Algorithm SHA256 $package).Hash -ne $env:PSSA_SHA256) { throw "PSScriptAnalyzer package hash mismatch" }; \
    Expand-Archive -Path $package -DestinationPath ("/usr/local/share/powershell/Modules/PSScriptAnalyzer/" + $env:PSSA_VERSION); \
    Remove-Item $package; \
    Import-Module PSScriptAnalyzer -RequiredVersion $env:PSSA_VERSION'
