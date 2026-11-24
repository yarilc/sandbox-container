# Design

## Context

See proposal.md for the motivation.

- **Sessions.** `launcher/core.sh` runs sessions with `podman create` followed by
  `podman start --attach`. Restricted sessions take their network, PID and IPC
  options from `network/session.py agent-args` (`--network=none`, plus a
  loopback relay to the egress proxy). Inside them, the static guard denies
  creating Unix sockets but allows loopback TCP (network-egress, "Restricted
  local IPC compatibility").
- **Toolchains.** `setup/toolchains.py` already pulls digest-pinned images on the
  host, then extracts subtrees from them. `launch-env` gives the launcher the
  library path and the default toolchain environment.
- **Spike.** A spike ran a nested engine from `quay.io/podman/stable` (Podman
  6.2, crun, fuse-overlayfs) beside session `yarilc-github-0` on the Windows
  Podman machine (cgroupfs, WSL kernel 6.18). Its findings shape the decisions
  below, and the logs are in `.test-state/logs/engine-*.txt`. Every runtime
  suite of this repository passed through that engine except:
  - the 5 budget subtests, which fail on the machine itself under cgroupfs;
  - the AF_VSOCK control, which also fails on the machine;
  - 3 guard tests that request explicit cgroup limits.

## Goals / Non-Goals

**Goals:**
- One engine design shared by every wrapper and every mode, Windows included,
  with the session's boundaries and no host authority.
- Reuse of the toolchain library's trust model (operator-pinned, host-fetched,
  read-only to the agent) for images.
- Removal of every delegation path: code, preferences, documentation and tests.

**Non-Goals:**
- Pulling images in restricted modes. The read-only mirror
  (`add-read-only-dependency-mirror`) may later serve registries; this change
  keeps offline engines offline.
- Building images that need network inside restricted sessions.
- Guaranteeing explicit cgroup limits for nested containers. Where the engine
  host delegates controllers they may work; they are not claimed.
- Image recipes in the release catalog. The catalog stays file-only in this
  change.

## Decisions

### D1. The engine owns the network namespace; the session joins it

The launcher creates and starts the engine first, with the network options the
session would have had:
- `network/session.py agent-args` for restricted modes;
- the default rootless network for unrestricted mode.

