# Spec Delta

## ADDED Requirements

### Requirement: Extra variables forwarded by name
`SANDBOX_CONTAINER_ENV_VARS` SHALL list host variable names, separated by whitespace, to forward into the session by name, never by value. An invalid name SHALL stop the launch before any engine or state operation. Unset or empty variables SHALL NOT be forwarded. Reserved names SHALL be skipped with one notice each.

#### Scenario: Listed variable reaches the session
- **WHEN** `SANDBOX_CONTAINER_ENV_VARS="GH_TOKEN"` is set and `GH_TOKEN` has a value
- **THEN** the session receives `GH_TOKEN` by name and the value is absent from engine arguments

#### Scenario: Names reserved by mode
- **WHEN** the list names a variable the launcher or agent part sets, a proxy, CA or restricted setting in a restricted mode, or in provider mode another method's credential variable
- **THEN** that name is skipped with a notice

#### Scenario: Reserved or invalid name
- **WHEN** the list names `HOME`, or names `HTTPS_PROXY` in offline mode
- **THEN** that name is skipped with a notice and the session starts
- **AND** a name such as `1BAD` stops the launch before any engine query

## MODIFIED Requirements

### Requirement: Predictable image operations
The wrapper SHALL build an absent image and refresh it on `--container-build` only with explicit `SANDBOX_CONTAINER_MAINTENANCE=1`, using the Containerfile beside the resolved wrapper script. Without that exact authorization, a required build SHALL fail with maintenance guidance before image acquisition or build. Runtime network mode SHALL NOT grant maintenance authority or imply filtering of host image pulls or build RUN steps. An image-inspection error other than absence SHALL fail without starting a build or container. Build failures SHALL stop launch and preserve the failure status. A build SHALL first pull any missing exact `FROM` base, then run `podman build --pull=never --format docker` without a timeout and with stdin from `/dev/null`, passing a trusted host CA bundle only as the `build-ca` build secret. Every image SHALL carry a `build-inputs-hash` label over its build inputs; a launch SHALL refuse an image whose label does not match the current inputs, with rebuild guidance. `--container-build` with no application argument SHALL validate every launch setting, build, and exit without a session; `--container-git-worktree` and `--container-shell` do not count as application arguments. An image name with whitespace or control characters SHALL be refused before any engine operation.

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

#### Scenario: Build-only operation
- **WHEN** `--container-build` is given with maintenance authorization and no application argument, also together with `--container-git-worktree`
- **THEN** the wrapper validates its settings, builds the image and exits with the build status without creating a container
- **AND** an invalid setting, such as an unusable delegation socket, stops it before the build

#### Scenario: Stale image
- **WHEN** the Containerfile or another build input changed after the image was built
- **THEN** a launch without `--container-build` stops before creation and names the rebuild command

### Requirement: Verified launch engine
After ordinary launch configuration is admitted, the wrapper SHALL verify that the engine used for image operations and container launch reports Linux and rootless operation. Failed or unrecognized verification SHALL stop before image inspection, build, or container creation. Every read-only engine query (`info`, `version`, `ps`, image and container existence and inspection, the delegation socket query) SHALL be bounded by a timeout; `create`, `start`, `build` and `pull` SHALL NOT be. Setup SHALL verify the engine after approved user-service preparation and before image operations or smoke container creation. Help and missing-installation refusal SHALL require no engine query.

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

#### Scenario: Stalled engine query
- **WHEN** a read-only engine query does not answer
- **THEN** the wrapper stops after the query timeout with the query's diagnostic and creates no container

### Requirement: Single-record launch verification response
Launch-engine verification SHALL accept exactly one valid response record, with no terminator or one final LF. Additional records, including empty records or extra trailing LF characters, and any CR character SHALL fail before image operations or container creation. Capture SHALL preserve record boundaries and command failure status; successful-looking output from a failed query SHALL NOT verify the engine. The same capture SHALL serve every read-only engine query.

#### Scenario: Normal response terminator
- **WHEN** a successful engine query emits one valid response with no final LF or exactly one final LF
- **THEN** launch-engine verification accepts the response

#### Scenario: Additional blank or nonblank records
- **WHEN** the engine query emits a valid first record followed by a blank record, additional nonblank record, or multiple trailing LF characters
- **THEN** startup fails with an invalid-engine-response diagnostic before image inspection, build, or creation

#### Scenario: Query fails after emitting valid data
- **WHEN** the engine query emits valid-looking output but exits nonzero
- **THEN** startup fails with the engine-query diagnostic and performs no image operation or launch

#### Scenario: Carriage return in a response
- **WHEN** an engine query response contains a CR character
- **THEN** startup fails with the invalid-response diagnostic

