# Spec Delta

## MODIFIED Requirements

### Requirement: Network modes from setup, without delegation
On Windows the entry SHALL pass `<P>_NETWORK` unset, `unrestricted`, `offline` or, when the profile declares authentication methods, `provider` to the launcher, and SHALL accept `--container-qualify`. It SHALL exit with status 1, before running WSL, when `<P>_PODMAN` enables delegation. The launcher in the distribution SHALL apply its usual checks to restricted modes.

#### Scenario: Offline session
- **WHEN** setup prepared offline networking in the machine and the user launches the entry from a project directory
- **THEN** the session starts with `network mode=offline` through the machine's launch service and has no network access

#### Scenario: Provider session
- **WHEN** an agent wrapper's setup prepared provider networking in the machine
- **THEN** the session starts with `network mode=provider` and reaches only its policy's hosts through the egress proxy

#### Scenario: Restricted mode without a prepared installation
- **WHEN** `$env:<P>_NETWORK='offline'` is set but setup prepared only unrestricted networking
- **THEN** the launch exits with status 1 and the launcher's setup guidance, before any engine query
- **AND** the guidance names `<name>.ps1 --container-setup` from Windows, not the wrapper path in the distribution

#### Scenario: Qualification
- **WHEN** the user runs `<name>.ps1 --container-qualify` after an offline setup
- **THEN** the fixed qualification runs in the machine and reports its status

#### Scenario: Delegation requested
- **WHEN** `$env:<P>_PODMAN='1'` is set
- **THEN** the entry exits with status 1 stating that delegation is unsupported on Podman machine, and WSL runs nothing
