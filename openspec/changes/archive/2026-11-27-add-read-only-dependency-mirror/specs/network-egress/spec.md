# Spec Delta

## MODIFIED Requirements

### Requirement: Restricted sessions have no direct external path
Offline sessions SHALL have only their own loopback services. Mirror-enabled sessions SHALL reach approved read-only upstreams through the trusted mirror. Provider sessions SHALL also reach approved CONNECT destinations through the trusted proxy frontend. Restricted sessions SHALL have no direct Internet route or secondary unrestricted attachment and SHALL deny host, LAN, metadata, other sessions, and proxy administration access. Unsupported enforcement SHALL stop startup before the agent runs.

#### Scenario: Direct connection attempts
- **WHEN** a restricted session tries direct IPv4/IPv6 sockets, host aliases, host gateway, private destinations, or a second session
- **THEN** those connections fail independently of client proxy settings

#### Scenario: Host or shared namespace defaults
- **WHEN** engine defaults would share host PID/IPC namespaces or those of another container
- **THEN** the restricted launch explicitly selects private namespaces and exposes no host process or IPC handles
- **AND** the proxy remains outside the agent's PID/IPC domains

#### Scenario: Backend cannot enforce isolation
- **WHEN** the selected rootless backend/version or resource setup cannot establish the required boundary
- **THEN** startup fails with a diagnostic and cleans up owned resources without starting the agent

#### Scenario: Mirror session with no provider
- **WHEN** a qualified mirror session starts with an approved upstream profile
- **THEN** approved dependency reads are reachable through the mirror
- **AND** provider CONNECT, direct external connections and proxy administration are unavailable

### Requirement: External Unix endpoints are denied
Restricted processes SHALL be unable to connect or explicitly send to unapproved external Unix endpoints through mounts or aliases, including sockets created after startup. Mirror and provider modes SHALL each retain only one bootstrap-verified preconnected proxy data channel as an external Unix exception; offline SHALL retain none. A socket's presence in a permitted file mount SHALL NOT authorize its use.

#### Scenario: Host socket exists or arrives in a shared tree
- **WHEN** a host service exposes a stream, datagram, or seqpacket Unix socket in the workspace, worktree parent, shared state or isolated home before or after startup
- **THEN** agent connection and explicit-recipient send operations to it fail
- **AND** renaming, symlinking, hard-linking or using an alternate visible pathname does not authorize that service

#### Scenario: Proxy exception is a preconnected channel
- **WHEN** mirror or provider preparation connects to the verified session frontend before confinement
- **THEN** only that connected policy-filtered data channel survives into the confined relay
- **AND** new connections, socket replacement and channel death cannot broaden access or trigger unfiltered reconnection

#### Scenario: External abstract socket
- **WHEN** an agent attempts to create a Unix socket for an external abstract endpoint
- **THEN** creation is denied independently of pathname permissions or writable settings

### Requirement: Trusted bootstrap and descriptor hygiene
Restricted startup SHALL use a protected native bootstrap that establishes confinement before untrusted loaders, interpreters, environment hooks or settings execute. It SHALL close unrelated inherited descriptors and leave no unconfined agent-side supervisor. Only ordinary validated standard I/O and the confined relay's verified preconnected egress data channel SHALL survive preparation. No other external connected socket, namespace handle or asynchronous I/O capability SHALL reach agent code.

#### Scenario: Early execution or descriptor injection
- **WHEN** image/workspace/state settings attempt pre-policy execution, an unexpected descriptor is inherited, or bootstrap identity/rule installation is invalid
- **THEN** startup rejects the condition or closes the unauthorized descriptor before any agent-controlled sentinel executes
- **AND** connected host sockets cannot bypass the policy through inherited handles, descriptor transfer, or asynchronous I/O paths

#### Scenario: Relay channel for mirror or provider mode
- **WHEN** a restricted startup in mirror or provider mode establishes an egress relay
- **THEN** only ordinary validated standard I/O and the confined relay's verified preconnected egress data channel survive preparation

