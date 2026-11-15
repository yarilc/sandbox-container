# container-isolation Specification

## Purpose

Define the outer container's filesystem and authority boundaries and require evidence that distinguishes container isolation from native agent approvals and internal sandbox execution.

## Requirements

### Requirement: Read-only system and caller identity
Sessions SHALL use a read-only container root, `--userns=keep-id`, and the caller's UID/GID. Writable persistent binds SHALL be limited to the selected workspace and state mode, plus the delegated socket when enabled. The host CA exception SHALL remain a read-only single-file mount governed by `host-ca-trust`.

#### Scenario: Ordinary session boundaries
- **WHEN** a session writes to its workspace and attempts to change `/usr`
- **THEN** workspace files belong to the caller and the system write fails
- **AND** a host sentinel outside all selected mounts is inaccessible when socket delegation is disabled

#### Scenario: Worktree expansion
- **WHEN** `--container-git-worktree` selects the immediate physical parent
- **THEN** the entire selected parent is writable as specified by `workspace-mounts`, with no additional inferred Git mounts

### Requirement: Ephemeral constrained temporary storage
Sessions SHALL explicitly provide ephemeral `/tmp`, `/run`, and `/var/tmp` mounts with `rw,nosuid,nodev,noexec`. Limits SHALL be 256 MiB for `/tmp`, 16 MiB for `/run`, and 256 MiB for `/var/tmp`. `/tmp` and `/var/tmp` SHALL permit caller writes with sticky directory mode `1777`. Temporary contents SHALL disappear after container removal. Internal sandbox compatibility SHALL NOT silently relax these options.

#### Scenario: Temporary file lifecycle
- **WHEN** a session writes temporary files in `/tmp` and `/var/tmp` and a new container starts after its removal
- **THEN** both paths accept caller writes but the previous files are absent
- **AND** all three temporary mounts retain `nosuid,nodev,noexec` and their specified limits

#### Scenario: Temporary mounts are explicit
- **WHEN** a shell session is created in shared or isolated state mode
- **THEN** `/tmp`, `/run`, `/var/tmp` and `/dev/shm` are explicitly provisioned, and `/dev` with its `devpts` is left to the engine
- **AND** no writable `/var/log` tmpfs or writable `/dev/shm` is introduced by automatic read-only provisioning

#### Scenario: Execution restrictions apply to both temporary directories
- **WHEN** a session attempts to execute a copied executable directly from `/tmp` or `/var/tmp`
- **THEN** the mount policy prevents direct execution from either directory
- **AND** ordinary temporary file writes remain possible

### Requirement: Engine-provided device mounts allow pseudo-terminals
Every shell container SHALL keep automatic read-only tmpfs provisioning enabled and SHALL NOT mount its own `/dev` or `devpts`, so that the engine provides `/dev` and a `devpts` that allows pseudo-terminals. It SHALL mask `/dev/shm` with an empty read-only tmpfs. Automatic provisioning SHALL add no writable path beyond the explicit temporary mounts and the engine's `/dev`.

#### Scenario: Terminal attaches on an engine that mounts /dev read-only
- **WHEN** an interactive session starts with a terminal on Podman 5 with crun 1.27
- **THEN** the terminal attaches and the shell starts without any host configuration change
- **AND** `/dev/pts` is present and `/dev/shm` is read-only and empty

#### Scenario: Pseudo-terminals are available to tools
- **WHEN** a process inside the session opens a pseudo-terminal, as an interactive tool run in the shell does
- **THEN** the allocation succeeds through `/dev/ptmx` and returns a terminal under `/dev/pts`

#### Scenario: Device masks stay empty and read-only
- **WHEN** a process inside the session lists or writes `/dev/shm` or `/run/secrets`
- **THEN** both are empty and the write fails

### Requirement: Standard runtime security policy
The wrapper SHALL NOT add privileged execution, extra capabilities, replacement or weakened OCI seccomp profiles, disabled SELinux labels, or automatic host bind relabeling. Restricted sessions SHALL additionally apply unprivileged Landlock filesystem confinement and an additional restrictive in-process seccomp filter through a protected bootstrap while preserving those standard runtime policies. Policy failures SHALL remain visible with actionable guidance rather than triggering an automatic security-policy bypass.

#### Scenario: SELinux denial
- **WHEN** host policy denies a workspace, state, or socket bind
- **THEN** startup reports the engine failure without adding relabel options or disabling labels

