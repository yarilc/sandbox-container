# Spec Delta

## MODIFIED Requirements

### Requirement: Verified launch engine
After ordinary launch configuration is admitted, the wrapper SHALL verify that the engine used for image operations and container launch reports Linux and rootless operation. Failed or unrecognized verification SHALL stop before image inspection, build, or container creation. Setup SHALL verify the engine after approved user-service preparation and before image operations or smoke container creation. Help and missing-installation refusal SHALL require no engine query.

#### Scenario: Local rootless engine without delegation
- **WHEN** local Podman reports Linux and rootless operation and delegation is disabled
- **THEN** engine verification succeeds without requiring a delegation socket

#### Scenario: Engine cannot be verified
- **WHEN** engine verification fails or reports rootful, non-Linux, empty, or malformed results
- **THEN** the wrapper exits nonzero with an actionable engine error before image operations or launch

#### Scenario: Setup can diagnose missing prerequisites
- **WHEN** interactive setup is requested before Podman or its required user service is usable
- **THEN** it can diagnose prerequisites and offer permitted user-service preparation without normal session preflight
- **AND** no image operation or container creation occurs until the selected engine passes verification

#### Scenario: Unconfigured invocation does not need an engine
- **WHEN** an ordinary offline invocation runs from a checkout without a protected installation and Podman is missing or unavailable
- **THEN** the wrapper reports the setup-required diagnostic without querying an engine

### Requirement: Transparent invocation and terminal handling
The wrapper SHALL start Bash with the selected mounts and identity and forward its arguments to Bash, preserving their order, spaces and empty values. `--container-shell` SHALL be accepted and SHALL behave like an invocation without it. The wrapper SHALL preserve stdin and allocate a TTY only when stdin and stdout are terminals. Restricted invocations SHALL enter through the protected Landlock/seccomp bootstrap before untrusted initialization; arguments, stdin, terminal allocation, signals and exit status SHALL retain the same contract.

#### Scenario: Pipeline invocation
- **WHEN** the wrapper is invoked with redirected stdin and Bash arguments containing spaces or empty values
- **THEN** stdin and arguments reach Bash unchanged without mandatory TTY allocation

#### Scenario: Interactive session
- **WHEN** stdin and stdout are terminals
- **THEN** the wrapper allocates a TTY and forwards an existing `TERM` by name

#### Scenario: Shell invocation
- **WHEN** the same arguments and input are passed with and without `--container-shell`
- **THEN** Bash receives the same arguments and input and the exit status is the same

#### Scenario: Bootstrap rejects preparation
- **WHEN** restricted-mode bootstrap validation or confinement fails
- **THEN** it exits nonzero without executing Bash or a session-controlled initialization hook
- **AND** the wrapper preserves that failure, reports the enforcement stage on stderr, and removes owned setup resources

#### Scenario: Target WSL enforcement
- **WHEN** the session runs on the measured WSL x86_64 target or a locally qualified native Linux/WSL2 x86_64 installation with usable Landlock ABI >= 3 and standard OCI policy
- **THEN** bootstrap preparation supports that ABI without requiring a kernel upgrade or ABI-9 features
- **AND** both required enforcement layers must install before Bash initialization

#### Scenario: Guarded pipeline and terminal
- **WHEN** a supported restricted session receives piped input or an interactive terminal
- **THEN** the bootstrap preserves empty/spaced arguments and input/terminal behavior
- **AND** bootstrap diagnostics do not contaminate Bash stdout

### Requirement: Predictable image operations
The wrapper SHALL build an absent image and refresh it on `--container-build` only with explicit `SANDBOX_CONTAINER_MAINTENANCE=1`, using the Containerfile beside the resolved wrapper script. Without that exact authorization, a required build SHALL fail with maintenance guidance before image acquisition or build. Runtime network mode SHALL NOT grant maintenance authority or imply filtering of host image pulls or build RUN steps. An image-inspection error other than absence SHALL fail without starting a build or container. Build failures SHALL stop launch and preserve the failure status.

#### Scenario: Image absent from an external workspace
- **WHEN** the wrapper is invoked through a symlink outside its repository with explicit unrestricted mode, the image is absent, and maintenance is explicitly authorized
- **THEN** it builds using the Containerfile beside the physical wrapper script

