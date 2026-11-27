# Network policy contract

## Dependency mirror

Explicit `mirror` mode serves operator-approved read-only dependencies through
`http://127.0.0.1:18081/mirror/`. The trusted service opens verified HTTPS
connections to the configured repositories. Approved upstreams can see the
requested paths, allowed read headers and timing. Provider mode also offers
this endpoint and keeps its end-to-end CONNECT tunnels. Offline mode starts
without either channel.

A nested container or build step uses `--network=host` to join the session
engine's network namespace and reach the confined listener. The private
profile library and upstream trust inputs stay in the operator's installation.

This contract is shared by the reference shell and the five agent wrappers.
`sandbox-container` took over the reference role from `claude-container`; the
status, evidence and maps below were recorded while Claude held it. The
reference shell profile declares no authentication method, so this repository
offers no provider mode; the provider sections describe the shared code, which
the shared tests exercise with the fixture profile and each agent wrapper ships.

Status: mandatory implementation/acceptance complete; specifications synchronized
and change archived as `2026-11-07-add-enforced-network-egress` following
the IPC design revision. IP-only tests passed, but an unapproved workspace Unix
socket bypassed that candidate, now replaced by mandatory native confinement.
The ABI-3 guard and multiplexed proxy are integrated; evidence and remaining
authenticated compatibility gaps are recorded separately.
See [the validation record](validation.md). A real account request using existing
OAuth credentials, fresh isolated login, saved-credential reuse and automatic
refresh after expiry passed in operator-reported checks. Real-key API access
remains unverified.
API-key support remains implemented with mandatory synthetic coverage; the
separately authorized real-key check is optional and unavailable without a key,
and does not block this change or account use. It is not counted as a passed
real-provider test.

The durable contract is [network-egress](../openspec/specs/network-egress/spec.md).
The [archived change](../openspec/changes/archive/2026-11-07-add-enforced-network-egress/)
retains the design, delta specifications, completed tasks and optional real-key
API check.

## Portable behavior

| Mode | Agent access | Session container engine (library images) |
| --- | --- | --- |
| unset/empty effective mode | Agent wrappers: ordinary launch stops with setup guidance. Reference shell: `offline` | As the selected mode |
| `offline` | Own loopback, pipes and fixed-peer socket pairs only | No external path; library images only |
| `provider` (profiles with authentication methods) | Loopback/pipes/pairs and preconnected exact-destination proxy | The session's proxy policy; library images only |
| `unrestricted` (explicit only) | Ordinary runtime networking | The session's network; may also pull |

Host Podman delegation was removed in every mode: an exact `<P>_PODMAN=1`
stops the launch with migration guidance. The engine shares the session's
network namespace, so its containers inherit the boundary of the mode.

New users first run the wrapper with `--container-setup`, then use its managed
launcher, which supplies validated saved preferences. Explicit operator modes
remain supported for manual installations and maintenance. In the agent
wrappers a missing/empty ordinary mode stops before runtime checks, engine
queries and state creation, and a managed empty override is preserved and
refused; the reference shell applies `offline` instead and refuses `provider`
because its profile declares no authentication method. No working-directory
configuration is discovered. Offline sessions have no external network.
Standalone qualification retains its offline default and fixed protected controls;
it cannot launch an arbitrary command. Maintenance consent never selects a mode.

Unknown modes fail before image operations. Restricted setup errors never retry
with unrestricted networking. Operator configuration selects the outer policy;
workspace/application settings, native approvals, YOLO, and shell mode cannot
broaden it. Restricted agents have no direct route, external resolver, UDP/QUIC,
host/LAN/metadata access, lateral session access, or proxy administration access.

## Required kernel and IPC boundary

