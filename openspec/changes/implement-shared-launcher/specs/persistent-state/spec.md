# Spec Delta

## ADDED Requirements

### Requirement: Read-only state
`SANDBOX_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the configuration directory and every shared directory read-only below the ephemeral home, taken from shared state or from the isolated home. Those directories SHALL already exist; the launcher SHALL NOT create them, check their owner or privacy, or pass them to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `SANDBOX_CONTAINER_READONLY_STATE=1` is set and the shared configuration directories exist
- **THEN** the session sees them read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and a configuration directory does not exist
- **THEN** the launch stops before the engine names the missing directory

## MODIFIED Requirements

### Requirement: Shared shell state by default
With `SANDBOX_CONTAINER_STATE_DIR` unset or empty, the wrapper SHALL mount `${SANDBOX_CONTAINER_CONFIG_DIR:-$HOME/.config/sandbox-container}` read/write at `/sandbox-home/.config/sandbox-container` and host `$HOME/.config/openspec` read/write at `/sandbox-home/.config/openspec`, below an ephemeral tmpfs home. The shell SHALL keep its Bash history in the first. Other home content SHALL disappear with the session, and the wrapper SHALL NOT create unused host cache or share directories.

#### Scenario: Existing default profile
- **WHEN** no state or configuration-directory override is selected
- **THEN** host `~/.config/sandbox-container` and OpenSpec configuration are the shared persistent sources
- **AND** Bash history written in one session is available in the next

#### Scenario: Custom shared configuration directory
- **WHEN** `SANDBOX_CONTAINER_CONFIG_DIR` names a custom directory and isolated state is not selected
- **THEN** that directory supplies the shell state and shared host OpenSpec configuration remains mounted

#### Scenario: Ephemeral home content
- **WHEN** a shared-state session writes a file directly in `/sandbox-home`
- **THEN** the write succeeds and the file is absent in the next session

### Requirement: Resolved state paths and isolation scope
The wrapper SHALL resolve selected state sources to physical absolute paths. `SANDBOX_CONTAINER_STATE_DIR` and the configuration override SHALL be absolute and free of colon, CR and LF, checked before any engine operation. In isolated mode, every configuration child and the CA mount parent SHALL resolve within that home and be private; escaping configuration symlinks SHALL fail. Documentation SHALL distinguish application-state isolation from access granted independently by workspace mounts or socket delegation.

#### Scenario: Top-level state alias
- **WHEN** the selected state path is a symlink to an accessible private directory
- **THEN** its resolved physical path is used as the bind source

#### Scenario: Isolated configuration escapes home
- **WHEN** `.config/sandbox-container` or `.config/openspec` resolves outside the selected isolated home through a symlink
- **THEN** startup fails with a path-specific isolation error

#### Scenario: Unusable state path
- **WHEN** `SANDBOX_CONTAINER_STATE_DIR` is relative or contains a colon
- **THEN** startup fails before any engine query

#### Scenario: Shared isolated child
- **WHEN** an existing `.config/openspec` inside the isolated home is readable by group or others
- **THEN** startup fails naming the directory