The session is then created with `--network container:<engine>`, keeping all its
other options. Kernel-level sharing is what the spike validated (there the
engine joined the session's namespace by path). This direction fits Podman's
dependency model: a `container:` dependency must be running when its dependent
starts, so the session can still be created and attached exactly as today.

Alternatives:
- **The engine joins the session by `ns:/proc/<pid>/ns/net` after `podman init`.**
  This keeps the session's options untouched, but depends on a PID that could be
  reused, and on Podman joining an initialized but not started container.
- **A pod.** This would change naming, ownership labels and cleanup for every
  session.

Task 1.1 verified D1 against the network runtime suite, qualification and
provider harness included. The only difference was `/etc/hosts`: a joined
container gets no `127.0.0.1 <short ID> <name>` entry, and Podman refuses
`--add-host` in `container:` mode. The launcher therefore binds a private hosts
file read-only at `/etc/hosts`:
- it holds the localhost entries and that line;
- it is created empty before `podman create`, and filled with the container's
  short ID and name before `podman start`, so the host name stays the container
  ID;
- engine sessions lose only Podman's `host.containers.internal` entry, which
  restricted sessions cannot reach anyway.

### D2. Loopback TCP endpoint on a fixed port

The engine's `podman system service` listens on `tcp://127.0.0.1:2375` inside
the shared namespace. The session gets:
- `CONTAINER_HOST=tcp://127.0.0.1:2375`;
- `DOCKER_HOST` with the same value, for Docker-API clients.

A Unix socket is not possible, because the guard denies socket creation in
restricted sessions. A fixed port is safe because every session has its own
namespace. Only processes in that namespace can reach the endpoint: the
application, and nested containers that use the engine's network. Both are
already inside the session's boundary.

The engine also serves a Unix socket inside its own filesystem and reports it
as `Host.RemoteSocket.Path`. Tools that bind the engine socket into nested
containers, such as `tests/run-runtime.sh`, then resolve it on the engine side,
as in the spike.

### D3. Engine image: our own Containerfile on a pinned base

A shared Containerfile in `launcher/engine/` builds
`FROM quay.io/podman/stable:<version>-immutable@sha256:<digest>`. Only the
`-immutable` tags keep their manifests: quay.io rebuilds the other tags daily
and deletes the manifests they pointed to, so a digest taken from `v6.2` or
`latest` stops resolving within a day (task 2.6). It
replaces the image's configuration rather than overriding it at run time,
because the spike found the image's defaults at four configuration layers:
- `containers.conf`: no host namespaces, cgroups enabled, `cgroupfs`, `crun`,
  `k8s-file` logs, `file` events, private UTS;
- `containers.conf.d/00-vendor.conf` (journald logs, which leave `podman logs`
  empty): deleted;
- `containers.rootless.conf.d/20-image_build.conf` (`volumes = ["/proc:/proc"]`,
  which gave every nested container the engine's procfs): deleted;
- `mounts.conf` (rhsm and entitlement passthrough, which tripped the guard's
  mount check): emptied;
- no `/etc/resolv.conf` in the image: an engine created with `--network=none`
  gets none, and nested bridge networks fail without it (measured), so the image
  carries the restricted sessions' resolver; an engine with a network gets
  Podman's generated file over it.

`storage.conf` keeps the image's overlay with fuse-overlayfs and
`additionalimagestores = ["/var/lib/shared"]`.

The Containerfile is a build input pinned like the others
(`tests/test_image_pins.py`). Setup builds it in every mode, as for the runtime
image.

### D4. Engine container options

| Option | Why it is needed (spike evidence) |
|---|---|
| `--init` | The service does not reap children, and zombie fuse-overlayfs/conmon processes exhausted `RLIMIT_NPROC`, so the proxy failed to clone. |
| `--user podman`, `--userns=keep-id:uid=1000,gid=1000` | The engine runs unprivileged as the caller: nested containers' root is the caller, so files they create in the workspace belong to the caller, as with delegation. Without it, nested root is a subordinate ID and cannot write a caller-owned workspace (measured, task 2.3). The engine user's subordinate ranges (1-999, 1001-65535) need 65535 of the caller's contiguous subordinate IDs. |
| `--cap-drop=all --cap-add=SETUID,SETGID,SYS_CHROOT --security-opt=no-new-privileges` | `newuidmap` and `newgidmap` need `CAP_SETUID` and `CAP_SETGID`. For the non-root engine user, Podman passes added capabilities as ambient ones, so no file capability is needed and no-new-privileges stays on (measured, task 2.3). Layer extraction (`pull`, `load`) and image builds chroot into the layer, which needs `CAP_SYS_CHROOT`: Podman re-executes itself in its rootless user namespace, where the bounding set caps it. Without it, a `RUN` step failed with `chrooting to directory …: operation not permitted` and a load of new layers failed with `chroot ".": operation not permitted` (measured, task 2.5). |
| `--security-opt unmask=ALL` | Mounting a fresh procfs requires a fully visible `/proc`. |
| `--security-opt label=disable` | Nested containers cannot work under the engine's SELinux label. |
| `--device /dev/fuse` | Needed by fuse-overlayfs. |
| `--device /dev/net/tun` | Needed by the nested default network (pasta). |
| `--security-opt seccomp=<profile>` | The engine host's default profile denies `sethostname` without `CAP_SYS_ADMIN`, which broke private UTS. |
| empty read-only tmpfs at `/run/secrets` | Masks the secrets directory. |
| workspace at the same path, `<library>/.images` at `/var/lib/shared:ro`, session volume at the graph root | The only mounts. |

The seccomp profile is generated by setup from the engine host's
`/usr/share/containers/seccomp.json`. The only change: `sethostname` and
`setdomainname` become unconditionally allowed. The kernel still requires
`CAP_SYS_ADMIN` over the owning UTS namespace, so nested containers can name
only themselves. The profile is stored in the installation, and its source
digest is part of the qualification identity. When the host's default changes,
setup regenerates it and qualification runs again.

`--privileged` is not used. These exceptions are listed in the README and
checked by the qualification probe (D10, task 5.1).

### D5. The image store is a read-only containers/storage tree in the library

- **Location.** `<library>/.images` holds an overlay containers/storage tree. The leading dot keeps it out of `installed()` and away from toolchain names, since `images` is a valid name.
- **Writes.** Only `--container-toolchain` writes it, through a helper container
  of the engine image, so file ownership follows the same ID mapping that session
  engines read:
  - `--user podman` with `--userns=keep-id:uid=1000,gid=1000`, as the engines,
    so the caller owns the store directory and no ownership change is needed;
  - the store mounted at the helper's graph root;
  - host network;
  - the host CA bundle when trust is enabled.
- **Pulls** go straight from the registry, so the index and platform digests are
  both recorded. The spike showed that save/load into an engine loses the index
  digest.
- **Local images** are streamed from the host engine with `podman save`, loaded
  by the helper, and verified to have the recipe's image ID.
- **Index.** `index.json` records which toolchains list which image. Deletion
  happens only when no toolchain lists an image any more. The index keeps its
  schema number and gains only optional fields, because `launch-env` rejects any
  other schema and the previous release must keep reading the library after a
  rollback.
- **Live updates.** Session engines mount the store at `/var/lib/shared:ro`.
  containers/storage detects a writer's change through the store's lock files,
  so a running engine sees an added image without a restart (verified in the
  spike). Images in the store are reported `ReadOnly`, and the engine refuses to
  remove them. Tagging one copies its record into session storage and keeps the
  original names (verified).
- **Visibility.** The store is visible under `/toolchains/.images` in sessions,
  read-only, `nosuid` and `nodev`. It contains only images the operator chose;
  `toolchains.md` tells the agent to use them through the engine.

Alternatives:
- **An OCI layout loaded into each session's storage.** This copies every image
  into every session and loses index digests.
- **A local registry service.** A new long-running trusted component, which the
  dependency mirror may provide later.

### D6. Session storage is a labelled volume

Each engine's graph root is a named volume carrying the session ownership label.
It is created with the engine and removed with it by the existing session-owned
cleanup, including the stale-session reconciliation of a later launch.

Alternatives:
- **tmpfs.** Bounded by memory and too small for real images.
- **Per-wrapper persistent storage.** Carries agent-built state across sessions,
  and concurrent engines on one store would contend.

### D7. Budgets reuse the agent rules

The launcher applies the session's memory, CPU and process budgets to the engine
container through the same code paths and rules as the agent:
- delegated controllers only with the systemd cgroup manager;
- the `--ulimit nproc` fallback where the kernel counts it per container;
- verification after creation;
- notices for unenforced budgets.

A session therefore has the agent's budget twice, and the launch notice says so.
Under cgroupfs, nothing bounds nested containers beyond the process rlimit of
the processes that inherit it; this is announced, as for the agent.

### D8. Removal is refused while any engine runs

The toolchain command lists running engine containers by their label. A change
that would delete an image fails while any of them is running, naming the
sessions. Adding images never deletes anything and is always allowed.

This is the conservative rule, and task 3.6 showed it is needed: removing an
image under a running nested container made its files vanish, and the engine
could no longer inspect or remove that container.

### D9. Delegation removal and migration

- **Launcher.** It refuses an exact `SANDBOX_CONTAINER_PODMAN=1` before engine
  queries, with one message shared with the Windows shim. It ignores other values
  and the old socket variable. It no longer adds the socket mount,
  `CONTAINER_HOST`, the tmpfs client storage or the endpoint selection code.
- **Setup.** The preferences schema version increases. Setup reads the old
  `podman` and `delegation_socket` keys only to migrate them away. The managed
  launcher refuses preferences that still contain an enabled `podman`, with
  setup guidance.
- **Windows.** The shim's existing refusal keeps its exit status with the new
  text; the bootstrap's saved-delegation refusal is unchanged.
- **Capability.** `container-podman-access` is retired in full, and its tests
  are removed or rewritten as refusal tests.

### D10. Qualification probes the engine without an image store

Restricted qualification starts a probe engine like a session's. It runs nested
containers from a root filesystem directory shipped in the engine image
(`podman run --rootfs`), so it needs no image store. It checks:
- no route out of the session;
- a private procfs and UTS in nested containers;
- an empty `/run/secrets`;
- refusal to write a read-only store, using a store with one empty record
  prepared by the probe;
- the engine container's options against D4.

The probe store is empty but holds the `overlay-images` and `overlay-layers`
lock files: a read-only store without them makes every container creation fail
(measured). The results join the report, bound to the engine image ID and the
seccomp profile digest. Launches that would start an engine require a current report
that includes them.

### D11. Image recipe checks use a temporary engine

`add` and `verify` start a temporary engine with no network. Its store is the
library's store, including the staged images. The check container runs in the
runtime image with `--network container:<engine>` and
`CONTAINER_HOST=tcp://127.0.0.1:2375`. This is the session topology, so a check
that passes predicts a session that works.

## Risks / Trade-offs

- **[The engine container is less confined than a shell container]** It holds
  user-namespace helper capabilities and the chroot capability, which standard
  containers also have; SELinux labelling is disabled, procfs is
  unmasked, and FUSE and TUN are present. → It runs unprivileged, holds no
  secrets and has no host socket. Its only host paths are the workspace (already
  writable by the session) and the read-only store. The exceptions are fixed,
  documented and checked by qualification.
- **[Nested containers bypass the in-process guard]** → Their reach is bounded by
  construction: the session's network namespace and the engine's mounts. Engine
  containment is part of qualification and of the credential-free bypass
  evidence.
- **[Double resource budget per session]** → Announced at launch, and documented.
  A shared budget across two containers would need a pod or a parent cgroup,
  which is out of scope.
- **[First image requires a new session]** → Stated in `toolchains.md` and the
  README; later images are live.
- **[Removal blocked by long sessions]** → The message names the sessions; the
  operator ends them or retries.
- **[D1 may conflict with session network options]** (`/etc/hosts`,
  `resolv.conf` and readiness checks under `container:` networking) → Task 1.1
  comes first, and the `ns:` fallback is defined.
- **[Old Podman clients in the session]** The runtime image has Podman 4.3.1
  against a 6.2 engine. → The remote API worked for every suite in the spike;
  the client version is recorded in validation.
- **[Breaking change for delegation users]** → Explicit refusal with migration
  guidance instead of silent behavior change. Setup migrates preferences.

## Migration Plan

1. Implement and test in this repository: launcher, network helper, setup and
   toolchains, with tests and documentation.
2. Validate on the Windows Podman machine (the spike environment) and on a
   native Linux host with the systemd cgroup manager. Record both in
   `docs/validation.md`, including the checks that stay machine-only.
3. Tag and propagate the shared files with `tools/propagate.py` (dry run, then
   `--apply`), following `docs/propagation.md`.
4. Operators rerun setup, which migrates saved delegation away and builds the
   engine image. They then add the images they need with
   `--container-toolchain add`.

**Rollback:** setup's last-working-release rollback restores the previous
installation, delegation included. The library stays readable by the previous
release: it skips `.images`, and the index keeps its schema (D5). Image-only
toolchains appear there as non-default toolchains without a root, which the
previous release lists but cannot use; task 3.7 checks this.

## Open Questions

- Whether nested explicit cgroup limits work on native hosts with the systemd
  cgroup manager. This is recorded in validation; nothing depends on it.
- Which image recipes, if any, join the release catalog. That is a later change.