#### Scenario: Internal sandbox denied by policy
- **WHEN** a Bubblewrap sandbox started inside the session cannot execute under the standard container policy
- **THEN** the failure is recorded without automatically broadening container privileges or weakening either seccomp layer or tmpfs policy

#### Scenario: Required enforcement is unavailable under the standard policy
- **WHEN** the kernel lacks the required ABI-3 filesystem features or the existing seccomp/SELinux policy blocks either enforcement layer
- **THEN** restricted startup fails before session-controlled code executes
- **AND** no replacement seccomp profile, disabled label, added privilege, or automatic host policy change is used to make it work

#### Scenario: Confinement persists across execution modes
- **WHEN** a restricted session starts Bash, a command passed to the wrapper, or descendant tools
- **THEN** inherited Landlock and additive seccomp restrictions cover them before their initialization
- **AND** live writable workspace/state binds grant ordinary file access without granting external Unix services or new Unix listeners or unconnected Unix sockets

### Requirement: Evidence-based isolation documentation
Documentation SHALL distinguish internal sandboxing, filesystem isolation, network egress enforcement, and socket authority. A validation record SHALL identify environment and versions and label checks as passed, failed, or unavailable. A sandboxed tool operation and its expected output SHALL be verified before claiming internal sandbox compatibility; executable availability or exit status alone SHALL NOT establish it.

#### Scenario: Synthetic runtime checks
- **WHEN** automated boundary checks run
- **THEN** they use synthetic state without real credentials and check external sentinels, ownership, state persistence, and temporary storage

#### Scenario: Sandbox operation unavailable or unsuccessful
- **WHEN** an internal sandbox check cannot run or fails to produce the expected result
- **THEN** the validation record reports unavailable or failed rather than passed, even if `bwrap` probes succeed or the command exits zero

#### Scenario: User reviews access boundaries
- **WHEN** the user reads the README
- **THEN** it explains shared-state write access, parent/worktree expansion, and socket-enabled host mounts beyond the workspace and identifies offline enforcement, explicit unrestricted networking, and why the reference offers no provider mode

### Requirement: Restricted containers have no capabilities or privilege gains
Offline/provider session containers and session egress proxy containers SHALL drop all Linux capabilities and enable container-level no-new-privileges. Required hardening SHALL preserve caller identity, standard OCI seccomp, active host security policy and existing mount restrictions. Failure to apply it SHALL stop startup without a weaker retry.

#### Scenario: Restricted agent starts in either state mode
- **WHEN** an offline shell session starts with shared or isolated state
- **THEN** its container drops all capabilities and enables no-new-privileges before the bootstrap executes
- **AND** caller-owned persistence, guard enforcement and allowed local IPC continue to work

#### Scenario: Provider proxy starts without capabilities
- **WHEN** the shared session helper starts a session proxy for a profile that declares authentication methods, as the shared tests do with the fixture profile
- **THEN** it has no capabilities and cannot gain privileges across execution
- **AND** its caller-owned transport socket, protected configuration, readiness identity and bounded diagnostic writes remain usable

#### Scenario: Engine or host policy rejects hardening
- **WHEN** required hardening cannot be applied or prevents a required startup operation
- **THEN** startup fails with an actionable diagnostic and removes only owned resources
- **AND** it adds no capabilities, disables no security policy and never retries unrestricted

#### Scenario: Unrestricted behavior is preserved
- **WHEN** the operator explicitly selects unrestricted networking
- **THEN** the shell container receives the same capability, no-new-privileges and resource-budget settings as restricted sessions
- **AND** no egress proxy, guard or network restriction is added to that session

### Requirement: Agent containers have explicit resource budgets
Every shell container SHALL be created with a memory limit, a CPU limit and a process limit for each budget whose cgroup v2 controller (`memory`, `cpu`, `pids`) the verified rootless engine reports as available. The defaults are 4 GiB memory, 2 CPUs and 512 processes. `SANDBOX_CONTAINER_MEMORY_LIMIT`, `SANDBOX_CONTAINER_CPU_LIMIT` and `SANDBOX_CONTAINER_PIDS_LIMIT` SHALL override them. No value SHALL disable a budget; only a missing controller leaves it unenforced.

#### Scenario: Default budgets
- **WHEN** a session starts with none of the budget variables set on an engine reporting the `cpu`, `memory` and `pids` controllers
- **THEN** the container is created with 4 GiB memory, 2 CPUs and 512 processes

#### Scenario: Operator overrides budgets
- **WHEN** the operator sets `SANDBOX_CONTAINER_MEMORY_LIMIT=8g`, `SANDBOX_CONTAINER_CPU_LIMIT=1.5` and `SANDBOX_CONTAINER_PIDS_LIMIT=1024` on an engine reporting all three controllers
- **THEN** the container is created with exactly those limits

