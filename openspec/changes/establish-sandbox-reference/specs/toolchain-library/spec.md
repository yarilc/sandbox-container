# Spec Delta

## MODIFIED Requirements

### Requirement: Shared operator-managed library
The toolchain library SHALL be one host directory shared by all wrappers, `${XDG_DATA_HOME:-$HOME/.local/share}/sandbox-toolchains` unless `SANDBOX_CONTAINER_TOOLCHAINS_DIR` names another absolute path. It SHALL be caller-owned and private (`0700`), and SHALL NOT be, contain or lie inside the workspace, a state directory or the installation. Only the operator's `--container-toolchain` command SHALL change it.

#### Scenario: Default location
- **WHEN** neither `XDG_DATA_HOME` nor `SANDBOX_CONTAINER_TOOLCHAINS_DIR` is set
- **THEN** the library is `$HOME/.local/share/sandbox-toolchains` for every wrapper

#### Scenario: Unsafe library rejected
- **WHEN** the library is group- or world-accessible, owned by another user, or overlaps the workspace, a state directory or the installation
- **THEN** the session launch fails before any container or image operation, naming the library path
- **AND** the toolchain command fails the same way for an unsafe mode or owner, or an overlap with the installation or a state directory

### Requirement: Toolchain command on the host
`--container-toolchain` SHALL be used alone with `add <recipe>`, `list`, `remove <name>` or `verify [<name>]`. It SHALL run on the host without starting a session. `add` with an image source SHALL require exact `SANDBOX_CONTAINER_MAINTENANCE=1` when the image must be pulled. Changes SHALL be serialized by a library lock and applied atomically, so that a reader sees either the previous or the new toolchain and index, never a partial one.

#### Scenario: Pull without maintenance
- **WHEN** `add` needs to pull an image and `SANDBOX_CONTAINER_MAINTENANCE` is not exactly `1`
- **THEN** the command fails naming the maintenance variable, without pulling

#### Scenario: Concurrent changes
- **WHEN** two `--container-toolchain` commands change the library at the same time
- **THEN** they run one after the other and the index lists the result of both

#### Scenario: Replace and remove
- **WHEN** `add` installs a name that already exists, or `remove` deletes one
- **THEN** the old directory is replaced or removed only after the new state is complete, and the index is regenerated

#### Scenario: Required toolchains
- **WHEN** a recipe requires a toolchain that is not installed, or `remove` targets a toolchain that another one requires
- **THEN** the command fails naming the missing or dependent toolchain, and the library is unchanged

### Requirement: Read-only session mount with live updates
Every session SHALL mount the library at `/toolchains` read-only with `nosuid` and `nodev`, unless `SANDBOX_CONTAINER_TOOLCHAINS=0` is set. The launcher SHALL create the library privately when it is missing. A toolchain added or removed on the host SHALL become visible to running sessions without a restart. The mount SHALL add no network, IPC or socket access.

#### Scenario: Toolchain added during a session
- **WHEN** the operator adds a toolchain while an offline session is running
- **THEN** the session can run its check command through `env.sh` without a restart, under the same network restrictions

#### Scenario: Library is read-only for the agent
- **WHEN** a process in the session tries to create, change or remove a file under `/toolchains`
- **THEN** the operation fails

#### Scenario: Mount disabled
- **WHEN** `SANDBOX_CONTAINER_TOOLCHAINS=0` is set
- **THEN** the session has no `/toolchains` mount and no toolchain environment

### Requirement: Session variables are protected from toolchains

A toolchain SHALL NOT set a variable that the session or a wrapper owns. Profile variables are the running wrapper's prefix, configuration, approval-bypass and credential variables, and the agent variables its profile declares; every other protected variable is neutral and the same in every wrapper. `add` SHALL reject both. `launch-env` SHALL fail on a neutral variable in the index, and SHALL leave a profile variable out of the session with one warning naming the toolchain and the variable.

#### Scenario: Other session variables stay protected

- **WHEN** a recipe sets `HOME`, `PATH`, an `LD_` variable, a proxy or CA variable, the profile's configuration variable, or a variable with the wrapper's or the `SANDBOX_` prefix
- **THEN** `add` fails naming the variable as protected

#### Scenario: Agent variable in a recipe

- **WHEN** a recipe sets a variable that the profile declares as an agent variable, or one that starts with a declared agent prefix, for example `FIXTURE_AGENT_MODEL` with the shared fixture profile
- **THEN** `add` fails naming the variable as protected, and the library is unchanged

#### Scenario: XDG variable in a recipe

- **WHEN** a recipe sets `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`, `XDG_RUNTIME_DIR` or another `XDG_` variable
- **THEN** `add` fails naming the variable as protected, and the library is unchanged

#### Scenario: Bus variable in a recipe

- **WHEN** a recipe sets `DBUS_SESSION_BUS_ADDRESS`
- **THEN** `add` fails naming the variable as protected in every wrapper, and the library is unchanged

#### Scenario: XDG variable in an existing index

- **WHEN** the library index lists a default toolchain with an `XDG_` variable
- **THEN** `launch-env` fails with an invalid-environment error, and the session does not start with that variable

#### Scenario: Another wrapper's variable in the shared index

- **WHEN** the shared index lists a default toolchain that sets a variable protected only by the current wrapper's profile, for example its credential or an agent variable, because another wrapper installed it
- **THEN** `launch-env` succeeds without that variable, still emits the toolchain's `PATH` entries and other variables, and prints one warning naming the toolchain and the variable

#### Scenario: Wrapper state location kept

- **WHEN** a wrapper places its state with XDG variables, and default toolchains are installed
- **THEN** new sessions keep the wrapper's XDG values

### Requirement: Agent variables are declared in the profile

The agent profile SHALL be able to declare the variables and variable prefixes that the agent reads, as an optional list. The profile loader SHALL reject an entry that is not a valid variable name or prefix, a duplicate, or an entry that names a neutral protected variable. A profile without the list, such as the reference profile, SHALL keep only the neutral and derived protection.

#### Scenario: Valid declaration

- **WHEN** a profile declares `FIXTURE_AGENT_` and `DISABLE_TELEMETRY`
- **THEN** the profile loads, and both are profile variables for the toolchain library

#### Scenario: Invalid declaration

- **WHEN** a profile declares an entry with a lowercase name, a space, a duplicate, or `PATH`
- **THEN** the profile loader fails naming the field
