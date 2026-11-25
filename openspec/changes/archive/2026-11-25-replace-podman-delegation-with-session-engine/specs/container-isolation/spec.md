# Spec Delta

## ADDED Requirements

### Requirement: Shell containers drop all capabilities and privilege gains
Every shell container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in all network modes and when the session has a container engine. The wrapper SHALL NOT add a capability back to resolve an incompatibility. A tool that needs a capability SHALL be documented as unsupported.

#### Scenario: Unrestricted shell session starts
- **WHEN** an explicitly unrestricted shell session starts with shared or isolated state
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Engine client works without capabilities
- **WHEN** a session with a container engine runs `podman info` and creates a child container through its `CONTAINER_HOST`
- **THEN** the client succeeds without capabilities in the shell container
- **AND** the documentation states the engine container's own hardening exceptions

#### Scenario: Incompatible tool is documented, not re-privileged
- **WHEN** a tool inside the session fails only because capabilities or privilege gains are unavailable
- **THEN** the wrapper adds no capability and does not disable no-new-privileges
- **AND** the limitation is recorded in the validation record

## MODIFIED Requirements

### Requirement: Read-only system and caller identity
Sessions SHALL use a read-only container root, `--userns=keep-id`, and the caller's UID/GID. Writable persistent binds SHALL be limited to the selected workspace and state mode. No Podman socket SHALL be mounted into a session. The host CA exception SHALL remain a read-only single-file mount governed by `host-ca-trust`.

#### Scenario: Ordinary session boundaries
- **WHEN** a session writes to its workspace and attempts to change `/usr`
- **THEN** workspace files belong to the caller and the system write fails
- **AND** a host sentinel outside all selected mounts is inaccessible, also through containers started by the session's container engine

#### Scenario: Worktree expansion
- **WHEN** `--container-git-worktree` selects the immediate physical parent
- **THEN** the entire selected parent is writable as specified by `workspace-mounts`, with no additional inferred Git mounts

### Requirement: Shell options do not weaken the network boundary
The reference wrapper SHALL expose no approval-bypass control. A session container engine SHALL NOT widen the session's network boundary, independently of state mode, worktree scope and the command passed to the shell. A leftover exact `SANDBOX_CONTAINER_PODMAN=1` SHALL stop startup in every mode.

#### Scenario: Delegation combinations in either state mode
- **WHEN** unrestricted mode is selected with and without a leftover exact Podman opt-in, in shared and isolated modes
- **THEN** the opt-in stops startup with migration guidance in both modes, and no session receives a Podman socket or a delegation variable

#### Scenario: Shell commands cannot change egress
- **WHEN** an offline session runs a command passed to the wrapper or an interactive Bash shell
- **THEN** offline restriction still applies
- **AND** a leftover exact `SANDBOX_CONTAINER_PODMAN=1` stops startup in either state mode, and containers started by the session's engine reach no external service

#### Scenario: Agent approval variable has no effect
- **WHEN** `CLAUDE_YOLO` or another agent's approval variable is set in the caller environment
- **THEN** the wrapper ignores it and passes no permission-bypass argument to Bash

## REMOVED Requirements

### Requirement: Every shell container drops capabilities and privilege gains
**Reason**: Its delegated-client scenario described host Podman delegation, which this change removes.
**Migration**: The same rule continues as "Shell containers drop all capabilities and privilege gains", with the session container engine in place of delegation.