#### Scenario: Invalid or unbounded budget value
- **WHEN** a budget variable is empty-but-set with whitespace, zero, negative, `-1`, `max`, non-numeric, or has an unsupported unit
- **THEN** the wrapper exits with status 1 and names the variable before any engine query, state creation or image operation

#### Scenario: Controller not delegated
- **WHEN** the verified engine does not report the `cpu` controller
- **THEN** the container is created without a CPU limit, while the memory and process limits are still applied when their controllers are reported
- **AND** the session continues and prints a notice naming the unenforced CPU budget and the missing controller

### Requirement: Resource budgets are verified, not assumed
Before starting the application, each launch SHALL inspect the created agent container and require each enforced budget to equal its selected value and each unenforced budget to be absent. Setup smoke and restricted qualification SHALL verify the effective cgroup v2 limits inside the agent container in the same way. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine ignores a budget
- **WHEN** the created container reports no limit or a different limit for a budget whose controller the engine reports as available
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names rootless cgroup v2 controller delegation

#### Scenario: Effective limits are measured
- **WHEN** setup smoke or the restricted qualification probe runs inside the agent container
- **THEN** it reads the container's cgroup v2 `memory.max`, `pids.max` and `cpu.max` for every enforced budget and requires them to match the selected budgets
- **AND** for every unenforced budget it requires the controller interface to be absent or unlimited

#### Scenario: Budgets do not bound persistent storage
- **WHEN** the operator reads the README or wrapper help
- **THEN** it states that the budgets and tmpfs sizes do not limit workspace or state storage growth

### Requirement: Engine default secrets mount is masked
Every agent container, every provider proxy and every qualification gate container SHALL be created with an empty read-only tmpfs at `/run/secrets`, so that an engine default mount there (such as RHEL subscription secrets from `mounts.conf`) is neither visible nor writable. The sandbox SHALL NOT require host configuration changes to achieve this.

#### Scenario: Host with a default secrets mount
- **WHEN** the engine's `mounts.conf` maps `/usr/share/rhel/secrets` to `/run/secrets`
- **THEN** the agent container has exactly one mount at `/run/secrets`, an empty tmpfs mounted read-only
- **AND** no host subscription file is readable inside the container

#### Scenario: Host without a default secrets mount
- **WHEN** the engine adds no mount at `/run/secrets`
- **THEN** the agent container still has the empty read-only tmpfs there, and the session behaves as before

### Requirement: Every shell container drops capabilities and privilege gains
Every shell container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in all network modes and with Podman delegation. The wrapper SHALL NOT add a capability back to resolve an incompatibility. A tool that needs a capability SHALL be documented as unsupported.

#### Scenario: Unrestricted shell session starts
- **WHEN** an explicitly unrestricted shell session starts with shared or isolated state
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Delegated Podman client works without capabilities
- **WHEN** an unrestricted session with exact `SANDBOX_CONTAINER_PODMAN=1` runs `podman info` and creates a child container through the mounted socket
- **THEN** the client succeeds without capabilities in the shell container
- **AND** the documentation states that the socket still grants host engine authority beyond these limits

#### Scenario: Incompatible tool is documented, not re-privileged
- **WHEN** a tool inside the session fails only because capabilities or privilege gains are unavailable
- **THEN** the wrapper adds no capability and does not disable no-new-privileges
- **AND** the limitation is recorded in the validation record

### Requirement: Shell options do not weaken the network boundary
The reference wrapper SHALL expose no approval-bypass control. Socket access SHALL require exact `SANDBOX_CONTAINER_PODMAN=1` and explicit unrestricted network mode, independently of state mode, worktree scope and the command passed to the shell. Restricted modes SHALL reject exact socket opt-in.

#### Scenario: Delegation combinations in either state mode
- **WHEN** unrestricted mode is selected with and without exact Podman opt-in, in shared and isolated modes
- **THEN** only exact Podman opt-in determines delegation mounts and variables

#### Scenario: Shell commands cannot change egress
- **WHEN** an offline session runs a command passed to the wrapper or an interactive Bash shell
- **THEN** offline restriction still applies
- **AND** exact socket opt-in rejects startup in either state mode

#### Scenario: Agent approval variable has no effect
- **WHEN** `CLAUDE_YOLO` or another agent's approval variable is set in the caller environment
- **THEN** the wrapper ignores it and passes no permission-bypass argument to Bash