#### Scenario: Inspection failure
- **WHEN** image inspection reports an engine error rather than absence
- **THEN** the wrapper exits nonzero without attempting a build or launch

#### Scenario: Explicit build fails
- **WHEN** `--container-build` is requested with explicit maintenance authorization and the build fails
- **THEN** the wrapper returns the build failure status without creating a session container

#### Scenario: Build requires separate authorization
- **WHEN** an image is absent or `--container-build` is requested without exact maintenance authorization
- **THEN** the wrapper exits before any pull or build with guidance for an operator maintenance invocation
- **AND** unrestricted runtime mode does not implicitly authorize that build

#### Scenario: Restricted setup gates build
- **WHEN** an offline invocation, including the default mode, lacks a protected installation or selects enabled socket delegation
- **THEN** startup fails before image build even with maintenance authorization

### Requirement: Minimal image build context
Automatic and explicit image builds SHALL exclude repository metadata, local credentials and state, caches, and unrelated project files from the build context. The build recipe and explicitly required build inputs SHALL remain available. This filtering SHALL apply when the wrapper is invoked through a symlink or outside its repository.

#### Scenario: Sensitive and unrelated files are excluded
- **GIVEN** a synthetic build context contains Git metadata, shell configuration state, isolated state, environment files, caches, and an unrelated nested file
- **WHEN** the repository's build-context filtering is applied
- **THEN** those files are unavailable to build instructions consuming the context
- **AND** the Containerfile remains available

#### Scenario: Both wrapper build paths use the filter
- **WHEN** an absent image triggers an automatic build or `--container-build` requests a refresh from another working directory
- **THEN** both builds use the filtered context beside the resolved wrapper script
- **AND** build failures retain their existing status and prevent launch

### Requirement: First-user setup and migration guidance
README, wrapper help and setup guidance SHALL identify `--container-setup` as the mandatory first step for offline use. They SHALL explain managed launch, that `offline` is the default mode, the explicit `unrestricted` alternative for direct invocation from a checkout, and that `provider` is not offered. They SHALL state that this wrapper replaces the Claude wrapper as the reference only, so existing Claude installations are unaffected.

#### Scenario: User follows first-run guidance
- **WHEN** a new user reads help or the README
- **THEN** instructions show how to invoke setup and subsequently use its managed launcher
- **AND** explain that an offline session has no external network and no unrestricted fallback is automatic

#### Scenario: Operator migrates an existing direct invocation
- **WHEN** an operator reads the direct-invocation guidance
- **THEN** it gives explicit `unrestricted` examples, including separately authorized maintenance, and states that a direct offline invocation needs a protected installation
- **AND** it does not imply that mode selection proves restricted readiness

### Requirement: Optional session lifetime limit
`SANDBOX_CONTAINER_RUN_TIMEOUT` SHALL set the native engine lifetime of the shell container in whole seconds. When it is unset, empty or `0`, no lifetime limit SHALL apply. Any other value that is not a positive decimal integer SHALL fail with status 1 before engine queries. The limit SHALL be independent of the 20-second shutdown budget.

#### Scenario: Lifetime disabled by default
- **WHEN** `SANDBOX_CONTAINER_RUN_TIMEOUT` is unset
- **THEN** the shell container is created without a lifetime limit

#### Scenario: Lifetime expires
- **WHEN** `SANDBOX_CONTAINER_RUN_TIMEOUT=60` is set and Bash is still running after 60 seconds
- **THEN** the engine stops the shell container
- **AND** the wrapper prints a stderr notice that the session lifetime limit was reached
- **AND** the wrapper exits with the engine client's status (255 on the measured Podman 4.9.3 server), then cleans up owned resources within the shutdown budget

#### Scenario: Session ends before the limit
- **WHEN** Bash exits before the limit
- **THEN** the wrapper propagates its exit status unchanged and prints no lifetime notice

#### Scenario: Invalid lifetime value
- **WHEN** `SANDBOX_CONTAINER_RUN_TIMEOUT` is negative, fractional or non-numeric
- **THEN** the wrapper exits with status 1 and names the variable before any engine query or state creation

