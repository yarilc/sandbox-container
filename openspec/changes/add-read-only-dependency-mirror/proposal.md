# Proposal

> Status: roadmap. Only this proposal exists; design, specs and tasks will
> follow when the open questions below are answered. It builds on
> `simplify-toolchain-provisioning` and
> `replace-podman-delegation-with-session-engine`. The Ansible use case below
> also needs `support-nested-systemd-containers`.

## Why

Toolchains give restricted sessions their compilers, but not the project's
dependencies. In an offline or provider session `mvn package`,
`npm install`, `pip install`, `cargo build` and `go build` cannot reach their
registries, so the operator falls back to an unrestricted session, which is
what the toolchain library was meant to avoid, together with Podman
delegation. When a toolchain that needs a registry is introduced, access to
that registry must be considered as well.

The session container engine adds a second kind of client: nested
containers. Projects that develop Ansible roles and playbooks test them with
Molecule in Rocky Linux 9 and Amazon Linux 2023 containers, where the roles
install rpm packages with `dnf`. The packages come from public repositories
and from repositories on hosts of the operator's local network. Neither an
unrestricted session nor a CONNECT allowlist is acceptable for them.

Sandboxes must never be able to publish. One reason to use them is to keep
the operator's push tokens, variables and private keys away from the agent,
and no channel may let the agent publish with credentials supplied by an
attacker either.

## What Changes

- A trusted read-only dependency mirror, outside agent control, through
  which a session reaches package registries and repositories. It accepts only
  `GET` and `HEAD` without a body. It forwards no client credential
  (`Authorization`, `Cookie` and similar headers are dropped; only a fixed
  header allowlist passes). It verifies upstream TLS itself, with the host CA
  bundle saved by setup.
- Upstreams are URL prefixes, not hosts. An upstream is an identifier, an
  ecosystem and a base URL. The mirror forwards only paths below that base URL
  that belong to the ecosystem's protocol, so other services on the same host
  stay unreachable.
- An `rpm` ecosystem for `dnf` clients, with Rocky Linux 9 and Amazon Linux
  2023 as the reference distributions. The mirror never follows a client's
  mirror list or metalink. Package signature checks stay in the client.
- Upstream profiles: named sets of upstreams.
  - A catalog of reviewed public profiles ships in the protected release, for
    example `rocky9`, `epel9` and `al2023`.
  - Operator profiles live in one private host directory shared by every
    wrapper, like the toolchain library.
  - The operator manages both with `--container-mirror add <catalog-name|file>`,
    `list`, `remove` and `verify [<name>]`. `add` refuses a profile file inside
    a writable session mount. `verify` fetches each upstream's repository
    index and reports the result per upstream.
- Local-network upstreams: an operator profile declares the exact address
  scope of each such upstream. The mirror resolves the name itself and
  connects only to addresses inside that scope, as a versioned, operator-approved
  local exception.
- Profile selection: profiles marked as default are active in every session
  with the mirror. A project activates other profiles only by naming them in a
  workspace file, which the launcher reads strictly (names only, bounded
  size). An unknown name yields a clear notice. The workspace never defines an
  upstream. The active profiles are fixed at launch, and startup reports them
  with their revision.
- Clients:
  - session clients get settings for their ecosystems: a Maven `<mirror>`,
    `npm_config_registry`, `PIP_INDEX_URL`, Cargo source replacement and
    `GOPROXY`;
  - nested containers of the session engine, image build steps included, are
    clients through the network namespace they share with the session. `rpm`
    targets point their `baseurl` at the mirror, typically through the
    repository variables of the test scenario.
- Recipes name the profiles they need (`"registries": ["rocky9"]`), not hosts.
- Offline stays offline: an offline session has neither the mirror nor any
  other channel. The mirror is available in provider mode and in a new
  restricted mode for profiles without authentication methods, such as the
  reference shell.
- Contract update: the mirror keeps the no-decryption guarantee (clients
  speak HTTP to the mirror over the existing session channel, and the mirror
  opens its own verified TLS connection). The network contract states its
  residual channels, for example the request paths seen by the registry.

