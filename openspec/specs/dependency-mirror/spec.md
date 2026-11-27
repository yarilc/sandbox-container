# dependency-mirror Specification

## Purpose

Give restricted sessions read-only access to approved dependency repositories
while retaining operator control of destinations and client package verification.

## Requirements

### Requirement: Operator-managed mirror library
The host SHALL provide `--container-mirror add <catalog-name|file>`, `list`, `remove <name>` and `verify [<name>]` through each wrapper. The private shared library SHALL store only validated, versioned profiles. The protected release SHALL supply the public catalog. Profiles SHALL identify named upstreams by ecosystem and approved HTTPS base URL.

#### Scenario: Catalog profile
- **WHEN** the operator adds a name available in the protected catalog
- **THEN** the profile becomes installed and `list` displays its name, revision and default status
- **AND** `list` identifies other available catalog entries

#### Scenario: Operator profile file
- **WHEN** the operator adds a well-formed profile file outside the writable mounts of the workspace and state, including a widened worktree scope
- **THEN** the command publishes a complete validated profile atomically
- **AND** relative file and Windows drive paths follow the host command's existing context rules

#### Scenario: Repository declares a separate package origin
- **WHEN** an operator profile declares an additional HTTPS artifact prefix for a repository
- **THEN** the profile records the prefix and its own address policy
- **AND** the mirror authorizes package reads only on that prefix's supported artifact routes

#### Scenario: Invalid or writable profile source
- **WHEN** a profile is malformed, mentions an unsupported ecosystem, contains credentials, or resolves into a writable mount
- **THEN** the command reports the cause without any fetch or partial library update

#### Scenario: Removal and verification
- **WHEN** the operator verifies an installed profile
- **THEN** the command probes the index of each upstream using the mirror's outbound policy, reports each result and signals failure if any probe fails
- **AND** removing the profile excludes it from subsequent launches

### Requirement: Launch-time mirror profile selection
In mirror-enabled modes, the launcher SHALL resolve installed default profiles and installed profiles named by `.sandbox-mirrors.json` or eligible default toolchains. The workspace file SHALL have bounded size and exactly one `profiles` array of names. The launcher SHALL validate and snapshot the effective profiles before starting the session.

#### Scenario: Project selection by name
- **WHEN** the workspace requests a profile that is installed but not a default
- **THEN** the profile is active for that launch and startup reports its name and revision

#### Scenario: Unknown or malformed selection
- **WHEN** a selection names an uninstalled profile
- **THEN** the launcher warns and omits that name
- **AND** a malformed or oversized selection, duplicate JSON keys or a selection file outside the workspace fails mirror-enabled startup with a concise diagnostic

#### Scenario: Snapshot isolation
- **WHEN** the workspace selection, the toolchain library or the installed profiles change after launch
- **THEN** the active profiles and upstream identities for the running mirror remain the ones resolved at launch

### Requirement: Read-only requests on approved routes
The trusted mirror SHALL accept only bodyless `GET` and `HEAD` requests on protocol routes under an active upstream's approved base or artifact prefixes. It SHALL generate upstream authority and framing from validated inputs, forward only approved read-related headers and omit all client credentials. It SHALL bound request and response processing and redact rejected input from diagnostics.

#### Scenario: Approved dependency download
- **WHEN** a client requests a permitted object with a bodyless `GET` or `HEAD`
- **THEN** the mirror uses the approved route and returns the corresponding download or head response
- **AND** the upstream receives no caller-supplied authorization, cookie or proxy credential headers

#### Scenario: Method, framing or route rejected
- **WHEN** the client sends a write method, CONNECT, a request body, ambiguous framing, an absolute target, unsafe path encoding or a path outside an active repository's protocol
- **THEN** the mirror rejects it and the upstream receives no request

#### Scenario: Unapproved redirect or embedded link
- **WHEN** upstream metadata or a redirect names another URL
- **THEN** the mirror only permits subsequent requests for explicitly approved origins and protocol paths
- **AND** it refuses redirects that leave the applicable protected policy

### Requirement: Verified mirror upstream connections
The mirror SHALL use verified HTTPS with the system trust store or protected CA bundle selected by setup. It SHALL resolve names on the trusted side and connect to a validated peer address without a second unchecked lookup. A LAN upstream SHALL require an operator-declared address scope and credential-free access for its exact approved host, port and prefix.

#### Scenario: Approved LAN repository
- **WHEN** a LAN upstream resolves within its approved address scope and presents a certificate valid for its configured hostname and trusted CA
- **THEN** the approved read succeeds with the same route checks as for a public upstream

#### Scenario: Address or TLS verification fails
- **WHEN** a public upstream resolves to a denied address, a LAN upstream returns answers outside its scope, or the upstream certificate fails verification
- **THEN** the mirror refuses the connection or request, with no fallback to an unverified transport