### Requirement: Transparent invocation and terminal handling
The wrapper SHALL start Bash with the selected mounts and identity and forward its arguments to Bash, preserving their order, spaces and empty values, in every network mode. `--container-shell` SHALL be accepted and SHALL behave like an invocation without it. The wrapper SHALL preserve stdin and allocate a TTY only when stdin and stdout are terminals. The session SHALL receive `USER`, `EDITOR=nano` and `VISUAL=nano`, and `TERM`, `COLORTERM`, `LANG` and `LC_ALL` by name when set; unrestricted sessions SHALL also receive `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and their lowercase forms by name when set, and restricted sessions never. Offline and unrestricted sessions SHALL forward no credential variable unless `SANDBOX_CONTAINER_ENV_VARS` lists it in unrestricted mode. Restricted invocations SHALL enter through the protected Landlock/seccomp bootstrap before untrusted initialization; arguments, stdin, terminal allocation, signals and exit status SHALL retain the same contract.

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

#### Scenario: Locale and proxy forwarding
- **WHEN** the host sets `LANG`, `HTTPS_PROXY` and `EDITOR=vim`
- **THEN** an unrestricted session receives `LANG` and `HTTPS_PROXY` by name and `EDITOR=nano`
- **AND** an offline session receives `LANG` but not `HTTPS_PROXY`

### Requirement: Owned container lifecycle
Concurrent sessions SHALL reserve distinct workspace-index names without removing another session's container. The wrapper SHALL clean up only its own container, propagate its process exit code, and forward INT, TERM, and HUP. Naming collisions SHALL be retried within a bounded limit; unrelated creation failures SHALL retain their diagnostics and status. A failed create whose name holds this session's own container SHALL never count as a collision: that container SHALL be removed, or reported as unresolved. Interruption during creation SHALL retain recoverable evidence of session ownership. Each create attempt SHALL set `CONTAINER_NAME` to the reserved name and run with stdin from `/dev/null`; unrestricted sessions SHALL run with `--init`.

#### Scenario: Name collision
- **WHEN** another session reserves the candidate name between enumeration and creation
- **THEN** the wrapper retries a different numeric name without deleting the other container

#### Scenario: Application exits with an engine-like status
- **WHEN** the started application exits with status 125
- **THEN** the wrapper returns 125 and cleans up its own container without treating the application exit as a name collision

#### Scenario: Interrupted session
- **GIVEN** the engine remains reachable for signal delivery and removal
- **WHEN** the wrapper receives INT, TERM, or HUP while attached
- **THEN** it forwards the signal, terminates with the corresponding signal status, and cleans up its owned container
- **AND** shutdown follows the bounded-shutdown contract

#### Scenario: Unrelated creation failure
- **WHEN** container creation fails without a name collision
- **THEN** the wrapper reports the original failure and removes no unrelated containers

#### Scenario: Interrupted creation has recoverable ownership
- **GIVEN** the engine creates a container for this session before the create client returns its ID
- **WHEN** the wrapper receives INT, TERM, or HUP during creation
- **THEN** it attempts bounded recovery and removal using evidence identifying that session's container
- **AND** it does not start the application after the interruption or remove an unrelated container by workspace name

#### Scenario: Own container behind a failed create
- **WHEN** create fails without publishing an ID and the engine reports this session's ownership label for the name
- **THEN** the wrapper returns the create status without retrying and removes that container

#### Scenario: Session name inside the container
- **WHEN** an unrestricted session starts as `<prefix>-3`
- **THEN** it runs with `--init` and `CONTAINER_NAME=<prefix>-3`

### Requirement: Restricted launches require current local qualification
Before ordinary offline/provider application execution, the wrapper SHALL validate a protected successful qualification report matching the current host, engine and enforcement inputs, for the network mode the launcher resolved, including a profile's default mode. Missing or mismatched evidence SHALL stop startup with requalification guidance. A report SHALL NOT replace per-launch engine, protected-path, guard, policy or readiness checks. Unrestricted launches and wrapper help SHALL NOT require this report.

#### Scenario: Changed environment or artifacts
- **WHEN** kernel/boot, engine version/backend/endpoint, effective security-policy state, guard/code, runtime/proxy image identity, hardening, gate revision or selected mode/profile/policy differs from the report
- **THEN** ordinary restricted startup fails before application execution and requests requalification
- **AND** changing environment variables or managed defaults never suppresses that failure

#### Scenario: Matching evidence
- **WHEN** a trusted complete report matches the effective restricted workflow and all per-launch enforcement checks pass
- **THEN** the requested application can start with its existing argument, stdin, terminal and exit-status semantics
- **AND** a locally qualified combination without recorded full acceptance is visibly identified as not release-measured

#### Scenario: Explicit qualification operation
- **WHEN** the operator invokes the dedicated qualification operation without a current report
- **THEN** only the protected gate fixtures run through normal confinement and resource preparation
- **AND** no supplied application command or writable fixture can execute through the report-check exception

#### Scenario: Default mode reaches the qualification check
- **WHEN** a launch leaves `<P>_NETWORK` unset
- **THEN** the qualification check and every Python helper use the mode the launcher resolved from the profile
