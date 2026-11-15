# Spec Delta

## MODIFIED Requirements

### Requirement: Dedicated interactive setup invocation
`--container-setup` SHALL run a dedicated setup operation before normal runtime preflight. It SHALL require an interactive terminal, reject combinations with launch options or shell arguments, and never start an ordinary shell session implicitly. Wrapper help SHALL remain side effect free and describe setup.

#### Scenario: Setup before runtime configuration exists
- **WHEN** an interactive user requests setup with no protected installation or an absent image
- **THEN** the questionnaire and prerequisite diagnosis run without requiring those first
- **AND** setup is not forwarded to Bash

#### Scenario: Unattended or ambiguous invocation
- **WHEN** setup has no interactive terminal or is combined with shell, build, worktree or shell arguments
- **THEN** it fails with usage guidance before mutations or image operations

#### Scenario: Help takes precedence
- **WHEN** wrapper help is requested together with setup and invalid configuration
- **THEN** help succeeds without loading managed preferences, prompting or requiring Podman

### Requirement: Workflow questionnaire with explicit defaults
Setup SHALL explain and collect network mode, state sharing, installation paths, host CA trust and workspace scope. It SHALL offer `provider` and ask for an authentication method only when the profile declares authentication methods, and ask about permission bypass only when the profile declares an approval-bypass variable. First-run defaults SHALL select provider networking with the first method when methods exist, otherwise `offline`, with shared state and disabled optional authority. Saved choices SHALL be offered on rerun.

#### Scenario: First setup choices
- **WHEN** the user reviews first-run defaults with the reference profile, which declares no authentication method and no approval-bypass variable
- **THEN** network options are only offline and unrestricted, and offline is proposed
- **AND** no authentication, residual-exfiltration or permission-bypass question is asked
- **AND** shared host state, isolated fresh state and worktree-parent exposure are explained before selection

#### Scenario: Provider selected
- **WHEN** setup runs with a profile that declares authentication methods, as the shared tests do with the fixture profile
- **THEN** network options also offer provider, the first-run default is provider with the first declared method, and choosing a method selects its protected policy profile without requiring an API key

#### Scenario: Previously saved network mode
- **WHEN** setup is rerun with a saved configuration, including explicit offline mode
- **THEN** the saved network mode remains the proposed choice instead of the first-run default

### Requirement: Optional authority requires deliberate selection
Setup SHALL explain and require explicit selection of unrestricted networking, Podman delegation, permission bypass when the profile declares it, worktree-parent exposure and host CA trust. Delegation SHALL be available only with unrestricted networking. Enabling the host launch service SHALL NOT implicitly grant its socket to the application.

#### Scenario: Restricted networking and delegation conflict
- **WHEN** the user requests delegation while choosing a restricted mode
- **THEN** setup explains the conflict and requires an explicit compatible choice before proceeding
- **AND** it never silently broadens networking

#### Scenario: Launch service without delegation
- **WHEN** setup enables the API service for restricted launch
- **THEN** the saved application delegation setting remains disabled unless separately selected in unrestricted mode

### Requirement: Mode-specific image and guard preparation
Setup SHALL inspect or prepare the runtime image and the additional components required by the selected mode. Restricted modes SHALL receive a validated static guard and digest manifest; provider mode, available only for profiles with authentication methods, SHALL also receive a valid selected policy, private runtime directory and immutable proxy image identity. Existing suitable artifacts SHALL be reused unless refresh is approved.

#### Scenario: Fresh provider setup
- **WHEN** provider setup is approved with no prepared artifacts for a profile with authentication methods
- **THEN** setup prepares the pinned build inputs, toolchain, runtime and proxy images, compiles the guard and validates its manifest and policy
- **AND** launch preferences refer to an inspected immutable proxy image rather than an unresolved local tag

#### Scenario: Offline or unrestricted setup
- **WHEN** setup prepares offline mode, as the reference does by default
- **THEN** it prepares the runtime and guard without requiring a provider proxy image or authentication
- **AND** unrestricted setup requires neither the restricted guard nor provider proxy components

#### Scenario: Preparation fails
- **WHEN** an image build, image inspection, guard compilation or validation fails
- **THEN** setup reports the failed stage and leaves the last working installation selected
- **AND** it does not substitute a different policy, toolchain or network mode

### Requirement: Persistent non-secret managed launch preferences
Setup SHALL save versioned non-secret preferences and provide a managed launcher usable from another workspace without repeated exports. Preferences and launcher code SHALL remain outside application-writable mounts and be validated before use. The launcher SHALL preserve arguments, stdin, terminal handling and current-directory semantics. Direct wrapper invocation SHALL support explicit environment-based runtime modes; an unset or empty effective network mode SHALL follow the wrapper's admission rule, which in the reference is the offline default.

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

### Requirement: Credential-preserving authentication assistance
When the profile declares authentication methods, setup SHALL support reusing selected shared account state or offering an explicit fresh login in isolated state; a profile without methods SHALL skip authentication entirely. It SHALL NOT copy credentials, collect or persist API keys/tokens in setup preferences, or require an API key for account use. Authentication SHALL use the chosen installed sandbox and preserve its selected network and CA policies.

#### Scenario: Fresh account login
- **WHEN** an account user chooses fresh isolated state and accepts login after sandbox validation
- **THEN** setup invokes the profile's login command through the configured sandbox and lets the application persist credentials in that state
- **AND** setup records no token, authorization code or credential-bearing login URL

#### Scenario: API key unavailable
- **WHEN** API mode is selected but no API key is available
- **THEN** sandbox preparation can complete with authentication explicitly pending and instructions for supplying the key through the existing runtime mechanism
- **AND** no paid model request is made automatically