Restricted agent and session proxy containers drop all capabilities and enable
container-level no-new-privileges before code executes. Caller identity,
keep-id user namespaces, standard OCI seccomp, host security policy and mount
restrictions remain unchanged. Hardening rejection stops preparation without
adding privileges or retrying with unrestricted networking. Explicit
unrestricted launches receive the same agent capability drop, no-new-privileges
and resource budgets, but no egress proxy, guard or network restriction.
Agent memory, CPU and process budgets, the set of budgets actually enforced, the
mechanism enforcing the process budget (cgroup, process rlimit or none) and the
optional lifetime are part of the qualification identity: changing them
requires requalification.

Every session proxy has budgets of 128 processes and 256 MiB memory, enforced
for each controller (`pids`, `memory`) the rootless engine delegates; a budget
whose controller is not delegated is not requested and is announced. Without
`pids`, the process budget falls back to a process rlimit of 128 on engine
kernels from Linux 5.14, like the agent's. On that fallback the first process of
the agent, the proxy and the session engine sets the limit inside the
container, through a fixed `/bin/sh` step or the engine's startup program, and the
engine applies no process rlimit: one applied at creation counts every
container of the user. `podman exec` processes get the engine's default
limits; only trusted host-side checks start them. With the fallback, the
machine as a whole is bounded only by the user's own process limit. Provider
startup verifies configured and effective cgroup v2 limits, or under the
fallback the proxy's step and its effective process rlimit, plus actual proxy
hardening before agent execution: an enforced limit must be exact and an
unenforced one absent. An unknown cgroup layout, an unverifiable controller list
or an ignored delegated limit blocks preparation. Proxy failure or exhaustion
leaves outbound access closed and retains bounded owned cleanup and primary
application/signal status. Per-session budgets do not replace multiplex/TLS
inspection bounds.

Both restricted modes require a protected static native bootstrap before any
application, interpreter, relay or shell initialization. Native Linux and WSL2
x86_64 require usable Landlock ABI >= 3, rootless same-host Unix Netavark/Podman
>= 4.9, standard OCI seccomp and the complete local qualification gate. Exact
kernel/server pins and upper version bounds do not determine admission. The
previous WSL 6.6.87.2 / server 4.9.3 results remain measured evidence. SELinux and
AppArmor may stay enabled without guaranteed compatibility; policy failures stop
startup without weakening them. An ABI query or mock pass alone is insufficient.

The bootstrap sets no_new_privs, installs ABI-3 MAKE_SOCK/REFER filesystem rules,
and stacks a restrictive native x86_64 seccomp filter on the standard OCI profile.
SELinux, noexec tmpfs and ordinary rootless privileges remain unchanged. Deny new
socket families except IPv4/IPv6 (contained by private network=none), including
Unix, VSOCK and Netlink. Permit only connected AF_UNIX stream/seqpacket pairs;
deny retargetable datagram/raw pairs, compat/x32 syscall ABIs, io_uring operations
and pidfd_getfd. A failed rule/filter installation stops before agent code.
Never replace/weaken the OCI profile or retry unrestricted automatically.
The bootstrap also rejects every nested mount below the private `/tmp`, `/run`
and `/var/tmp` roots, except the engine's `/run/.containerenv` file, the
provider's verified `/run/sandbox-egress`, and `/run/secrets` only as a
read-only tmpfs. The wrapper, proxy and qualification gate mount that empty read-only tmpfs at
`/run/secrets` so engine default mounts there (RHEL `mounts.conf` subscription
secrets) are skipped; a writable `/run/secrets` still stops startup.