### Requirement: Bounded mirror cache
The mirror SHALL limit the space, retention and concurrency of its private cache. Only complete successful artifact responses SHALL be eligible for reuse under the same upstream and policy revision. Mutable repository indexes SHALL be revalidated through the approved route before reuse.

#### Scenario: Repeated artifact request
- **WHEN** the same permitted artifact is requested again under the same session policy
- **THEN** a usable cache entry can serve the same complete bytes without bypassing request authorization

#### Scenario: Failed transfer or policy change
- **WHEN** a response is incomplete, its cache entry has expired, or the policy identity differs
- **THEN** the entry is not returned as a successful download
- **AND** removing or exceeding a cache entry does not bypass repository authorization

### Requirement: RPM repositories with retained signature checks
The mirror SHALL serve RPM repository metadata and packages at local DNF `baseurl` routes. The public catalog SHALL include Rocky Linux 9 and release-specific Amazon Linux 2023 profiles. DNF configuration SHALL retain package signature checks and support metadata signature verification where provided by the repository.

#### Scenario: RPM download from public or LAN profile
- **WHEN** a target selects a compatible configured public or LAN base URL and refreshes DNF metadata
- **THEN** DNF retrieves `repomd.xml`, approved relative metadata, available detached signatures and RPMs through the mirror
- **AND** installing a package still requires the applicable client signature checks

#### Scenario: Release-specific Amazon Linux repository
- **WHEN** an Amazon Linux 2023 target selects its release and architecture
- **THEN** its local base URL resolves to the reviewed upstream for that combination or identifies a missing profile
- **AND** the mirror does not follow a client-supplied mirror list or metalink or silently change the release

#### Scenario: RPM metadata refers to a separate artifact prefix
- **WHEN** a configured release publishes relative RPM links that resolve under its separately approved artifact prefix
- **THEN** DNF can follow those links through the local mirror with the metadata and signature bytes intact
- **AND** the mirror admits only the configured artifact route and applies its connection policy independently

### Requirement: Maven dependency mirror settings
The Maven client settings SHALL mirror configured repositories to an active approved Maven route. The mirror SHALL support repository metadata, plugins, artifacts and their integrity files in the Maven repository layout.

#### Scenario: Maven resolves a build
- **WHEN** Maven uses the generated settings and a fixture build needs an approved plugin and dependency
- **THEN** both resolve through the mirror with checksums intact and no request to a project-defined external repository

### Requirement: PyPI simple repository and distribution files
The launcher SHALL provide an active PyPI route as `PIP_INDEX_URL`. The mirror SHALL support simple repository HTML and JSON responses and rewrite approved distribution links to local routes while retaining integrity and package compatibility metadata.

#### Scenario: pip installs a distribution
- **WHEN** pip resolves a package through the mirror's simple index
- **THEN** it can download the selected approved distribution from a mirror URL and verify its original hash
- **AND** a distribution URL outside the approved artifact origins remains inaccessible

### Requirement: npm registry metadata and tarballs
The launcher SHALL provide an active npm mirror as `npm_config_registry` and suppress automatic audit requests in that client configuration. The mirror SHALL serve approved package metadata and tarballs through local URLs and preserve integrity values.

#### Scenario: npm resolves a scoped package
- **WHEN** npm installs from an approved registry and its metadata refers to an approved tarball
- **THEN** the tarball URL resolves through the mirror and the client verifies its integrity
- **AND** publish and registry audit POST requests are rejected by the mirror

### Requirement: Cargo sparse registry replacement
The launcher SHALL provide Cargo source replacement settings for an active approved sparse registry. The mirror SHALL serve index entries and configure their download endpoint to use local routes while preserving crate checksums.

#### Scenario: Cargo resolves and downloads crates
- **WHEN** Cargo uses the generated configuration to resolve approved dependencies
- **THEN** index entries and crate downloads flow through the mirror and the original checksum remains verifiable

### Requirement: Go proxy requests limited to approved modules
Go client settings SHALL select an approved mirror route as the sole `GOPROXY` and preserve checksum database verification. For upstreams capable of fetching modules on demand, the mirror SHALL require explicitly approved module prefixes and apply them on path segment boundaries to module and checksum lookups.

#### Scenario: Approved module with checksum verification
- **WHEN** Go resolves an approved module using the generated settings
- **THEN** the version, module objects and required checksum data are available on approved routes and client verification remains enabled

#### Scenario: Unapproved module lookup
- **WHEN** a module or a checksum lookup falls outside the approved module prefixes
- **THEN** the mirror rejects the lookup before an upstream request and the client configuration provides no direct fallback
