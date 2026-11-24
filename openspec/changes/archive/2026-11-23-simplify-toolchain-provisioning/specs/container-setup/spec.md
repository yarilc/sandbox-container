## MODIFIED Requirements

### Requirement: Persistent non-secret managed launch preferences
Setup SHALL save versioned non-secret preferences and provide a managed launcher usable from another workspace without repeated exports. Preferences and launcher code SHALL remain outside application-writable mounts and be validated before use. The launcher SHALL preserve arguments, stdin, terminal handling and current-directory semantics. Direct wrapper invocation SHALL support explicit environment-based runtime modes; an unset or empty effective network mode SHALL follow the wrapper's admission rule, which in the reference is the offline default. The saved workspace scope SHALL apply only to session launches: host management commands such as `--container-toolchain` SHALL reach the wrapper with their arguments unchanged.

#### Scenario: New terminal and workspace
- **WHEN** the user invokes the managed launcher in a new terminal from a separate workspace
- **THEN** the saved network, state, service, CA and workspace-scope choices apply without modifying shell startup files
- **AND** the current directory determines the mounted workspace and container working directory

#### Scenario: Explicit environment overrides
- **WHEN** a supported runtime variable is explicitly present in the launch environment
- **THEN** its value, including an empty value, takes precedence over the saved default
- **AND** the effective configuration still passes existing conflict, privacy and enforcement checks

#### Scenario: Unsafe or malformed preferences
- **WHEN** managed preferences are untrusted, invalid or use an unsupported schema
- **THEN** the launcher fails before image operations or container creation without evaluating their contents as shell code

#### Scenario: Invoked dispatcher or alias is writable
- **WHEN** an invocation uses a dispatcher copy or a symlink chain with any entry inside a writable workspace or state mount
- **THEN** launch fails before application execution even if the configured command and final symlink target are protected
- **AND** relative paths and dot-dot components are interpreted with filesystem symlink semantics

#### Scenario: Legacy managed dispatcher needs migration
- **WHEN** an old managed dispatcher cannot identify its actual invocation path to the installed helper
- **THEN** normal launch fails with setup guidance while help and setup remain available
- **AND** setup atomically upgrades the recognized dispatcher without overwriting unrelated command files

#### Scenario: Saved mode supplies launch configuration
- **WHEN** a validated managed launcher supplies saved offline or unrestricted mode and there is no network environment override
- **THEN** the wrapper uses that mode instead of its default
- **AND** existing mode-specific readiness and qualification checks still determine whether an application can start

#### Scenario: Empty network override is not replaced
- **WHEN** an operator explicitly sets `SANDBOX_CONTAINER_NETWORK` to an empty value for a managed launch whose saved mode is unrestricted
- **THEN** the empty value overrides the saved mode and the wrapper applies its offline default
- **AND** it does not silently restore the saved unrestricted mode

#### Scenario: Explicit direct operator workflow
- **WHEN** an operator invokes the wrapper directly with a valid nonempty network mode and its required configuration
- **THEN** it proceeds through existing runtime checks without requiring managed preferences
- **AND** mode selection alone does not authorize maintenance, delegation or restricted qualification

#### Scenario: Toolchain command with the saved worktree scope
- **WHEN** setup saved the worktree scope and the operator runs the managed launcher with `--container-toolchain list`, on Linux or through the Windows entry
- **THEN** the toolchain command lists the library and no session starts
- **AND** a session started by the same launcher still mounts the parent of the current directory

## ADDED Requirements

### Requirement: Setup re-verifies the toolchain library
After setup prepares the runtime image of a new release, it SHALL rerun the check of every installed toolchain whose verified base differs from that release's base, and record the new base for each check that passes. A failed check SHALL NOT fail setup: setup SHALL name the toolchain and its failure, and the toolchain SHALL keep its previous verified base.

#### Scenario: Base changed by an update
- **WHEN** a default toolchain was verified on the previous base and setup installs a release with a new base
- **THEN** setup reruns its check, and new sessions get its default environment without a manual `verify`

#### Scenario: Check fails after an update
- **WHEN** the rerun check of a toolchain fails on the new runtime image
- **THEN** setup completes with its usual result, names the toolchain and the failed check, and new sessions give that toolchain no default environment, with the launcher's usual warning

#### Scenario: Nothing to re-verify
- **WHEN** no toolchain is installed, or every installed toolchain was verified on the new base
- **THEN** setup runs no toolchain check