Provider mode retains exactly one bootstrap-verified preconnected data channel
to its protected session proxy; offline retains none. A versioned bounded
multiplex protocol supports repeated/concurrent independently authorized tunnels.
The relay is confined, no unfiltered supervisor remains, and neither proxy nor
protocol sends host descriptors or exposes administration. The guard stays as
the container's confined init: it runs the application as a child in the
terminal's foreground process group, forwards the signals sent to it, reaps
orphans, exits with the application's status, and holds neither the data FD
nor standard input and output. Channel death fails
closed and requires a new session; no finite one-shot socket pool or reconnect
exception is permitted. Close the data FD before executing the application branch.
An established channel does not expire merely because no frames arrive: an idle
prompt needs no heartbeat or reconnect. After the first frame byte, header and
payload completion share an absolute 10-second deadline. Stream idle operations
remain bounded at 300 seconds and tunnel lifetimes at 12 hours; ordinary tunnel
expiry and missing close acknowledgement preserve a healthy session channel.
The caller waits at most ten seconds for acknowledgement after CLOSE transmission;
compact closing records occupy the existing 64-stream budget until remote CLOSE.
Exhaustion refuses new local opens while existing healthy tunnels continue. Late
frames retain state/credit checks; discarded DATA receives no new credit. A
64-entry control queue, one sender and at most 64 shared stream-close tasks bound
closure work. Temporary queue saturation applies bounded backpressure outside
stream locks; queue admission, writer-lock acquisition and drain share an
absolute 30-second control-write budget. Sustained write failure closes the
channel; recoverable congestion alone does not. EOF, incomplete
frames, protocol errors and actual proxy loss continue to fail closed.

External pathname/abstract Unix services stay inaccessible regardless of mount,
alias, socket type or creation time. **New named Unix services and unconnected Unix sockets are denied everywhere,
including private tmpfs.** Existing connected pairs may have inert private names,
but cannot become listeners, retarget or publish on host binds. Preserve own-loopback services, pipes and
fixed-peer connected stream/seqpacket pairs. Verify attempts to retarget those
pairs, descriptor transfer and inheritance against controlled external peers.
Host agents, named caches/daemons and external supervisors are incompatible with
restricted mode; a private runtime directory does not restore named IPC.

Landlock additionally denies socket inode creation/placement on shared file
state. Verify private /tmp, /run and /var/tmp roots and reject overlapping binds;
explicit REFER grants retain baseline ordinary rename/link/Git/worktree behavior.
Keep HOME/configuration unchanged and use a private 0700 XDG_RUNTIME_DIR for
ordinary runtime files. Preserve validated terminal/pipe/file stdio and close all
other inherited handles before preparation. Explicitly use private PID/IPC
namespaces; expose no host process, namespace, ring or device handles.

The release matrix records kernel/architecture, ABI, bootstrap/filter/protocol
identities, engine/backend, standard OCI policy, filesystem and actual positive/
negative results. Test Unix bypasses, alternate-family denial with positive
controls, async/compat syscalls, actual tool execution and session lifecycle.
Historical IP-only passes and mocked guard passes remain component evidence.
Startup requires current protected installation qualification plus mandatory
per-session checks. Qualification uses controlled positive/negative IP/IPC,
alternate-transport and provider TLS evidence in the actual production path;
an unavailable required control is blocking. Reports bind the actual host/boot,
engine/backend/security artifacts, code, immutable images, selected policy/profile,
CA trust, hardening and the engine host's IPv6 state. On kernels booted without
IPv6, kernel rejection of `AF_INET6` replaces the IPv6 positive control; any
contradictory evidence blocks. Changed inputs invalidate reuse; unobservable active LSM
policy identity causes a fresh gate each launch. Local qualification does not
claim exhaustive platform acceptance. Authenticated
account login/reuse/refresh has scoped manual evidence; optional real-key API
readiness remains unverified. Actual tool execution has a separate synthetic
Messages-API check.

These semantics are the common contract. Each sibling wrapper needs its own
bootstrap integration, compatibility and enforcement evidence before adoption
can be declared complete. Kernel/API references are recorded in the change's
design; this document does not claim that the current environment passed them.

Provider policies are versioned protected inputs outside writable mounts. They
select exact normalized hostnames and ports, normally HTTPS CONNECT on 443.
Connection-time IPv4/IPv6 validation denies private/special destinations and DNS
rebinding. Explicit local exceptions require an exact destination, address scope,
and port. Denials never add exceptions. TLS verification remains enabled without
decryption. Shell/commands that ignore proxy variables remain isolated.

