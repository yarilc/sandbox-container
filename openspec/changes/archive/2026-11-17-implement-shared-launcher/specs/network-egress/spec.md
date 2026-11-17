# Spec Delta

## MODIFIED Requirements

### Requirement: Credential-free local enforcement qualification
Each restricted installation SHALL pass a bounded credential-free gate through its production launch and guard path before ordinary use. The qualified code identity SHALL include the shared launcher core and the agent launcher part, so a change to either invalidates the report. Required denial checks SHALL have controlled positive controls or demonstrate explicit enforcing syscall rejection. Missing fixtures, unrelated connectivity failure, skipped required checks and unavailable transport evidence SHALL fail qualification.

#### Scenario: Mandatory IP and IPC controls
- **WHEN** offline or provider mode is qualified
- **THEN** the gate verifies direct IPv4/IPv6 denial, no external DNS/UDP path, denial of existing and late external Unix endpoints and host-bind socket publication, and denial of alternate socket families and pair retargeting
- **AND** actual loopback and permitted connected-pair data exchange, descendant enforcement and ordinary caller-owned file persistence succeed
- **AND** controlled host endpoints are reachable by an unconfined positive control when the denial depends on a listening peer

#### Scenario: Provider boundary qualification
- **WHEN** provider mode is qualified
- **THEN** controlled TLS endpoints exercise matching CONNECT/SNI with certificate verification, mismatched-SNI zero-byte rejection, denied authority and fail-closed channel/proxy loss through the production guard, relay and proxy
- **AND** isolated fixture policy and certificates never modify production host inventories, private-address exclusions or CA defaults

#### Scenario: Probe or ordinary smoke is insufficient
- **WHEN** only an ABI query, socket creation result, version query or the previous smoke check succeeds
- **THEN** no successful qualification report is issued
- **AND** ordinary restricted startup remains blocked

#### Scenario: Host kernel without IPv6
- **WHEN** the engine host has no IPv6 support, observed as a missing `/proc/sys/net/ipv6` and `EAFNOSUPPORT` on `AF_INET6` socket creation
- **THEN** the gate uses an IPv4-only positive-control network and peer
- **AND** the IPv6 denial is evidenced by `EAFNOSUPPORT` on `AF_INET6` socket creation in both the unconfined control and the guarded probe
- **AND** every other required check, including the IPv4 positive controls and denials, runs unchanged

#### Scenario: Inconsistent IPv6 evidence
- **WHEN** the detected IPv6 state is neither clearly present nor clearly absent, or the fixture network, peer addresses, control or guarded probe contradict it
- **THEN** qualification fails without a report and without falling back to the other path

#### Scenario: IPv6 state is bound to the report
- **WHEN** a report was issued for one IPv6 state and the host later runs with the other state
- **THEN** the report is stale and restricted startup requires requalification

#### Scenario: Launcher core changed after qualification
- **WHEN** `launcher/core.sh` or `agent/launcher.sh` differs from the one recorded in the report
- **THEN** ordinary restricted startup requires requalification

### Requirement: Single protected agent profile
All agent-specific values used by the shared network sandbox, launcher and setup components SHALL come from one data-only agent profile and its policy file, mirrored for the launcher by the agent launcher part and checked against them. Examples are wrapper and variable names, images, labels, installation and state names, native configuration and credential variables, the in-container application path (`native.exec`), executable temporary storage (`native.exec_tmp`), authentication assistance and policy profiles. The profile SHALL NOT select who builds the runtime image. The profile SHALL be schema-validated, trusted-path checked and outside session-writable mounts.

#### Scenario: Invalid or unprotected profile
- **WHEN** the profile is missing, malformed, has duplicate or unknown keys, fails field validation, or is reachable through a writable workspace or state mount or an escaped symlink
- **THEN** setup, qualification and restricted startup fail before the session runs, identify the profile, and do not fall back to built-in defaults

#### Scenario: Profile not taken from the workspace
- **WHEN** the current workspace contains a file with the profile's name or layout
- **THEN** the wrapper uses only the profile in its protected installation or checkout and ignores the workspace copy

#### Scenario: Obsolete or mistyped launcher fields
- **WHEN** the profile declares `install.runtime_build`, a relative `native.exec` or a non-boolean `native.exec_tmp`
- **THEN** profile validation fails naming the field

### Requirement: Profile-bound restricted identity
The agent profile, its provider policy file, the shared launcher core and the agent launcher part SHALL be part of the protected code identity recorded in local qualification reports, and restricted preflight SHALL require each of them to be a protected file. Any change to one of them SHALL invalidate matching qualification evidence.

#### Scenario: Profile changed after qualification
- **WHEN** the installed profile or provider policy differs from the one recorded in the current qualification report
- **THEN** ordinary restricted launches are refused with setup or requalification guidance

#### Scenario: Writable launcher core
- **WHEN** `launcher/core.sh` or `agent/launcher.sh` in the installation is writable by others or reachable through a writable mount
- **THEN** restricted preflight fails naming the file

### Requirement: Residual exfiltration disclosure
For every profile that declares authentication methods, provider help, setup guidance, the README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones, so each allowed host can receive workspace data sent with a foreign key or account. They SHALL name the hosts of each base profile and SHALL NOT present the disclosure or a host reduction as preventing this channel. The launcher core SHALL print the provider help from the profile and the default policy, so every wrapper names the same hosts its policy allows.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract of a wrapper whose profile declares authentication methods
- **THEN** the foreign-credential channel is described for every allowed host of the selected profile
- **AND** the text states that only offline mode removes the channel

#### Scenario: Reference without provider mode
- **WHEN** an operator reads the reference README or network contract
- **THEN** it states that the reference offers no provider mode and that the channel is described by each agent wrapper

#### Scenario: Help follows the policy
- **WHEN** the fixture agent's default policy lists two hosts for a base profile
- **THEN** `--container-help` names both hosts in the provider disclosure
