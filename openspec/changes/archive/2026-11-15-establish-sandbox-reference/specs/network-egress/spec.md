# Spec Delta

## MODIFIED Requirements

### Requirement: Mandatory inherited IPC enforcement
Restricted sessions SHALL admit qualifying native Linux and WSL2 x86_64 installations with usable Landlock ABI >= 3, using filesystem confinement plus an additional restrictive in-process seccomp filter before session code. Restrictions SHALL survive descendants. The standard OCI seccomp profile and any active SELinux/AppArmor policy SHALL remain active. Compatibility with SELinux/AppArmor SHALL NOT be guaranteed; their enabled status alone SHALL NOT reject preparation. No ABI-9 feature or kernel upgrade SHALL be required.

#### Scenario: Target WSL kernel
- **WHEN** the measured WSL x86_64 target provides usable ABI 3 and permits both required enforcement layers
- **THEN** restricted preparation does not reject it solely for lacking newer Landlock IPC rights
- **AND** local qualification requires the installation enforcement gate, while measured release support requires separately recorded real-rootless acceptance

#### Scenario: Unsupported or blocked kernel features
- **WHEN** ABI is below 3, required Landlock rules or the additional filter cannot install, or the syscall architecture is unsupported
- **THEN** startup fails before Bash, a session command, the relay or application initialization
- **AND** no privilege addition, replacement/weakened OCI profile, automatic kernel change or unrestricted retry occurs

#### Scenario: Native approvals cannot remove confinement
- **WHEN** a session forks, execs, creates threads or starts a nested Bubblewrap sandbox
- **THEN** all session-controlled descendants retain both enforcement layers and cannot acquire unfiltered external peers
- **AND** another session sharing file state does not gain access to its IPC

#### Scenario: Native Linux with active security modules
- **WHEN** native Linux x86_64 reports SELinux or AppArmor enabled
- **THEN** preparation evaluates actual enforcement and local qualification without rejecting the enabled status alone
- **AND** any policy denial stops preparation without disabling security modules, changing labels or adding privileges

### Requirement: Client compatibility does not establish enforcement
In provider mode, the shared session helper SHALL set consistent uppercase/lowercase HTTP/HTTPS proxy values and narrowly scoped loopback bypasses, clearing conflicting inherited and image defaults including alternate proxy variables. Unsetting or ignoring them SHALL NOT create a direct route. TLS trust SHALL preserve the existing single-file opt-in host CA contract in every mode.

#### Scenario: Client bypass and incompatible transport
- **WHEN** a command clears proxy variables, uses a wildcard bypass, or requires an unsupported transport
- **THEN** direct egress still fails and no automatic direct fallback or TLS relaxation occurs

#### Scenario: Host CA off and on
- **WHEN** an offline session runs with host CA trust unset and then enabled with `1`
- **THEN** the first run has no host CA mount or wrapper CA variables
- **AND** the second has only the read-only bundle at `/sandbox-home/ca/bundle.pem` and the four existing CA variables pointing there

### Requirement: Accurate provider identity documentation
The network contract and the provider documentation of every profile with authentication methods SHALL distinguish CONNECT authorization, SNI binding of the initial and retried TLS 1.3 ClientHellos, and encrypted application routing. They SHALL state that matching SNI does not prove exclusive communication with the provider or prevent encrypted Host changes, shared-service routing, provider-side forwarding or sending data to allowed services. They SHALL name uninspected TLS 1.2 renegotiation as an accepted limitation.

#### Scenario: Operator reviews provider guarantees
- **WHEN** an operator reads the network contract or an agent wrapper's provider documentation
- **THEN** the effective initial and retried ClientHello guarantee and remaining application-level limits are visible
- **AND** ECH/GREASE and unsupported-client failures require explicit compatibility guidance without automatic policy relaxation

#### Scenario: Renegotiation limitation
- **WHEN** an operator reads the network contract or provider security documentation
- **THEN** TLS 1.2 renegotiation is identified as uninspected, with the reason and the absence of TLS decryption stated

### Requirement: Destination-binding acceptance evidence
The reference SHALL keep controlled positive/negative destination-binding evidence through the production guard, relay and proxy on the supported WSL ABI-3 target, driven through the shared session helper with the fixture profile. Parser tests and historical transport passes SHALL remain separate from production acceptance. Real authenticated checks belong to the agent wrappers and SHALL require separate authorization; unavailable checks SHALL be labeled unavailable.

#### Scenario: Controlled shared-address regression
- **WHEN** acceptance exercises two controlled TLS hostnames at one address with certificates valid for the respective names
- **THEN** matching CONNECT/SNI succeeds with certificate verification and the authorized-CONNECT/different-SNI case fails before client bytes reach the upstream
- **AND** a controlled unfiltered positive control demonstrates that the alternate hostname is otherwise reachable at that address

#### Scenario: Regression and compatibility matrix
- **WHEN** a change to the proxy, relay, guard or session helper is assessed before tagging
- **THEN** evidence covers malformed/missing/duplicate/conflicting SNI, non-TLS, ECH, fragmentation, inspection limits/deadlines, concurrency, direct multiplex use, channel/proxy failure, and old-proxy rejection
- **AND** controlled TLS/streaming tests cover the narrow and wide fixture profiles, bad-certificate rejection, CA off/on, and long-lived/WebSocket transport, without real credentials

