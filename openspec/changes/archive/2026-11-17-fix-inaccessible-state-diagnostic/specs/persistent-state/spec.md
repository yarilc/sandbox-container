## MODIFIED Requirements

### Requirement: Private credential directories
The wrapper SHALL create selected state directories with user-only permissions and verify caller ownership and read/write/search access. It SHALL reject group/other access on the shared configuration directory or isolated home and its existing `.config/sandbox-container` directory. Errors SHALL carry the wrapper prefix, identify the path and suggest explicit repair or permission-enforcing storage; existing permissions SHALL NOT be repaired recursively. Access SHALL be checked before a path is resolved, so no raw shell error replaces the wrapper's diagnostic.

#### Scenario: Private state created
- **WHEN** a selected credential directory is absent on a filesystem supporting Unix permissions
- **THEN** it is created privately and verified before container creation

#### Scenario: Unsafe existing directory
- **WHEN** a credential directory has the wrong owner, lacks required access, or grants group/other access
- **THEN** startup fails with a path-specific error without launching a container or recursively changing existing permissions

#### Scenario: Filesystem ignores permissions
- **WHEN** the state filesystem cannot enforce user-only directory access
- **THEN** startup rejects that state and recommends native Linux storage rather than silently weakening privacy

#### Scenario: Directory the caller cannot enter
- **WHEN** the shared configuration directory, a shared directory, the isolated home or one of its children exists with mode `000`
- **THEN** startup fails before image operations with `sandbox-container: state directory is not accessible: <path>` and a hint to grant the caller access or choose another directory
- **AND** stderr contains no shell error such as `cd: ... Permission denied`

#### Scenario: Directory that cannot be created
- **WHEN** a selected state directory is absent and its parent does not let the caller create it
- **THEN** startup fails before image operations with a prefixed error naming the directory that could not be created

### Requirement: Read-only state
`SANDBOX_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the configuration directory and every shared directory read-only below the ephemeral home, taken from shared state or from the isolated home. Those directories SHALL already exist and be accessible to the caller; the launcher SHALL NOT create them, check their owner or privacy, or pass them to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `SANDBOX_CONTAINER_READONLY_STATE=1` is set and the shared configuration directories exist
- **THEN** the session sees them read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and a configuration directory does not exist
- **THEN** the launch stops before the engine names the missing directory

#### Scenario: Inaccessible read-only state
- **WHEN** read-only state is selected and a configuration directory exists but the caller cannot enter it
- **THEN** the launch stops before image operations with a prefixed error naming that directory, without a shell error
