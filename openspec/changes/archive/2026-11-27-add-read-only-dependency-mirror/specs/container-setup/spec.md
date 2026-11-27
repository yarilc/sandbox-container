# Spec Delta

## MODIFIED Requirements

### Requirement: Workflow questionnaire with explicit defaults
Setup SHALL explain and collect network mode, state sharing, installation paths, host CA trust and workspace scope. When a same-host launch service is reachable or startable, setup SHALL offer explicit `mirror` networking. It SHALL offer `provider` and ask for an authentication method only when the profile declares authentication methods, and ask about permission bypass only when the profile declares an approval-bypass variable. First-run defaults SHALL select provider networking with the first method when methods exist, otherwise `offline`, with shared state and disabled optional authority. Saved choices SHALL be offered on rerun. When no same-host launch service is available, the network choice SHALL follow the rule for setup without a launch service instead.

#### Scenario: First setup choices
- **WHEN** the user reviews first-run defaults with the reference profile, which declares no authentication method and no approval-bypass variable, on a host where a same-host launch service is reachable or can be started
- **THEN** network options are offline, mirror and unrestricted, and offline is proposed
- **AND** the default offline choice asks no authentication, residual-exfiltration or permission-bypass question
- **AND** shared host state, isolated fresh state and worktree-parent exposure are explained before selection

#### Scenario: Provider selected
- **WHEN** setup runs with a profile that declares authentication methods, as the shared tests do with the fixture profile, and a same-host launch service is reachable or can be started
- **THEN** network options also offer provider, the first-run default is provider with the first declared method, and choosing a method selects its protected policy profile without requiring an API key

#### Scenario: Previously saved network mode
- **WHEN** setup is rerun with a saved configuration, including explicit offline mode, and a same-host launch service is reachable or can be started
- **THEN** the saved network mode remains the proposed choice instead of the first-run default

### Requirement: Mode-specific image and guard preparation
Setup SHALL inspect or prepare the runtime image and the additional components required by the selected mode. The runtime image SHALL be built through the wrapper's build-only operation, for every profile. Every mode SHALL also receive the session engine image, built from its digest-pinned base, and the engine seccomp profile derived from the engine host's default profile. Restricted modes SHALL receive a validated static guard and digest manifest; provider mode, available only for profiles with authentication methods, SHALL also receive a valid selected policy, private runtime directory and immutable proxy image identity. Mirror and provider setup SHALL prepare an immutable egress service with the matching protected mirror catalog, trust configuration and qualification inputs. Existing suitable artifacts SHALL be reused unless refresh is approved.

#### Scenario: Fresh provider setup
- **WHEN** provider setup is approved with no prepared artifacts for a profile with authentication methods
- **THEN** setup prepares the pinned build inputs, toolchain, runtime and proxy images, compiles the guard and validates its manifest and policy
- **AND** launch preferences refer to an inspected immutable proxy image rather than an unresolved local tag

#### Scenario: Offline or unrestricted setup
- **WHEN** setup prepares offline mode, as the reference does by default
- **THEN** it prepares the runtime, the guard and the engine image without requiring a provider proxy image or authentication
- **AND** unrestricted setup requires neither the restricted guard nor provider proxy components

#### Scenario: Preparation fails
- **WHEN** an image build, image inspection, guard compilation or validation fails
- **THEN** setup reports the failed stage and leaves the last working installation selected
- **AND** it does not substitute a different policy, toolchain or network mode

#### Scenario: Engine image and profile recorded
- **WHEN** setup prepares any mode
- **THEN** the installation records the engine image identity and the engine seccomp profile, and a later setup reuses them unless their inputs or the engine host's default profile changed

#### Scenario: Fresh mirror setup
- **WHEN** mirror setup is approved on a reference installation with no prepared assets
- **THEN** setup prepares the guard and trusted mirror service and qualifies them through the selected runtime path
- **AND** setup prepares the private profile library and reports authentication as not applicable

### Requirement: Persistent non-secret managed launch preferences
Setup SHALL save versioned non-secret preferences and provide a managed launcher usable from another workspace without repeated exports. Preferences and launcher code SHALL remain outside application-writable mounts and be validated before use. The launcher SHALL preserve arguments, stdin, terminal handling and current-directory semantics. Direct wrapper invocation SHALL support explicit environment-based runtime modes; an unset or empty effective network mode SHALL follow the wrapper's admission rule, which in the reference is the offline default. The saved workspace scope SHALL apply only to session launches: host management commands such as `--container-toolchain` and `--container-mirror` SHALL reach the wrapper with their arguments unchanged.

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
- **WHEN** a validated managed launcher supplies saved offline, mirror or unrestricted mode and there is no network environment override
- **THEN** the wrapper uses that mode instead of its default
- **AND** existing mode-specific readiness and qualification checks still determine whether an application can start

#### Scenario: Empty network override is not replaced
- **WHEN** an operator explicitly sets `SANDBOX_CONTAINER_NETWORK` to an empty value for a managed launch whose saved mode is unrestricted
- **THEN** the empty value overrides the saved mode and the wrapper applies its offline default
- **AND** it does not silently restore the saved unrestricted mode