Decisions already taken during exploration:
- **A CONNECT allowlist of registry hosts is rejected.** An encrypted tunnel
  cannot tell a download from a publish:
  - every host with user accounts (`registry.npmjs.org`, `pypi.org`,
    `github.com`) would be a publishing channel;
  - `proxy.golang.org` fetches modules from arbitrary domains on request;
  - even static hosts would depend on their CDN refusing domain fronting.
  This also holds for distribution repositories: they go through the mirror.
- **Prefetching dependencies from project files is rejected.** It depends on
  how each project expresses its dependencies (`pom.xml`, Gradle scripts, the
  various lockfiles) and is too complex to manage at any level. The mirror
  works at the registry protocol level instead, and package managers keep
  resolving dependencies inside the session.
- **Both public and local-network upstreams.** The project maintains the
  public catalog; the operator defines local-network upstreams.
- **Only the operator defines upstreams**, outside every writable mount.
  Projects select operator-approved profiles by name and never define or
  propose new ones, so the agent cannot grant itself a destination.
- **Operator management comes first:** profiles are managed with one command
  modelled on `--container-toolchain`, shared by every wrapper.
- **No interim path:** test containers get packages only through the mirror,
  not through unrestricted sessions or prepared images that carry them.
- **Windows is in scope:** the Ansible use case must work on the Windows
  Podman machine as on native Linux.

## Capabilities

### New Capabilities

- `dependency-mirror`: the read-only mirror, its ecosystems, the upstream
  profile catalog and operator profiles with their command, profile selection,
  the cache and the per-ecosystem client settings.

### Modified Capabilities

- `network-egress`: the restricted mode with the mirror for profiles without
  authentication methods, the mirror stream on the session channel,
  local-network exceptions for mirror upstreams, the startup report of active
  profiles, and the residual channel disclosure.
- `toolchain-library`: the `registries` recipe field naming profiles.
- `session-container-engine`: nested containers and image builds reach the
  mirror, and nothing else, inside the session's network boundary.

## Impact

- Shared network code: a new trusted component that parses HTTP, a new
  version of the multiplex protocol (a second stream kind next to the CONNECT
  proxy), relay and session changes, budgets and qualification for the
  mirror.
- Setup: mode selection and acknowledgement for the new restricted mode; the
  profile directory, catalog and `--container-mirror` command.
- Launcher: reading the project's profile selection, and reporting the active
  profiles.
- Toolchain catalog recipes gain `registries` and mode-dependent client
  settings.
- Session engine: the nested path to the mirror for containers and build
  steps.
- Windows: the Podman machine needs the same mode, nested clients included;
  its cache lives in the machine.

## Open Questions

- **Credentials for local-network upstreams:** whether any repository needs
  them; if so, the mirror holds them outside the sandbox, and where they are
  stored and qualified.
- **Nested client path:** how nested containers and build steps reach the
  mirror from the engine's network namespace. A fixed loopback address keeps
  repository URLs stable in test scenarios; to verify with a spike on native
  Linux and on the Windows Podman machine.
- **rpm repository layouts:** replacing Rocky's mirror list and Amazon Linux
  2023's `mirror.list` with base URLs, the release-locked paths of Amazon Linux
  2023, and which public profiles the catalog ships.
- **Project selection file:** its name, location and format.
- **Go:** module paths through `proxy.golang.org` need an allowlist of module
  domains, or vendoring, because the proxy fetches arbitrary domains.
- **Mode naming and defaults:** the name of the new restricted mode, and
  whether it becomes the default when installed toolchains declare
  registries.
- **Clients that ignore standard settings:** the mirror configuration of
  Maven 3.9's native transport and of Gradle (init script), to confirm with a
  spike.
- **Performance** of large installs (npm, Maven, `dnf`) through the Python
  mirror and the single multiplexed channel, to measure before fixing budgets.
- **Ecosystem order:** `rpm` now has a driving use case and, like Maven, a
  static layout without link rewriting. Either can validate the architecture
  first; then PyPI, npm and crates.io, with Go last.