### Requirement: Bounded multiplexed proxy data transport
Provider mode SHALL carry concurrent independently authorized CONNECT and mirror streams over its sole preconnected channel using a protected versioned protocol. Mirror mode SHALL carry mirror streams over the same protocol and refuse CONNECT streams. Stream, frame, queue and flow-control resources SHALL be bounded. Invalid protocol/state or channel failure SHALL fail closed without policy changes or descriptor transfer. Sequential requests SHALL NOT be limited to a finite preopened socket pool. Absence of incoming frames SHALL NOT expire an established channel; incomplete frames and individual operations SHALL retain finite deadlines. Stream-local failures and recoverable control congestion SHALL preserve unrelated streams on a healthy channel.

#### Scenario: Repeated and concurrent tunnels
- **WHEN** clients open concurrent tunnels or more sequential tunnels than the active concurrency limit
- **THEN** each logical connection independently passes authority, DNS and address checks
- **AND** TLS, streaming, supported WebSockets and backpressure operate within bounded resources

#### Scenario: Malformed transport and channel death
- **WHEN** clients send invalid versions, lengths, stream IDs, state transitions or credits, or the channel dies
- **THEN** affected operations fail closed with bounded sanitized diagnostics and no unfiltered reconnection
- **AND** the protocol exposes neither administration nor host descriptor transfer

#### Scenario: Resume after an idle prompt
- **WHEN** a healthy provider session has no open tunnels and receives no transport frames for longer than 300 seconds
- **THEN** the local proxy listener and original preconnected channel remain available
- **AND** a subsequent approved TLS request succeeds through that same channel without restarting the session
- **AND** inactivity alone imposes no session expiration or periodic traffic requirement

#### Scenario: An idle tunnel expires independently
- **WHEN** an individual tunnel exceeds its idle operation deadline and its peer acknowledges closure normally
- **THEN** that tunnel releases its resources without closing the shared channel or other tunnels
- **AND** a new approved request can use the existing channel

#### Scenario: A partial frame stalls
- **WHEN** a peer starts a frame but does not complete its header and declared payload within the finite frame completion deadline
- **THEN** the channel closes and pending operations terminate
- **AND** incremental partial progress does not extend that deadline indefinitely

#### Scenario: Idle channel loses its peer or is cancelled
- **WHEN** an established channel waiting for a new frame receives EOF, a transport error or session cancellation
- **THEN** its receiver terminates and owned channel resources are released
- **AND** outbound access remains closed without a replacement connection or a broader network mode

#### Scenario: One stream fails while another carries traffic
- **WHEN** a tunnel is cancelled, fails an individual operation, or exceeds its close-acknowledgement deadline while the shared transport remains healthy
- **THEN** its application-facing operations terminate within finite lifecycle bounds
- **AND** another authorized tunnel continues exchanging data and the original relay listener remains usable
- **AND** a subsequent authorized tunnel succeeds on the same channel when stream capacity is available

#### Scenario: Concurrent CONNECT and dependency requests
- **WHEN** a provider session uses both stream types through the same channel
- **THEN** each request passes the policy for its stream type
- **AND** mirror concurrency cannot consume the reserved provider capacity and failed mirror streams release resources without disrupting healthy CONNECT streams

#### Scenario: Stale transport revision
- **WHEN** installed egress components disagree on the supported transport revision or startup identity
- **THEN** restricted egress startup fails before the application executes

### Requirement: Exact destination enforcement outside the agent
For provider CONNECT, a trusted proxy outside agent control SHALL allow only normalized exact policy hostnames and approved ports, normally 443. It SHALL reject unapproved IP literals, wildcard/suffix matches, ambiguous authorities, unsafe ports, and unsupported proxy methods. TLS SHALL remain end-to-end without decryption or disabled certificate verification. Provider tunnels SHALL additionally satisfy mandatory initial TLS server-name binding before client bytes are forwarded upstream.

#### Scenario: Authority validation
- **WHEN** a client requests an approved exact hostname on its approved port
- **THEN** the proxy evaluates it for connection
- **AND** deceptive suffixes, userinfo, malformed authorities, unapproved ports, literals, and wildcard destinations are rejected

#### Scenario: Redirect or tunnel target changes
- **WHEN** an approved HTTPS response redirects the client to an unapproved hostname
- **THEN** a new connection to that hostname is denied
- **AND** a different initial TLS SNI inside an approved tunnel is rejected
- **AND** documentation makes no claim to inspect encrypted paths, payloads, HTTP Host or HTTP/2 authority, domain fronting using matching SNI, or provider-side forwarding

