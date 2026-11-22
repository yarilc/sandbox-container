# Spec Delta

## MODIFIED Requirements

### Requirement: Ordinary launches run the managed installation in the machine distribution
The entry SHALL run every ordinary launch through the managed installation in
the selected WSL distribution, as the selected user, starting the bootstrap of
that installation's current release. It SHALL use no other WSL distribution and
neither the machine's SSH connection nor its Windows API connection, and SHALL
run no checkout script inside the distribution for an ordinary launch.
Restricted modes SHALL use the distribution's own Unix launch service.

#### Scenario: Another distribution is active
- **WHEN** an Ubuntu distribution is running and the user launches the entry from a project directory
- **THEN** the session starts on the machine distribution's local rootless engine

#### Scenario: Release bootstrap only
- **WHEN** an ordinary launch runs after setup
- **THEN** the distribution executes the bootstrap, the namespace helper and the wrapper from the protected release, not from the Windows checkout
- **AND** the release contains the bootstrap and the helper as protected files

## ADDED Requirements

### Requirement: Sessions and setup in the machine's systemd namespaces
Sessions and setup that the entry starts SHALL run as the selected user in the PID and mount namespaces of the machine's systemd, as the machine's login shells do, with the environment, working directory, standard streams and exit status unchanged and `XDG_RUNTIME_DIR=/run/user/<uid>`. When systemd is the distribution's PID 1, they SHALL run directly. When `sudo` needs a password, the entry SHALL exit with status 1 before any Podman command.

#### Scenario: One engine for sessions and the machine
- **WHEN** a session started by the entry runs its container
- **THEN** the machine's launch service can run a command in that container and remove it
- **AND** the session's podman and the service use one rootless user namespace

#### Scenario: Setup probe
- **WHEN** the machine that Podman started serves its rootless API at `/run/user/<uid>/podman/podman.sock` and the user runs `<name>.ps1 --container-setup`
- **THEN** setup finds that service and offers every network mode that the profile allows

#### Scenario: Socket of another distribution
- **WHEN** another WSL distribution serves a Podman socket under `/mnt/wslg/runtime-dir/podman/`
- **THEN** neither setup nor a launch from the entry uses it

#### Scenario: Password required
- **WHEN** `sudo` in the distribution asks the user for a password
- **THEN** setup and the launch exit with status 1 naming passwordless `sudo` as a machine requirement, before any Podman command
- **AND** `<name>.ps1 --container-help`, which queries no engine, still prints the help without `sudo`

#### Scenario: Environment kept
- **WHEN** a launch forwards `<P>_NETWORK`, a configuration directory and a 30000-character argument
- **THEN** the wrapper receives them unchanged inside the namespaces, and no file of the transport remains

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

#### Scenario: Qualification
- **WHEN** the user runs `<name>.ps1 --container-qualify` after an offline setup
- **THEN** the fixed qualification runs in the machine and reports its status

#### Scenario: Delegation requested
- **WHEN** `$env:<P>_PODMAN='1'` is set
- **THEN** the entry exits with status 1 stating that delegation is unsupported on Podman machine, and WSL runs nothing

### Requirement: Saved delegation refused
The bootstrap SHALL exit with status 1, before running the managed command, when the release's saved preferences enable Podman delegation, and SHALL ask to rerun setup from Windows. Saved unrestricted, offline and provider networking SHALL be accepted.

#### Scenario: Saved delegation
- **WHEN** a release saved delegation, for example because setup ran from a Linux shell in the machine
- **THEN** every launch through the entry exits with status 1 before any Podman command, asking to rerun `<name>.ps1 --container-setup`

#### Scenario: Saved offline networking
- **WHEN** setup from Windows saved offline networking
- **THEN** the bootstrap runs the managed command

## REMOVED Requirements

### Requirement: Only unrestricted networking without delegation
**Reason**: The machine supports offline and provider networking through its own launch service.
**Migration**: Replaced by "Network modes from setup, without delegation": delegation stays refused, and restricted modes follow setup.

### Requirement: Saved preferences limited to unrestricted networking
**Reason**: Saved offline and provider networking are supported on the machine.
**Migration**: Replaced by "Saved delegation refused".
