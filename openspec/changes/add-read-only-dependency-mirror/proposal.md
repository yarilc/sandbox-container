# Proposal

> Status: roadmap. Only this proposal exists; design, specs and tasks will
> follow when the open questions below are answered. It builds on
> `simplify-toolchain-provisioning`.

## Why

Toolchains give restricted sessions their compilers, but not the project's
dependencies. In an offline or provider session `mvn package`,
`npm install`, `pip install`, `cargo build` and `go build` cannot reach their
registries, so the operator falls back to an unrestricted session, which is
what the toolchain library was meant to avoid, together with Podman
delegation. When a toolchain that needs a registry is introduced, access to
that registry must be considered as well.

Sandboxes must never be able to publish. One reason to use them is to keep
the operator's push tokens, variables and private keys away from the agent,
and no channel may let the agent publish with credentials supplied by an
attacker either.

## What Changes

- A trusted read-only dependency mirror, outside agent control, through
  which a session reaches package registries. It accepts only `GET` and
  `HEAD` without a body. It forwards no client credential (`Authorization`,
  `Cookie` and similar headers are dropped; only a fixed header allowlist
  passes). It contacts only fixed upstreams per ecosystem, chosen by the
  mirror, not by the client, and accepts only the paths of each ecosystem's
  protocol. It verifies upstream TLS itself, with the host CA bundle saved by
  setup.
- A shared cache of fetched artifacts, written only by the mirror. Sessions
  never write it.
- Recipes declare the ecosystems they need by name
  (`"registries": ["maven-central"]`), not hosts. The ecosystem catalog with
  its upstreams lives in the protected release. Sessions with the mirror get
  the client settings of the installed toolchains' ecosystems:
  - a Maven `<mirror>`;
  - `npm_config_registry`;
  - `PIP_INDEX_URL`;
  - Cargo source replacement;
  - `GOPROXY`.
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
- **Prefetching dependencies from project files is rejected.** It depends on
  how each project expresses its dependencies (`pom.xml`, Gradle scripts, the
  various lockfiles) and is too complex to manage at any level. The mirror
  works at the registry protocol level instead, and package managers keep
  resolving dependencies inside the session.

## Capabilities

### New Capabilities

- `dependency-mirror`: the read-only mirror, its ecosystem catalog, the cache
  and the per-ecosystem client settings.

### Modified Capabilities

- `network-egress`: the restricted mode with the mirror for profiles without
  authentication methods, the mirror stream on the session channel, and the
  residual channel disclosure.
- `toolchain-library`: the `registries` recipe field.

## Impact

- Shared network code: a new trusted component that parses HTTP, a new
  version of the multiplex protocol (a second stream kind next to the CONNECT
  proxy), relay and session changes, budgets and qualification for the
  mirror.
- Setup: mode selection and acknowledgement for the new restricted mode.
- Toolchain catalog recipes gain `registries` and mode-dependent client
  settings.
- Windows: the Podman machine needs the same mode; its cache lives in the
  machine.

## Open Questions

- **Public registries or a company repository** (Artifactory/Nexus).
  - Public registries mean a fixed upstream catalog maintained by the project.
  - A company repository is one operator-configured upstream with private
    addresses, so it needs a local exception, and possibly a read-only token
    that the mirror holds outside the sandbox.
- **Go:** module paths through `proxy.golang.org` need an allowlist of module
  domains, or vendoring, because the proxy fetches arbitrary domains.
- **Mode naming and defaults:** the name of the new restricted mode, and
  whether it becomes the default when installed toolchains declare
  registries.
- **Clients that ignore standard settings:** the mirror configuration of
  Maven 3.9's native transport and of Gradle (init script), to confirm with a
  spike.
- **Performance** of large installs (npm, Maven) through the Python mirror
  and the single multiplexed channel, to measure before fixing budgets.
- **Ecosystem order:** Maven first (static layout, no link rewriting) to
  validate the architecture, then PyPI, npm and crates.io, with Go last.