#### Scenario: Explicit direct operator workflow
- **WHEN** an operator invokes the wrapper directly with a valid nonempty network mode and its required configuration
- **THEN** it proceeds through existing runtime checks without requiring managed preferences
- **AND** mode selection alone does not authorize maintenance or restricted qualification

#### Scenario: Toolchain command with the saved worktree scope
- **WHEN** setup saved the worktree scope and the operator runs the managed launcher with `--container-toolchain list`, on Linux or through the Windows entry
- **THEN** the toolchain command lists the library and no session starts
- **AND** a session started by the same launcher still mounts the parent of the current directory

#### Scenario: Mirror command with the saved worktree scope
- **WHEN** setup saved the worktree scope and the operator invokes `--container-mirror add` through the managed launcher
- **THEN** the management command runs on the host and validates the import against the effective widened workspace and state mounts

### Requirement: Credential-preserving authentication assistance
For profiles with authentication methods in modes using provider authentication, setup SHALL support reusing selected shared account state or offering an explicit fresh login in isolated state; a profile without methods SHALL skip authentication entirely. It SHALL NOT copy credentials, collect or persist API keys/tokens in setup preferences, or require an API key for account use. Authentication SHALL use the chosen installed sandbox and preserve its selected network and CA policies.

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

#### Scenario: Mirror mode skips authentication assistance
- **WHEN** setup runs in mirror mode with a profile that declares authentication methods
- **THEN** it offers no login and asks for no key

### Requirement: Provider residual exfiltration acknowledgement
When provider mode is selected, setup SHALL show a residual-exfiltration notice before authentication questions. The notice SHALL state that the allowed hosts of the selected profile can receive workspace data sent with attacker-supplied credentials. Setup SHALL require explicit acknowledgement. Declining SHALL return to the network-mode choice and SHALL NOT select another mode on the operator's behalf. The acknowledgement is not stored.

#### Scenario: Operator acknowledges the notice
- **WHEN** the operator selects provider mode and acknowledges the notice
- **THEN** setup continues with the authentication question
- **AND** the setup plan and saved preferences are otherwise unchanged

#### Scenario: Operator declines the notice
- **WHEN** the operator selects provider mode and declines the acknowledgement
- **THEN** setup asks for the network mode again, with no mode silently substituted
- **AND** no installation, image or state mutation has occurred

#### Scenario: Rerun or non-provider mode
- **WHEN** setup is rerun with saved provider mode, or offline or unrestricted mode is selected
- **THEN** a provider selection asks for the acknowledgement again
- **AND** offline and unrestricted selections do not show the provider notice

#### Scenario: Operator declines the mirror notice
- **WHEN** the operator selects mirror mode and declines its acknowledgement
- **THEN** setup offers the network choices again before mutating installation, image or state resources

#### Scenario: Operator acknowledges the mirror notice
- **WHEN** the operator selects mirror mode
- **THEN** setup explains that permitted request paths and timing are visible to mirror upstreams
- **AND** setup requires an explicit acknowledgement before preparation

### Requirement: Setup without a launch service offers only unrestricted networking
Before asking for the network mode, setup SHALL check, read-only, whether a same-host Unix launch service answers at `CONTAINER_HOST`, the saved endpoint or the default endpoint, and whether a usable systemd user manager could start one. When neither holds, setup SHALL offer only unrestricted networking, explain why and require explicit confirmation.

#### Scenario: Host without systemd user manager or service
- **WHEN** setup runs where no launch service answers and `systemctl --user` is missing or fails, as in a Podman machine distribution on WSL
- **THEN** setup states that offline, mirror and provider networking need a same-host service and that none is available or startable
- **AND** it asks for explicit confirmation of unrestricted networking and saves the local engine as the launch endpoint

#### Scenario: Local endpoint leaves CONTAINER_HOST unset
- **WHEN** the saved launch endpoint is the local engine
- **THEN** the smoke check and managed launches run Podman without `CONTAINER_HOST`, and the launcher treats an empty `CONTAINER_HOST` or `CONTAINER_CONNECTION` as unset, because Podman treats a set variable as a remote context even when it is empty

#### Scenario: Confirmation declined
- **WHEN** the user declines unrestricted networking in that situation
- **THEN** setup ends with status 1 without changes and explains how to make a service available: start a same-host Podman service, or set `CONTAINER_HOST` to its Unix endpoint, then rerun setup

#### Scenario: Saved restricted mode without a service
- **WHEN** setup is rerun with saved offline networking and no service is reachable or startable any longer
- **THEN** setup does not propose offline, states that the saved mode cannot be kept, and changes to unrestricted only after explicit confirmation

#### Scenario: Service reachable or startable
- **WHEN** a launch service answers at one of the checked endpoints, or a usable systemd user manager exists
- **THEN** setup offers every mode the profile allows, as before

#### Scenario: Explanation names no runtime directory
- **WHEN** setup explains how to make a service available
- **THEN** the explanation refers to the setup guide and names no socket path derived from `XDG_RUNTIME_DIR`
