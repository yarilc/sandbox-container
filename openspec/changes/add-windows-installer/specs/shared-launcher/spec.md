# Spec Delta

## MODIFIED Requirements

### Requirement: Shared Windows shim and bootstrap
The shared launcher SHALL include the Windows shim `launcher/windows/core.ps1`, the installer scripts under `launcher/windows/` and the bootstrap `launcher/windows/bootstrap.sh`, copied byte for byte from the reference tag like the other shared files. None SHALL contain agent identifiers: the shim and the installer SHALL read the wrapper name, file name and variable prefix from `agent/profile.json`. Setup SHALL install the bootstrap in every release.

#### Scenario: Shim edited in a wrapper
- **WHEN** a wrapper's `launcher/windows/core.ps1` differs from the reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Agent-neutral shim
- **WHEN** the alignment test scans the shim and the bootstrap
- **THEN** neither contains the reference's name, prefix or other profile identifiers

#### Scenario: Agent-neutral installer
- **WHEN** the alignment test scans the installer scripts
- **THEN** none contains the reference's name, prefix or other profile identifiers, and each is ASCII
