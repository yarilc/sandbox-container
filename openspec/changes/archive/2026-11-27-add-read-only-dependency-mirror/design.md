# Design

## Context

See [proposal.md](proposal.md) for the dependency workflows. `network/guard.c`
establishes confinement before `network/relay.py` starts the provider listener.
`network/mux.py` currently opens streams containing CONNECT authorities only.
`launcher/core.sh` places the agent and its private engine in the same network
namespace. `setup/toolchains.py` already validates recipes and builds a
read-only index consumed by the launcher.

## Goals / Non-Goals

**Goals**

- Reuse the confined transport, private launch lifecycle and protected setup.
- Keep the dependency protocol and authorization in trusted code and let
  package managers resolve dependencies and verify their integrity.
- Qualify the same installed boundary for the shell, nested builds and
  systemd targets in the Windows Podman Machine working session.

**Non-Goals**

- Upstream authentication is a roadmap item. Published profiles and operator
  LAN profiles use credential-free reads.
- Separate release work covers Gradle-specific configuration and additional
  public RPM repositories.

## Decisions

### D1. Use a separate mirror stream on the existing channel

Expose `http://127.0.0.1:18081/mirror/<profile>/<upstream>/` on the confined
side. Keep provider CONNECT on port `18080`. Add a typed mirror OPEN to the
versioned transport and reuse its per-stream windows, cancellation and bounded
queues. The trusted peer dispatches by stream type and independently checks
mode, active profile, upstream and request. Reserve capacity for provider
traffic so a set of downloads cannot occupy every provider stream slot. Use a
single protocol revision across relay, proxy, guard, manifest, readiness and
qualification, with a mode and effective policy identity check before exec.

Reusing the installed proxy container and channel keeps one verified external
descriptor and one owned resource lifecycle. A second descriptor or listener
reachable outside the namespace would require a new containment boundary.
The new listener serves HTTP origin-form requests for package clients. The
provider listener keeps its CONNECT protocol and TLS binding.

```text
session and private engine            trusted egress container
dnf / build RUN --> loopback :18081 --> mirror stream --> approved HTTPS prefix
provider client --> loopback :18080 --> CONNECT stream --> provider policy
                      both streams share the verified bootstrap channel
```

### D2. Freeze operator policy before launch

Use a versioned JSON profile containing its name, displayed revision, default
flag and typed upstream records. Store installed profiles together in a
private, native host directory shared across wrappers. Model command dispatch,
path safety and atomic publication on `--container-toolchain`. Validate path
ownership, permissions, symlinks and writable-mount overlap for the library
and imported profiles, including saved parent-worktree and state mounts.
`verify` uses the same trusted outbound checks as the mirror and reports a
protocol-specific index probe for each upstream. The catalog is read from the
protected release. Catalog profiles become eligible after an operator adds
them. Validate both the effective content identity and the named revision.

Read a bounded `.sandbox-mirrors.json` at the workspace root, with exactly a
`profiles` array of names. Read only regular files within the workspace, with
strict JSON and duplicate keys rejected. Merge installed defaults, named
workspace profiles and the `registries` declarations of default toolchains
already eligible for the current runtime, deduplicating the resulting names.
Resolve precedence by sorting installed defaults and eligible tools by name
and preserving workspace and upstream list order.
Warn about unknown names. Reject malformed inputs to mirror-enabled startup.
Capture the active set once, before constructing the read-only egress
snapshot. Expose only the names, revisions and local URLs the clients need.
The profile snapshot keeps policy consistent throughout a running session
while the operator manages the library concurrently.

Keep the toolchain index schema and add optional `registries` for schema 2
recipes. Apply current base and enablement checks before consuming declarations.
Old recipes have an empty declaration and their installation checks stay
offline. Image-only recipes can name profiles without contributing PATH or
environment variables.

### D3. Enforce normalized paths and verified HTTPS at the trusted peer