API and account authentication use separate profiles. SSO, cloud/gateway/local
providers, optional features, Git, registries, browsing, and MCP destinations
require explicit reviewed additions. Record policy revision, source date, CLI
version, authentication method, and actual compatibility evidence. Disable
unnecessary optional traffic using version-supported controls.

Image pulls, proxy acquisition, and build RUN steps are separate host maintenance
activities. Exact operator maintenance authorization is required for acquisition
or builds; selecting unrestricted runtime mode does not authorize maintenance.
The runtime filter does not constrain those host activities. Do not forward
maintenance authority into the agent.

Each session owns distinct recoverable resources. Setup failure and shutdown
remove only owned resources within one 20-second budget and preserve the primary
exit/signal status. Proxy failure leaves outbound connections closed. Protected
bounded logs contain sanitized destination/port/reason, never secrets or payloads.

## Session container engine

A session whose toolchain library holds images gets a private container engine
(`session-container-engine`). It does not open a path around the boundary:

- **Network:** the engine owns the session's network namespace, created with the
  session's own network options (`--network=none` in offline and provider mode),
  and the session joins it. Nested containers, with their own namespace or with
  `--network=host`, have no route, DNS or connection that the session lacks; the
  engine pulls nothing in restricted modes.
- **Guard:** nested containers do not run under the in-process guard. Their reach
  is bounded by construction: the session's network namespace, and engine mounts
  limited to the workspace, the library's read-only image store and the CA
  bundle when trusted. No Podman socket, state, configuration or credential is
  mounted, and `/run/secrets` is masked.
- **Cgroup delegation:** an eligible engine (private cgroup namespace, cgroup v2
  root mounted read-write with `nsdelegate` and owned by its user namespace's
  root) gets its own cgroup subtree, delegated to the engine user by its startup
  step, so nested containers can run systemd and take explicit limits
  (`support-nested-systemd-containers`). The step is the only root process of
  the engine and holds `CHOWN` only to delegate; afterwards `CHOWN` stays only in
  the bounding set. The session budgets stay on the engine's cgroup: the kernel's
  `nsdelegate` rule forbids writes to the limit files of a cgroup namespace root
  from inside it, whoever owns them.
- **Qualification:** restricted qualification adds the `session-engine` check. A
  probe engine configured like a session's must show its documented hardening
  (PID 1 as the engine user with `cap_setuid,cap_setgid,cap_sys_chroot` and the
  bounding set with `cap_chown` as well, no root process, no-new-privileges, the
  derived seccomp profile, the keep-id mapping, the FUSE and TUN devices) and a
  read-only store; a nested container started with `--network=host` must see its
  own procfs and host name, no secrets, no route and no TCP path out. Every limit
  file of the engine's cgroup root must refuse a write, both from the engine user
  without capabilities and from a nested root that mounts the engine's cgroup
  namespace read-write; on a delegated engine that nested container must run in a
  cgroup of its own. The engine's delegation state (`delegated`, or `ineligible:
  <reason>`, which is no failure) is recorded in the report. The report binds the
  engine image ID and the seccomp profile digest, and a launch that starts an
  engine runs `qualify.py check --engine`, which refuses an installation without
  them.

| Check | Tests |
| --- | --- |
| No path out of an offline session | `tests/test_network_runtime.py::test_offline_session_engine_has_no_external_path`; the `session-engine` probe (`tests/test_qualification.py::test_engine_case_checks_hardening_views_and_reach`, `run-runtime.sh --qualification`) |
| Private views, no secrets, read-only store | `tests/test_runtime.py::SessionEngineTests`; the `session-engine` probe |
| Hardening exceptions | `tests/test_engine.py::EngineOptionsTests`; the `session-engine` probe |
| Cgroup delegation and unwritable budgets | `tests/test_engine.py::EngineCgroupTests` and the startup program tests; the `session-engine` probe (`tests/test_qualification.py::test_engine_case_checks_hardening_views_and_reach`); `tests/test_runtime.py::SessionEngineTests` |
| Qualification binding | `tests/test_qualification.py::test_engine_identity_requires_the_engine_checks`, `test_engine_launch_requires_a_qualified_engine` |

## Reference shell examples

The offline interfaces require the prepared protected guard and a matching
local qualification report. Use the protected installed wrapper path in place of
`./sandbox-container.sh` when the checkout is session-writable:

```bash
# Qualify a prepared restricted installation without credentials.
./sandbox-container.sh --container-qualify