#### Scenario: Historical observation provenance
- **WHEN** the validation record mentions earlier Claude-specific observations, such as the 2026-11-07 CONNECT followed by Cloudflare SNI and HTTP 403
- **THEN** they stay recorded as history of the imported repository and are not presented as evidence of the reference shell

### Requirement: Single protected agent profile
All agent-specific values used by the shared network sandbox and setup components SHALL come from one data-only agent profile and its policy file. Examples are wrapper and variable names, images, labels, installation and state names, native configuration and credential variables, authentication assistance and policy profiles. The profile SHALL be schema-validated, trusted-path checked and outside session-writable mounts.

#### Scenario: Invalid or unprotected profile
- **WHEN** the profile is missing, malformed, has duplicate or unknown keys, fails field validation, or is reachable through a writable workspace or state mount or an escaped symlink
- **THEN** setup, qualification and restricted startup fail before the session runs, identify the profile, and do not fall back to built-in defaults

#### Scenario: Profile not taken from the workspace
- **WHEN** the current workspace contains a file with the profile's name or layout
- **THEN** the wrapper uses only the profile in its protected installation or checkout and ignores the workspace copy

### Requirement: Residual exfiltration disclosure
For every profile that declares authentication methods, provider help, setup guidance, the README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones, so each allowed host can receive workspace data sent with a foreign key or account. They SHALL name the hosts of each base profile and SHALL NOT present the disclosure or a host reduction as preventing this channel.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract of a wrapper whose profile declares authentication methods
- **THEN** the foreign-credential channel is described for every allowed host of the selected profile
- **AND** the text states that only offline mode removes the channel

#### Scenario: Reference without provider mode
- **WHEN** an operator reads the reference README or network contract
- **THEN** it states that the reference offers no provider mode and that the channel is described by each agent wrapper

## ADDED Requirements

### Requirement: Runtime modes with an offline default
The wrapper SHALL accept `SANDBOX_CONTAINER_NETWORK=offline|unrestricted` and apply `offline` when it is unset or empty. `provider` SHALL be accepted only for a profile that declares authentication methods. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the destination boundary; session-writable configuration SHALL NOT select or broaden it.

#### Scenario: Default and invalid selection
- **WHEN** an ordinary invocation leaves the effective mode unset or empty
- **THEN** it starts an offline session, subject to every offline prerequisite
- **AND** `provider` or an unknown nonempty mode fails with an invalid-mode diagnostic without image operations or session startup

#### Scenario: Policy cannot escalate itself
- **WHEN** workspace settings, application state, or commands request a broader policy or remove proxy variables
- **THEN** the running session retains its operator-selected outer boundary

#### Scenario: Offline operation
- **WHEN** offline mode applies by default, by explicit operator choice or from a validated managed launcher
- **THEN** the wrapper applies all existing restricted platform, protected-installation, guard and qualification requirements
- **AND** the resulting session cannot reach external services

#### Scenario: Explicit unrestricted operation
- **WHEN** an operator explicitly chooses unrestricted mode, or the validated managed launcher supplies that saved choice
- **THEN** the mode retains its existing authority, prerequisite and separate maintenance requirements
- **AND** failed restricted preparation never falls back to unrestricted networking

#### Scenario: Qualification is not an ordinary session
- **WHEN** the standalone fixed qualification operation is invoked with no effective network mode
- **THEN** its existing offline qualification default and protected-fixture checks remain available
- **AND** neither that operation nor its internal probe admits an arbitrary application command or bypasses enforcement

### Requirement: Profiles without authentication methods
The profile loader SHALL accept a profile with no authentication method and without an approval-bypass variable. Its policy file SHALL then declare no policy profiles. For such a profile, the shared session helper, setup and qualification SHALL refuse provider mode before any image, proxy or container operation, naming the absence of authentication methods.

#### Scenario: Reference profile loads
- **WHEN** the reference profile declares `"auth": {}` and no `approval_bypass_env`, with a policy whose `profiles` is empty
- **THEN** the profile and policy load and offline and unrestricted sessions can start

#### Scenario: Provider requested without methods
- **WHEN** provider mode reaches the session helper, setup or qualification with such a profile
- **THEN** the operation fails before image, proxy or container operations and the diagnostic states that the profile declares no authentication method

#### Scenario: Empty policy with declared methods
- **WHEN** a profile declares authentication methods and its policy file declares no profiles
- **THEN** policy validation fails as before

## REMOVED Requirements

### Requirement: Separate Claude authentication profiles
**Reason**: The reference profile declares no authentication method; the `anthropic-api` and `anthropic-account` inventories belong to the Claude wrapper.
**Migration**: The Claude wrapper keeps this requirement in its own specification when it adopts `sandbox-ref-19`. The shared mechanics it relied on are covered by "Profiles without authentication methods" and the fixture-profile tests in `reference-propagation`.

### Requirement: Authenticated account-profile reduction evidence
**Reason**: Account-profile evidence is operator-run against a real Claude account and does not apply to the reference shell.
**Migration**: The Claude wrapper keeps this requirement and its validation history.

### Requirement: Operator-selected runtime modes
**Reason**: The reference defaults to offline and offers provider mode only for profiles with authentication methods.
**Migration**: See "Runtime modes with an offline default".