#### Scenario: Reference profile has nothing to authenticate
- **WHEN** setup completes with the reference profile
- **THEN** it offers no login, asks for no key and reports authentication as not applicable

### Requirement: Verified readiness with separate authentication status
Setup SHALL declare the selected sandbox ready only after installed-path checks, engine verification, artifact validation and a smoke launch succeed through the actual selected runtime path. Restricted candidates SHALL additionally pass the installation enforcement gate and publish its protected matching report before activation. Completion output SHALL separately report authentication as verified, pending or not applicable, provide the launch/rerun commands and identify PATH requirements.

#### Scenario: Sandbox smoke check succeeds
- **WHEN** the selected installation passes its smoke check
- **THEN** setup reports sandbox readiness and the resolved managed launch command
- **AND** a version or shell smoke check alone does not imply authenticated provider success
- **AND** with the reference profile the authentication status is not applicable in every mode

#### Scenario: Login or optional authentication check skipped
- **WHEN** the sandbox is usable but authentication was skipped, unavailable or failed
- **THEN** setup reports sandbox ready and authentication pending with the appropriate next command
- **AND** it does not claim a working authenticated model request

#### Scenario: Enforcement check fails
- **WHEN** the restricted gate cannot install required enforcement, fails a required control or cannot publish a protected matching report
- **THEN** setup reports incomplete setup, returns nonzero and does not activate the candidate installation

#### Scenario: Setup repeats qualification after relevant updates
- **WHEN** setup prepares changed kernel, engine/backend, security-policy state, protected enforcement code, container hardening or effective image/policy identities
- **THEN** it reruns qualification for the candidate and preserves the previous activation until successful report publication
- **AND** interruption or failed revalidation never replaces the previous report with an apparent pass

#### Scenario: Local qualification and measured acceptance differ
- **WHEN** a candidate passes locally on a combination without recorded full release acceptance
- **THEN** setup identifies it as locally qualified and not release-measured
- **AND** active SELinux/AppArmor is reported without guaranteeing compatibility or claiming authentication success

### Requirement: Agent profile in the protected installation
Setup SHALL install the agent profile and its policy file, which declares no policy profiles when the agent profile declares no authentication methods, together with the shared sandbox components, validate them in the native installation, and use them as qualification inputs. Rollback SHALL restore the profile matching the restored installation.

#### Scenario: Installation from a checkout
- **WHEN** setup prepares a native installation from a checkout
- **THEN** it copies and validates the profile and policy with the other protected inputs before candidate qualification and activation

#### Scenario: Rollback after failed activation
- **WHEN** setup restores a previous installation after a failed update
- **THEN** the restored profile, policy, code and qualification report belong to the same installation

### Requirement: Saved budgets govern managed launches and verification
The managed launcher SHALL supply the saved budgets and lifetime through `SANDBOX_CONTAINER_MEMORY_LIMIT`, `SANDBOX_CONTAINER_CPU_LIMIT`, `SANDBOX_CONTAINER_PIDS_LIMIT` and `SANDBOX_CONTAINER_RUN_TIMEOUT` when these are absent from the launch environment. An explicitly present variable SHALL take precedence. Setup smoke and qualification SHALL use the saved values for every budget the engine can enforce.

#### Scenario: Managed launch uses saved budgets
- **WHEN** the user launches through the managed command with no budget variables exported
- **THEN** the shell container receives the saved budgets and lifetime
- **AND** a restricted launch matches the qualification report produced by setup

#### Scenario: Explicit override differs from qualified values
- **WHEN** the user exports `SANDBOX_CONTAINER_MEMORY_LIMIT=16g` for a restricted managed launch qualified with `4g`
- **THEN** the override is used and the qualification check stops the launch with requalification guidance

#### Scenario: Smoke verifies saved values
- **WHEN** setup runs its installed smoke check
- **THEN** the smoke compares the effective cgroup limits of every enforced budget with the saved budgets, not with ambient environment values
- **AND** it requires every unenforced budget to be absent

#### Scenario: Setup plan names unenforced budgets
- **WHEN** setup runs on an engine that does not report the `cpu` controller
- **THEN** the setup plan lists the CPU budget as not enforced, with the missing controller, and setup continues without an extra question

## ADDED Requirements

### Requirement: Shared-directory privacy is declared by the profile
The optional boolean agent-profile field `native.private_shared_dirs` (default `false`) SHALL declare that the wrapper requires every shared directory to be private. When it is `true`, setup SHALL check each shared directory before image preparation, as it checks the configuration directory: caller-owned, private and accessible. Setup SHALL NOT report a shared directory as private unless it passed that check.

#### Scenario: Private shared directory required by the profile
- **WHEN** the profile sets `private_shared_dirs: true` and an existing shared directory has group or other permissions
- **THEN** setup fails before image preparation, names that directory and does not change its permissions

#### Scenario: Shared tool settings without the privacy flag
- **WHEN** the profile leaves `private_shared_dirs` unset and an existing shared directory is accessible but not private
- **THEN** setup accepts it as before: shared directories are created privately when missing and must be accessible
- **AND** the setup summary does not call the directory private

#### Scenario: Invalid profile field
- **WHEN** `native.private_shared_dirs` is present but not a boolean
- **THEN** profile validation fails and setup does not start

## REMOVED Requirements

### Requirement: Profile-declared shared-directory privacy
**Reason**: Its scenarios named specific agent wrappers; the behavior is restated neutrally.
**Migration**: See "Shared-directory privacy is declared by the profile".