Use one strict request parser and a per-ecosystem route table. Accept bodyless
`GET` and `HEAD` on configured routes. Reject ambiguous framing, absolute
targets, path traversal and ambiguous encoding before upstream traffic. Build
upstream URLs from the protected base and validated route segments. Allow
only typed query forms required by a supported protocol. Generate upstream
authority and framing and send only approved headers needed for reads. Bound
timeouts, headers and transformed metadata sizes and stream archive bodies.

Use the system trust store or the protected CA bundle selected at setup,
including for LAN HTTPS. Reuse trusted address validation and connect to
the checked peer address with the approved hostname for TLS identity. A LAN
profile declares approved addresses for its exact upstream. Preserve the
existing public-address constraints for public profiles. Accept an upstream
redirect only after applying the approved prefix, path, address and TLS
checks to the new target, with a finite hop limit. The initial adapters can
reject redirects and use reviewed canonical bases. These checks constrain
which requests the mirror can represent even if a caller ignores how the
launcher configured its package manager.

### D4. Validate RPM end to end before adding the other adapters

Map RPM routes to repository metadata and package objects under the approved
base. A split repository can register additional artifact prefixes under the
same upstream ID. Each prefix has its own approved URL and address policy.
Support the relative paths used by `repomd.xml`, including detached
metadata signatures when the repository publishes them. Preserve metadata and
RPM bytes and use the distro or operator-installed signing key. Configure
scenario-specific `baseurl` entries and disable the distro mirror list and
unrelated repositories in the scenario. Select the Rocky Linux 9
BaseOS, AppStream and Extras URLs from the [Rocky repository documentation](https://docs.rockylinux.org/books/admin_guide/13-softwares/).
For Amazon Linux use approved release-and-architecture-specific CDN prefixes.
Resolve the distro's `mirror.list` into a reviewed direct URL during catalog
maintenance. The runtime matches an exact configured release and reports a
missing release profile. The registered `2023.12.20261120` target's DNF logs
show a release-specific `/al2023/core/guids/<guid>/x86_64/` metadata prefix
and package links that resolve under `/al2023/blobstore/` on the same CDN.
Preserve the original path hierarchy below the mirror's local upstream
prefix so DNF resolves those relative links correctly. Map only hash-shaped
RPM objects under the explicitly approved blobstore prefix. Accept the fixed
optional anonymous `instance_id=none` query on that layout and omit it from
the upstream request. The primary metadata and signatures pass through as
published. Use [AWS
versioned repository guidance](https://docs.aws.amazon.com/linux/al2023/ug/deterministic-upgrades.html)
and keep [RPM and metadata signature checks](https://docs.aws.amazon.com/linux/al2023/ug/repo-metadata-signing.html)
in DNF. Public profiles target reviewed repositories with the architecture
and release combinations listed in their catalog entries.

**Podman Machine spike.** The working Codex session is on WSL2 with a
rootless session engine, Podman server 6.2.0 and client 4.3.1. On 2026-11-27 a
Python HTTP fixture bound to `127.0.0.1` in the session served a fixed
`/repodata/repomd.xml` response. These commands used the registered
`localhost/al2023-systemd:1.0.0` image and a short `urllib.request` client with
proxy variables ignored and the response bytes asserted:

```sh
podman run --rm --pull=never --network=host --entrypoint /usr/bin/python3 IMAGE -c PROBE
podman run --rm --pull=never --network=none --entrypoint /usr/bin/python3 IMAGE -c PROBE
podman build --pull=never --network=host --layers=false --tag TEMP_TAG CONTEXT
podman image rm TEMP_TAG
```

The build context's `RUN` executed the same probe. `host` succeeded for both
run and build, `none` returned connection refused, and cleanup succeeded.
Here `host` is the session engine's namespace. This establishes loopback
reachability. The production mirror route is covered separately by the
credential-free gate. Both Rocky Linux 9 and Amazon Linux 2023 target images
include DNF 4.14 and Python 3.9 and have passed their systemd smoke tests.

### D5. Keep each package manager on its protocol-specific routes

- **Maven.** Generate settings with a mirror for all repositories. Serve the
  approved [Maven repository layout](https://maven.apache.org/repositories/layout.html)
  including metadata, plugins and checksums. Use the pinned Maven client's
  native transport in the fixture and document selecting the settings file.
- **PyPI.** Set `PIP_INDEX_URL` to the approved simple endpoint. Adapt the
  [Simple Repository API](https://packaging.python.org/en/latest/specifications/simple-repository-api/)
  HTML and JSON links to local URLs for approved artifact origins. Preserve
  hashes, metadata and compatibility attributes used for distribution selection.
- **npm.** Supply `npm_config_registry` and disable automatic audit requests
  for the mirror configuration. Adapt package metadata tarball URLs to local
  routes with approved origins. Preserve integrity values. Document that
  [lockfiles naming another registry](https://docs.npmjs.com/using-npm/registry.html/)
  require matching reviewed routes or regeneration with the mirror settings.
- **Cargo.** Use Cargo source replacement with a local sparse registry. Serve
  the [index](https://doc.rust-lang.org/cargo/reference/registry-index.html)
  and adapt its download configuration to approved local crate routes.
  Preserve index checksums and downloaded crate bytes.
- **Go.** Set a single local `GOPROXY` with no `direct` fallback. An operator
  profile explicitly approves module path prefixes on segment boundaries.
  Check the canonical module path for version and checksum lookups before
  contacting an upstream that can resolve modules on demand. Provide the Go
  checksum database protocol through approved routes and preserve client
  signature and checksum verification. Keep arbitrary module discovery out
  of the public defaults. See the [Go Modules Reference](https://go.dev/ref/mod).

Generated client settings and rewritten links are conveniences. The trusted
request checks are the authorization boundary even when a client reads a
different configuration. If several sources for an ecosystem are active,
select the first configured compatible upstream in documented profile order
for clients with a single registry endpoint. RPM scenarios select explicit
URLs per distribution and repository. Report selected URLs and alternatives
so the operator can use a different approved source explicitly.

### D6. Bound resource usage, qualification and rollout

Use a private per-session cache on the machine for complete successful
artifact responses. Scope entries to the protected profile revision, upstream
and canonical target, publish complete entries atomically and bound entries,
total space, retention and concurrent transfers. Revalidate mutable indexes
through their approved route. Check budgets and mixed-stream progress with a
fixed large fixture. Range requests can pass without populating the cache.

Offer `mirror` as an explicit restricted setup choice, with no provider login
flow in that mode. Retain existing launch defaults. Ask the operator to
acknowledge that the upstream observes the allowed paths and request timing.
Qualify the new stream using a protected known HTTPS peer through the installed
guard and relay. The fixture carries a positive read, malformed and denied
requests and peer-side evidence of what was forwarded. Exercise the provider
path in the same channel for regression coverage. Bind reports to enforcement
and fixture identities and validate each operator snapshot independently at
launch. Production upstream availability is checked by `--container-mirror
verify` and handled separately from confinement qualification.

## Risks / Trade-offs

- **Availability and protocol drift.** Verify each reviewed prefix and client
  contract independently. Keep repository layouts and releases explicit so a
  change can be tested before the catalog is published.
- **Metadata advertises other origins.** Map only reviewed artifact URLs and
  require every subsequent request to pass the same trusted checks. Preserve
  bytes covered by client integrity checks and fail cleanly on unsupported
  layouts.
- **Shared-channel contention.** Test large concurrent dependency downloads,
  cancellation and healthy provider traffic with bounded buffers and cache.
- **Limited tooling in the working session.** The two DNF targets are already
  installed. Use a deterministic local repository fixture for regression
  tests. Ansible, Molecule and RPM fixture-building tools were unavailable in
  the preflight. Detect prerequisites explicitly and record unavailable
  checks in `docs/validation.md`. A basic DNF check supplies DNF evidence and
  the Molecule scenario supplies orchestration evidence when the controller
  is available.

## Migration Plan

Setup prepares a complete protected release with the matching guard, peer
image, relay and qualification inputs. A newly prepared release qualifies the
selected mode before activation. Operators add named profiles when needed.
The existing setup rollback restores the previous complete release and its
matching qualification. A rolled-back release can use its supported saved
network mode and leave the private mirror library dormant.