# Default offline shell from a protected installation; the image must exist.
./sandbox-container.sh
./sandbox-container.sh -c 'git status'

# Explicit broad-network compatibility.
SANDBOX_CONTAINER_NETWORK=unrestricted ./sandbox-container.sh

# Operator-controlled preparation; runtime mode does not filter build traffic.
SANDBOX_CONTAINER_NETWORK=unrestricted SANDBOX_CONTAINER_MAINTENANCE=1 \
./sandbox-container.sh --container-build
```

Provider examples, profiles and endpoint inventories belong to each agent
wrapper's own contract copy.

Changing profiles or adding endpoints requires an operator policy revision and
revalidation. An agent-writable launcher cannot protect its own future launches;
install launcher/helpers/policies outside every writable workspace/state tree.

## Five-wrapper parity checklist

The reference is `sandbox-container` (this repository); the five wrappers are
Claude, Codex, Antigravity, OpenCode and Pi. Ports copy `network/`, `setup/` and the shared tests unchanged. Each
wrapper keeps the following per-agent items:
- its own `agent/profile.json` (variable prefix, images, labels, native home,
  command, configuration variable, authentication methods and their required
  hosts, and optional `install.files`: extra agent files, such as a version
  pin, that setup installs next to the wrapper and that qualification binds,
  and optional `install.runtime_build`: `wrapper` makes setup build the runtime
  image with the installed wrapper's build-only `--container-build`; an
  account method's `login_args` may be empty when the agent has no login
  command, and setup then offers sign-in inside the interactive agent; and
  optional `native.protected_env`: the variables and `_`-terminated prefixes
  the agent itself reads, which toolchains cannot set; the reference shell
  declares none, no authentication method and no approval-bypass variable);
- its own provider policies in `agent/policies/`;
- its wrapper and agent image.

`tests/test_alignment.py` fails if an agent identifier enters the shared files.
Variable prefixes differ; behavior and migration semantics must agree.

Port checklist for a wrapper:
1. Copy `network/`, `setup/` and the shared tests listed in `tests/test_alignment.py`.
2. Write `agent/profile.json` and `agent/policies/default.json`.
3. In the wrapper, keep CLI, engine verification, image operations, state layout
   and the agent container lifecycle. Call `network/session.py` `prepare`,
   `start`, `agent-args` and `stop` as documented in `network/README.md`. Add
   only agent-specific command, environment and credential options.
4. Pass the remaining shutdown budget to `stop`, and terminate an in-flight
   `start` by process group.
5. Adapt the agent-specific tests, then run the shared and runtime suites.

Later shared changes reach the ported wrappers through a new `sandbox-ref-N`
tag and `tools/propagate.py`; see [propagation](propagation.md).

| Wrapper | Contract adoption | Implementation | Real enforcement | Auth compatibility |
| --- | --- | --- | --- | --- |
| Sandbox (reference) | Reference (`sandbox-ref-36`, shared launcher core) | Guard, qualification and guided setup integrated; session container engine for image toolchains, with systemd in nested containers, host Podman delegation removed; Windows entry on a Podman machine (WSL provider) with installer, offline and unrestricted modes; no provider mode (no authentication method); provider mechanics covered by the fixture profile and the fixture agent part | WSL ABI 3: all runner modes passed (2026-11-22); `sandbox-ref-29` to `sandbox-ref-31` runner modes in a nested `cgroupfs` engine passed except the recorded budget and explicit-limit tests, `sandbox-ref-32` and `sandbox-ref-33` modes from a session passed except the nested-engine cases, `sandbox-ref-34` all modes from a session passed except the nested-engine cases and the tests that need cgroup limits, and its engine case passed on the machine's engine (2026-11-24), `sandbox-ref-35` all modes passed natively, the terminal tests included (2026-11-25), `sandbox-ref-36` the unit discovery, default, network, qualification, setup and setup runtime modes passed natively, the terminal tests included, and the engine started without a capability error (2026-11-26); Podman machine on Windows: validation script passed on both PowerShell editions (2026-11-21) and on 5.1 with the session engine (2026-11-24), nested systemd: runtime and qualification modes passed on the machine's engine (2026-11-26); native Linux (Rocky 9, Podman 5.8.0, `systemd` with `memory` and `pids`, no IPv6): `sandbox-ref-34` engine budgets and offline engine sessions verified, `sandbox-ref-35` every mode passed with the guarded terminal tests unavailable, and a terminal attached in an interactive session (2026-11-25), `sandbox-ref-36` the same modes as on WSL passed with the guarded terminal tests unavailable, and an unrestricted session started its engine without a capability error (2026-11-26) | Not applicable |
| Claude | Adopted `sandbox-ref-36`: shared launcher core | Shared launcher core, mandatory bootstrap, multiplexed proxy and guided setup integrated; session container engine for image toolchains, with systemd in nested containers, host Podman delegation removed; Windows entry on a Podman machine (WSL provider) with installer and every network mode | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-22); `sandbox-ref-34` modes from a Claude session with its engine passed except the nested-engine cases and the tests that need cgroup limits, and the engine and setup runtime cases passed on the machine's engine (2026-11-25), `sandbox-ref-35` unit discovery, guard, network, feasibility and setup runtime modes passed natively, the terminal tests included, with the interrupted-creation case passing alone after timeouts in the full network run (2026-11-25), and `sandbox-ref-36` unit tests of the changed files, setup, setup runtime, qualification and wrapper modes and the engine cases of the runtime and network suites passed natively, the other modes not rerun (2026-11-26); Podman machine on Windows: setup, account login, a Claude session and the validation script on both PowerShell editions passed (2026-11-22), and the validation script on 5.1 with the session engine (2026-11-24); native Linux (Rocky 9, Podman 5.8.0, `systemd` with `memory` and `pids`, no IPv6): `sandbox-ref-35` unit discovery, guard, network, feasibility and setup runtime modes passed with the guarded terminal tests unavailable, and a terminal attached in an interactive session (2026-11-25) | Account login, reuse and refresh passed; operator session with tool use passed (2026-11-11, `anthropic-account`); real-key API unavailable |
| Codex | Adopted `sandbox-ref-36`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; session container engine for image toolchains, with systemd in nested containers, host Podman delegation removed; Windows entry on a Podman machine (WSL provider) with installer and every network mode | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-22), and on `sandbox-ref-36` natively, the terminal tests and the engine cases included, with the shared and wrapper modes passing on a rerun after timing failures under load (2026-11-26); Podman machine on Windows: setup, device-code login, a Codex session, Codex's own sandbox in `unrestricted` and the validation script on both PowerShell editions passed (2026-11-22), the `sandbox-ref-36` smoke test pending (release risk) | Operator session with tool use passed (2026-11-11, `openai-account`; 2026-11-22 on Windows); refresh and real-key API checks pending; synthetic Responses API streaming and tool call passed |
| Antigravity | Adopted `sandbox-ref-36`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; private session engine for image toolchains with nested systemd; host delegation removed; keyring removed; Windows entry on a Podman machine (WSL provider) with installer and every network mode | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-23); Podman machine on Windows: setup, Google sign-in, an `agy` session with tool use, token reuse, the Gemini API key method with a dummy key and the validation script on both PowerShell editions passed (2026-11-23); `sandbox-ref-36` shared manifest, migration preflight and local synthetic suites recorded in the validation log, production checks scheduled after closure | Operator session with tool use passed (2026-11-11, `google-account`, policy `antigravity-2026-11-11-v2`; 2026-11-23 on Windows); refresh and real-key Gemini API checks pending; synthetic Gemini streaming and tool call passed |
| OpenCode | Adopted `sandbox-ref-36`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; private session container engine for image toolchains with nested systemd, host Podman delegation removed; Windows entry on a Podman machine (WSL provider) with installer and every network mode | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-23); Podman machine on Windows: setup, an OpenCode session with tool use (`openrouter-api`), native variables through `OPENCODE_CONTAINER_ENV_VARS` and the validation script on both PowerShell editions passed (2026-11-23); `sandbox-ref-36` shared manifest, alignment, static checks, OpenSpec merge preview and full non-runtime synthetic suites passed in the working session (2026-11-27), production WSL/Linux and Windows checks scheduled after closure | Operator session with tool use passed (2026-11-11, `anthropic-api`; 2026-11-23 on Windows, `openrouter-api`); the `openai-api` and `opencode-zen` profiles pending; synthetic Chat Completions streaming and tool call passed |
| Pi | Adopted `sandbox-ref-36`: shared launcher core | Shared launcher core, guard, multiplexed proxy, qualification and guided setup integrated; private session container engine for image toolchains with nested systemd, host Podman delegation removed; Windows entry on a Podman machine (WSL provider) with installer and every network mode | WSL ABI 3: all runner modes passed on `sandbox-ref-28` (2026-11-23); Podman machine on Windows: setup, a Pi session with tool use (`openrouter-api`), `PI_NPM_CACHE_SIZE` through `PI_CONTAINER_ENV_VARS` and the validation script on both PowerShell editions passed (2026-11-23); `sandbox-ref-36` shared manifest, alignment, static checks, OpenSpec merge preview and full non-runtime synthetic suites passed in the working session (2026-11-27), production WSL/Linux and Windows checks scheduled after closure | Operator session with tool use passed (2026-11-11, `anthropic-api`; 2026-11-23 on Windows, `openrouter-api`); the `openai-api` and `gemini-api` profiles pending; synthetic Chat Completions streaming and tool call passed |

For each wrapper, record mode/default parity, operator policy authority, separate
maintenance permission, authentication/feature inventories, leftover delegation refusal, session engine containment,
kernel/ABI/bootstrap prerequisites, Unix and alternate-transport isolation,
denied named IPC, fixed-peer pairs and multiplexed transport, preserved file persistence, DNS/address controls,
TLS/CA compatibility, redacted diagnostics,
owned bounded cleanup, controlled bypass evidence, and separate authenticated
login/refresh/streaming/WebSocket evidence. No untested entry counts as passed.

## Limits

Destination filtering permits data to be sent to allowed services. The
proxy binds an approved CONNECT hostname/address to exactly matching normalized
SNI in the initial TLS 1.2/1.3 ClientHello before forwarding client bytes, and
binds the retried ClientHello after a TLS 1.3 HelloRetryRequest the same way.
ECH/GREASE, missing/malformed/mismatched names and inspection limits/timeouts
fail closed. TLS 1.2 renegotiation is an accepted limitation: its ClientHello
is encrypted under the established session and the proxy never decrypts TLS.
This is not exclusive provider application access: encrypted HTTP Host/authority,
content, domain fronting with matching SNI, and shared services remain opaque. Network activity performed remotely by provider-hosted tools is outside
the local boundary. Rootless/backend support must be based on controlled positive
and negative tests, not an `--internal` flag or a failed Internet request alone.

### Residual exfiltration to allowed services

Destination and SNI binding cannot distinguish the operator's credentials from
attacker-supplied ones. A prompt-injected agent can send workspace data to any
allowed host with a foreign API key or account. Each agent wrapper lists the
hosts of its base profiles here and its setup requires an acknowledgement each
time provider mode is selected. The disclosure and any host reduction do not
prevent the channel; only offline mode removes it. The reference shell has no
provider mode and therefore no allowed hosts.

### Credential-injecting interception (not implemented)

A stronger design would let the proxy hold the provider credentials and inject
them into requests, so the agent never sees them and requests carrying other
credentials could be refused. It requires terminating provider TLS in the proxy
with a local CA trusted by the agent, re-signing upstream certificates, moving
credential custody and refresh into the proxy, and parsing HTTP in a much larger
trusted proxy. It conflicts with this contract's no-decryption guarantee and the
client's end-to-end certificate validation. It is a separately evaluated option
only: it is not implemented and requires an explicit operator decision and its
own change. Provider tunnels continue to forward TLS end to end.


## N01–N14 implementation and acceptance map

| Source task | Implementation (recorded in the Claude wrapper) | Acceptance / remaining scope |
| --- | --- | --- |
| N01 | Operator modes, protected profiles and separate maintenance authority | Wrapper/policy tests; sibling rollout pending |
| N02 | Private network/PID/IPC plus ABI-3 Landlock and additive seccomp | Real guard IP/IPC/alternate-family tests and wrapper gate |
| N03 | Outside session-owned versioned multiplex proxy, exact CONNECT authority policy | Codec/parser/address/TLS/streaming/WebSocket tests |
| N04 | Protected installation, static guard digest, policy snapshot/session manifest | Path/alias/ancestor/ELF/digest/mount/readiness rejection tests |
| N05 | Non-forwarding agent resolver, trusted per-OPEN resolution, numeric connect | DNS/rebinding/mixed/special IPv4/IPv6 and UDP/QUIC bypass tests |
| N06 | Consistent proxy/bypass variables, confined loopback relay, TLS unchanged | Synthetic real CLI/SSE tool and transport checks; real account request/refresh passed; long-lived/WebSocket transport covered by controlled fixtures |
| N07 | Leftover exact delegation opt-in refused before any engine query; session engine containment | Real mode/state/shell/YOLO grid; engine containment checks (qualification and runtime) |
| N08 | Unique ownership, recovery, one bounded shutdown budget | Concurrent/failed/interrupted setup, proxy death, stalled cleanup and statuses |
| N09 | Explicit host maintenance gate, immutable/prepared artifacts | Build/context/preflight tests; unrelated destinations remain denied |
| N10 | Protected bounded normalized destination/reason diagnostics | Secret/control-character/framing fuzz and real denial-log checks |
| N11 | Credential-free guard/proxy/wrapper and legacy positive controls | Mandatory account task 6.5 completed with scoped manual evidence; real-key check 6.4 is optional/unavailable |
| N12 | README/help/AGENTS, OpenSpec deltas, contract/parity and versioned evidence | Strict validation; main-spec sync/archive is a separate workflow |
| N13 | Dated installed-version API/account endpoint inventories | Account login/reuse/refresh passed; real-key API optional/unavailable |
| N14 | Version-supported optional-traffic controls and existing single-file CA trust | Native/YOLO/shell, actual synthetic Bash tool and CA checks; real login/reuse/refresh passed |

## N15–N17 destination-binding acceptance map

| Item | Implementation | Required acceptance |
| --- | --- | --- |
| N15 | Provider help/setup/security guidance distinguishes CONNECT/address, initial TLS SNI and encrypted application routing | Review visible guarantees and ECH/GREASE compatibility guidance |
| N16 | Trusted proxy ClientHello parser/gate, bounded buffers/deadline, redacted denials and mandatory `tls-clienthello-sni-v2` identity (retried ClientHello binding added by N22) | Unit/proxy tests plus controlled production acceptance; old readiness fails before agent sentinel |
| N17 | Controlled two-name shared-address TLS fixture with verified certificates and upstream byte counters | Matching success, alternate-name positive control, mismatched zero-byte rejection, fragmentation/limits/concurrency/failure checks and API/account inventory coverage |

Current measured status belongs to `docs/validation.md`. Parser and upstream-stub
checks do not establish production guard acceptance. Historical real login and
refresh results do not certify the revised proxy; real authenticated rechecks
need separate authorization. N01 sibling rollout remains pending.