### Requirement: Qualification binds agent hardening settings
The qualification identity of a restricted installation SHALL include:
- the agent capability and no-new-privileges settings;
- the selected memory, CPU and process budgets;
- the set of agent and proxy budgets actually enforced, as determined by the controllers the engine reports;
- the session lifetime setting.

A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** a restricted installation was qualified with default budgets and the operator launches with `SANDBOX_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and the shell does not start

#### Scenario: Qualification with matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

#### Scenario: Controller delegation changed after qualification
- **WHEN** an installation was qualified while `cpu` was not delegated and the engine later reports `cpu`
- **THEN** the qualification check reports mismatched evidence and requires requalification

### Requirement: Hardening controls are documented
Wrapper help and the README SHALL document:
- the budget variables, their defaults and accepted formats;
- the lifetime variable;
- the unsafe-workspace override and the refused directories;
- that capabilities are dropped in every mode.

Help SHALL remain side effect free.

#### Scenario: Operator reads wrapper help
- **WHEN** the operator runs `--container-help`
- **THEN** the output lists `SANDBOX_CONTAINER_MEMORY_LIMIT`, `SANDBOX_CONTAINER_CPU_LIMIT`, `SANDBOX_CONTAINER_PIDS_LIMIT`, `SANDBOX_CONTAINER_RUN_TIMEOUT` and `SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE` with their defaults
- **AND** no engine query or state creation occurs

## ADDED Requirements

### Requirement: Offline is the default runtime mode
An ordinary launch with an unset or empty `SANDBOX_CONTAINER_NETWORK` SHALL run in `offline` mode. `unrestricted` SHALL apply only when set explicitly. `provider` and any other value SHALL fail with status 1 before engine queries, state creation or image operations, naming the accepted values `offline` and `unrestricted`.

#### Scenario: No mode selected
- **WHEN** the wrapper is invoked from a protected installation without `SANDBOX_CONTAINER_NETWORK`
- **THEN** the session starts in offline mode and stderr reports `network mode=offline`

#### Scenario: Explicit unrestricted mode
- **WHEN** `SANDBOX_CONTAINER_NETWORK=unrestricted` is set
- **THEN** the session starts with ordinary runtime networking and no guard or proxy

#### Scenario: Provider mode requested
- **WHEN** `SANDBOX_CONTAINER_NETWORK=provider` is set
- **THEN** the wrapper exits with status 1, states that the reference profile declares no authentication method, and performs no engine or image operation

### Requirement: Missing offline installation directs to setup
When an ordinary offline launch, including the default mode, runs from a location without a protected installation, the wrapper SHALL exit with status 1 and an English stderr message naming `--container-setup` and the explicit `unrestricted` alternative. This refusal SHALL precede engine queries, state creation and image/resource operations, and SHALL NOT prompt or run setup.

#### Scenario: First invocation from a checkout
- **WHEN** the wrapper is invoked from its repository checkout without a network mode, interactively or with redirected input
- **THEN** it returns status 1 with the setup-required stderr message and no stdout
- **AND** it creates no state or runtime resources and performs no engine or image operation

#### Scenario: Build and shell options cannot bypass setup
- **WHEN** such an invocation uses shell, build or worktree options, including combinations with `SANDBOX_CONTAINER_MAINTENANCE=1`
- **THEN** it receives the same setup-required refusal before state creation or engine operations
- **AND** maintenance consent does not select a runtime mode

#### Scenario: Dedicated entry points remain reachable
- **WHEN** help, interactive setup or the standalone qualification operation is requested without a network mode
- **THEN** that entry point retains its own argument, terminal, prerequisite and enforcement checks
- **AND** help still takes precedence and qualification still cannot execute a supplied command

## REMOVED Requirements

### Requirement: Actionable missing-setup admission
**Reason**: The reference wrapper defaults to `offline` instead of refusing a launch without a mode.
**Migration**: See "Offline is the default runtime mode" and "Missing offline installation directs to setup". Agent wrappers keep their explicit-mode admission after adopting `sandbox-ref-19`.