#### Scenario: Verified upstream for mirror requests
- **WHEN** a restricted session makes a dependency mirror request
- **THEN** the trusted mirror enforces the verified HTTPS upstream requirements of the dependency mirror capability

### Requirement: Trusted DNS and connection-time address validation
Only trusted infrastructure SHALL resolve approved upstream names. Each connection SHALL use an address validated against denied IPv4/IPv6 special, private, loopback, link-local, and metadata ranges without a second unchecked resolution. An approved mirror LAN exception SHALL apply only to its exact upstream scope. Restricted agents SHALL have no external DNS, UDP/QUIC, or alternate direct transport path.

#### Scenario: Rebinding and mixed address records
- **WHEN** an approved name resolves or changes to a forbidden IPv4/IPv6 address, including mapped IPv4 or a mixed public/private answer
- **THEN** the proxy refuses that connection without connecting to the forbidden address

#### Scenario: Arbitrary DNS and alternate transports
- **WHEN** a tool sends DNS queries, UDP, QUIC, or traffic to a resolver or unapproved HTTPS destination
- **THEN** the traffic cannot leave the restricted session
- **AND** necessary local name handling does not forward arbitrary agent-selected names upstream

### Requirement: Session-owned egress resource lifecycle
Proxy resources, bootstrap/setup channels, transport endpoints, configuration, and local clients SHALL have unique recoverable session ownership. Setup failure SHALL stop launch and remove only owned resources. Cleanup SHALL share the launcher's bounded shutdown budget and preserve primary exit status. Proxy failure SHALL leave outbound attempts closed without changing mode.

#### Scenario: Concurrent sessions and setup interruption
- **WHEN** sessions with different policies start concurrently or setup is interrupted after resource creation
- **THEN** identities remain distinct and cleanup recovers and removes only the interrupted session's resources

#### Scenario: Bootstrap fails after proxy setup
- **WHEN** confinement or descriptor validation fails after creating the session proxy
- **THEN** no agent code runs, the failure status is preserved, and only owned proxy/setup resources are removed within the shared shutdown budget

#### Scenario: Proxy failure
- **WHEN** the proxy becomes unavailable during a mirror or provider session
- **THEN** subsequent outbound attempts fail and the agent receives no alternate network attachment

### Requirement: Redacted actionable diagnostics
Startup SHALL report mode, selected provider policy profile and revision when applicable, and the active mirror profile names and revisions in mirror-enabled modes. Protected logs SHALL distinguish proxy unavailability, DNS failure, destination rejection, and provider authentication failure when observable. Denial records SHALL contain only bounded sanitized destination/port, session identity, and reason; credentials, token URLs, headers, bodies, and prompts SHALL NOT be logged.

#### Scenario: Malicious diagnostic input
- **WHEN** a rejected request includes userinfo, control characters, authorization data, or a token-bearing URL
- **THEN** logs omit secrets and untrusted raw request content and report a bounded reason without allowing log injection

### Requirement: Credential-free local enforcement qualification
Each restricted installation SHALL pass a bounded credential-free gate through its production launch and guard path before ordinary use. The qualified code identity SHALL include the shared launcher core and the agent launcher part, so a change to either invalidates the report. Required denial checks SHALL have controlled positive controls or demonstrate explicit enforcing syscall rejection. Missing fixtures, unrelated connectivity failure, skipped required checks and unavailable transport evidence SHALL fail qualification.

#### Scenario: Mandatory IP and IPC controls
- **WHEN** offline, mirror or provider mode is qualified
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

#### Scenario: Mirror boundary qualification
- **WHEN** mirror or provider mode is qualified
- **THEN** a protected fixture independently demonstrates an approved read through the production guard, relay and trusted service, and denial of writes, disallowed routes and client credentials at the upstream
- **AND** fixture policy and trust inputs remain isolated from production inputs, mirror and offline modes deny provider CONNECT, and loss of the trusted peer fails closed
- **AND** reports bind the installed mirror implementation, protocol and fixture revisions

### Requirement: Shared restricted session interface
Restricted-session preparation, proxy lifecycle, restricted container arguments and proxy cleanup SHALL be provided by one shared, profile-driven component. Wrappers SHALL invoke it through fixed operations with explicit inputs and outputs. They SHALL NOT re-implement these steps. Its cleanup SHALL use only the remaining launcher shutdown budget and SHALL NOT change the primary exit status.

