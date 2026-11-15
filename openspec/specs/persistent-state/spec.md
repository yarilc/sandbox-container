# persistent-state Specification

## Purpose

Preserve compatible shared Claude state while offering explicit application-home isolation and enforcing private credential directory ownership and permissions.

## Requirements

### Requirement: Explicit isolated application home
A nonempty `SANDBOX_CONTAINER_STATE_DIR` SHALL select a dedicated writable home at `/sandbox-home`, containing shell state, OpenSpec configuration, caches, and other home data. The wrapper SHALL NOT add shared host shell or OpenSpec configuration mounts in this mode. A simultaneous nonempty host `SANDBOX_CONTAINER_CONFIG_DIR` SHALL fail with an actionable conflict error before image operations or launch.

#### Scenario: Fresh isolated profile
- **WHEN** a dedicated state directory is selected and host `SANDBOX_CONTAINER_CONFIG_DIR` is unset or empty
- **THEN** the container uses `HOME=/sandbox-home` and `SANDBOX_CONTAINER_CONFIG_DIR=/sandbox-home/.config/sandbox-container` with configuration persisted under the selected directory
- **AND** the wrapper adds no shared host configuration mounts or automatic imports

#### Scenario: Conflicting profile controls
- **WHEN** dedicated state and a nonempty host `SANDBOX_CONTAINER_CONFIG_DIR` are both selected
- **THEN** startup fails before image operations with instructions to select one state mode

### Requirement: Private credential directories
The wrapper SHALL create selected state directories with user-only permissions and verify caller ownership and read/write/search access. It SHALL reject group/other access on the shared configuration directory or isolated home and its existing `.config/sandbox-container` directory. Errors SHALL identify the path and suggest explicit repair or permission-enforcing storage; existing permissions SHALL NOT be repaired recursively.

#### Scenario: Private state created
- **WHEN** a selected credential directory is absent on a filesystem supporting Unix permissions
- **THEN** it is created privately and verified before container creation

#### Scenario: Unsafe existing directory
- **WHEN** a credential directory has the wrong owner, lacks required access, or grants group/other access
- **THEN** startup fails with a path-specific error without launching a container or recursively changing existing permissions

#### Scenario: Filesystem ignores permissions
- **WHEN** the state filesystem cannot enforce user-only directory access
- **THEN** startup rejects that state and recommends native Linux storage rather than silently weakening privacy

### Requirement: Resolved state paths and isolation scope
The wrapper SHALL resolve selected state sources to physical absolute paths. In isolated mode, existing shell and OpenSpec configuration paths SHALL resolve within that home; escaping configuration symlinks SHALL fail. Documentation SHALL distinguish application-state isolation from access granted independently by workspace mounts or socket delegation.

#### Scenario: Top-level state alias
- **WHEN** the selected state path is a symlink to an accessible private directory
- **THEN** its resolved physical path is used as the bind source

#### Scenario: Isolated configuration escapes home
- **WHEN** `.config/sandbox-container` or `.config/openspec` resolves outside the selected isolated home through a symlink
- **THEN** startup fails with a path-specific isolation error

### Requirement: Explicit migration and reversible selection
The wrapper SHALL neither copy nor merge credentials or settings automatically. Documentation SHALL describe a fresh isolated home, deliberate copying of selected state with sessions stopped, permission checks, and returning to shared mode by unsetting `SANDBOX_CONTAINER_STATE_DIR`. Changing modes SHALL NOT delete either profile.

#### Scenario: Isolated state reused and deselected
- **WHEN** a user restarts with the same dedicated home and later unsets the state override
- **THEN** the dedicated profile persists across its restarts and shared mode resumes without merging or deleting profiles

#### Scenario: Migration instructions reviewed
- **WHEN** a user reads the state-mode documentation
- **THEN** it identifies source and destination layouts, conflict handling, visibility of copied secrets to the shell, backup privacy, and the lack of automatic imports

### Requirement: Private state creation preserves the host process umask
Private state-directory creation SHALL NOT change the umask inherited by subsequent host image, launch, or lifecycle commands. Missing state directories SHALL still be created with user-only permissions in shared and isolated modes. Existing ownership, access, mode, and resolved-path checks SHALL remain enforced without recursive permission repair. Documentation SHALL distinguish this host creation policy from actual container process and file modes.

#### Scenario: Caller umask is preserved for later host commands
- **WHEN** the wrapper starts under caller umask `0022` or `0002` and creates missing state directories
- **THEN** subsequent host Podman commands inherit the caller's original umask
- **AND** the created state directories deny group and other access

#### Scenario: Private creation applies in both state modes
- **WHEN** shared shell/OpenSpec configuration or an isolated application home and its configuration directories must be created
- **THEN** each directory created by those state operations has user-only permissions
- **AND** existing private-directory validation and isolated symlink-escape rejection still apply

#### Scenario: Unsafe existing directories are not repaired
- **WHEN** a selected credential directory already grants group or other access
- **THEN** startup fails with the existing path-specific privacy error
- **AND** existing permissions are not changed recursively

#### Scenario: Runtime permissions have separate evidence
- **WHEN** validation reports the modes of files created by a container session
- **THEN** it records actual container umask and observed file and directory modes
- **AND** it does not infer those modes from the host's private state-creation umask

### Requirement: Isolated state does not overlap the workspace
The wrapper SHALL refuse an isolated state directory that is the workspace mount, contains it, or lies inside it, comparing resolved physical paths. The check SHALL run before image or engine operations, on direct and managed launches, and in worktree mode SHALL use the parent directory that is mounted.

#### Scenario: State directory inside the workspace
- **WHEN** `SANDBOX_CONTAINER_STATE_DIR` names the workspace or a directory below it
- **THEN** startup fails before engine operations, naming the state directory and the workspace

#### Scenario: State directory containing the workspace
- **WHEN** the workspace lies below the selected state directory
- **THEN** startup fails with the same error

#### Scenario: Symlinked state directory
- **WHEN** the selected state path is a symlink that resolves inside the workspace
- **THEN** startup fails with the same error

#### Scenario: Managed launch
- **WHEN** a managed launch selects an isolated state directory that overlaps the workspace
- **THEN** the managed launcher refuses it before starting the wrapper

### Requirement: Shared shell state by default
With `SANDBOX_CONTAINER_STATE_DIR` unset or empty, the wrapper SHALL mount `${SANDBOX_CONTAINER_CONFIG_DIR:-$HOME/.config/sandbox-container}` read/write at `/sandbox-home/.config/sandbox-container` and host `$HOME/.config/openspec` read/write at `/sandbox-home/.config/openspec`. The shell SHALL keep its Bash history in the first. It SHALL keep the remaining home read-only and SHALL NOT create unused host cache or share directories.

#### Scenario: Existing default profile
- **WHEN** no state or configuration-directory override is selected
- **THEN** host `~/.config/sandbox-container` and OpenSpec configuration are the shared persistent sources
- **AND** Bash history written in one session is available in the next

#### Scenario: Custom shared configuration directory
- **WHEN** `SANDBOX_CONTAINER_CONFIG_DIR` names a custom directory and isolated state is not selected
- **THEN** that directory supplies the shell state and shared host OpenSpec configuration remains mounted