#### Scenario: Wrapper integration
- **WHEN** a wrapper starts an offline, mirror or provider session
- **THEN** preflight, the guard probe, proxy creation, readiness, hardening verification, guard and relay arguments, and proxy cleanup come from the shared component
- **AND** the wrapper adds only agent-specific command, environment, state and credential options

#### Scenario: Interrupted proxy start
- **WHEN** a signal arrives while the shared component is creating or verifying the proxy
- **THEN** the wrapper terminates that operation, then recovers and removes only the proxy owned by this session within the remaining shutdown budget
- **AND** no agent container is created and the signal status is returned

#### Scenario: Stalled proxy cleanup
- **WHEN** proxy recovery or removal stalls during shutdown
- **THEN** each engine call is bounded by the remaining budget
- **AND** the unconfirmed resource is reported without replacing the primary exit status

#### Scenario: Arguments with special characters
- **WHEN** the agent command or its arguments contain spaces, quotes or newlines
- **THEN** the shared component returns them unchanged as separate arguments

### Requirement: Residual exfiltration disclosure
For every profile that declares authentication methods, provider help, setup guidance, the README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones, so each allowed host can receive workspace data sent with a foreign key or account. They SHALL name the hosts of each base profile and SHALL NOT present the disclosure or a host reduction as preventing this channel. The launcher core SHALL print the provider help from the profile and the default policy, so every wrapper names the same hosts its policy allows.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract of a wrapper whose profile declares authentication methods
- **THEN** the foreign-credential channel is described for every allowed host of the selected profile
- **AND** the text identifies offline mode as starting without any external channel

#### Scenario: Reference without provider mode
- **WHEN** an operator reads the reference README or network contract
- **THEN** it states that the reference offers no provider mode and that the channel is described by each agent wrapper

#### Scenario: Help follows the policy
- **WHEN** the fixture agent's default policy lists two hosts for a base profile
- **THEN** `--container-help` names both hosts in the provider disclosure

### Requirement: Runtime modes with an offline default
The reference wrapper SHALL accept `SANDBOX_CONTAINER_NETWORK=offline|mirror|unrestricted` and apply `offline` when it is unset or empty. `mirror` SHALL require explicit selection or a validated saved operator choice. `provider` SHALL be accepted only for a profile that declares authentication methods. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the destination boundary; session-writable configuration SHALL NOT select or broaden it.

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

#### Scenario: Toolchains or workspace request mirror profiles in offline mode
- **WHEN** the effective mode is offline and a workspace or toolchain names mirror profiles
- **THEN** the session starts without the mirror, relay egress descriptor or external access

### Requirement: Profiles without authentication methods
The profile loader SHALL accept a profile with no authentication method and without an approval-bypass variable. Its policy file SHALL then declare no policy profiles. For such a profile, the shared session helper, setup and qualification SHALL refuse provider mode before any image, proxy or container operation, naming the absence of authentication methods.

#### Scenario: Reference profile loads
- **WHEN** the reference profile declares `"auth": {}` and no `approval_bypass_env`, with a policy whose `profiles` is empty
- **THEN** the profile and policy load and offline, mirror and unrestricted sessions can start

#### Scenario: Provider requested without methods
- **WHEN** provider mode reaches the session helper, setup or qualification with such a profile
- **THEN** the operation fails before image, proxy or container operations and the diagnostic states that the profile declares no authentication method

#### Scenario: Empty policy with declared methods
- **WHEN** a profile declares authentication methods and its policy file declares no profiles
- **THEN** policy validation fails as before

## ADDED Requirements

### Requirement: Mirror request visibility disclosure
Shared help, setup guidance and the network contract SHALL disclose that approved upstreams can observe allowed request paths and timing. They SHALL describe HTTP on the confined loopback endpoint and verified HTTPS from the trusted mirror to each upstream. Documentation SHALL identify offline mode as the option with no external channel.

#### Scenario: Operator reads the mirror network contract
- **WHEN** the operator inspects help or the network contract for a mode using the mirror
- **THEN** the text explains the residual channel through approved requests and preserves the separate description of provider end-to-end TLS when provider mode is available
