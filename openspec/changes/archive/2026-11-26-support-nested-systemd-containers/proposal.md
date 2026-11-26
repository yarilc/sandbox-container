# Proposal

> Status: roadmap. The spike ran on both platforms on 2026-11-25 and
> 2026-11-26 (logs in `.test-state/logs/systemd-spike-*.txt`); design, specs
> and tasks follow. It builds on
> `replace-podman-delegation-with-session-engine`, and the Ansible use case
> also needs `add-read-only-dependency-mirror`.

## Why

Projects that develop Ansible roles and playbooks test them in containers
that run systemd as PID 1, so that services, handlers and unit files behave as
on a real host. Examples are Molecule scenarios, or an operator's lab of a
controller image with Rocky Linux 9 and Amazon Linux 2023 targets that run
`/sbin/init` (the `orbit-e2e-lab` image toolchain). The session container
engine cannot run them on either supported platform. The spike reproduced the
same failure on both:
- **Native Linux with the `systemd` cgroup manager** (Rocky Linux 9.8,
  kernel 5.14, Podman 5.8, controllers `memory` and `pids`);
- **Windows Podman machine** (Fedora 44 machine, WSL kernel 6.18, Podman 6.1,
  `cgroupfs`, no controllers).

On both, the engine has its own cgroup in a private cgroup namespace, mounted
read-write, but its root belongs to the root of the engine's user namespace,
while the engine runs as its `podman` user (uid 1000). Nested containers
therefore get no cgroup of their own, and stay at the engine's cgroup root.
Systemd 252 in the Rocky Linux 9.9 and Amazon Linux 2023.12 targets stops
with `Failed to create /init.scope control group: Permission denied`, and
explicit nested limits fail with `crun: cannot set limits without cgroups`.
Systemd needs a writable cgroup v2 hierarchy, not controllers.

The `session-container-engine` spec forbids widening the engine's hardening
exceptions for a nested tool. Supporting systemd therefore needs an explicit,
reviewed exception rather than a workaround.

## What Changes

- Eligibility is measured when the engine starts, not inferred from the cgroup
  manager. An engine is eligible when it has a private cgroup namespace whose
  root is a cgroup v2 directory, mounted read-write with `nsdelegate` and
  owned by the root of the engine's user namespace. Both platforms are
  eligible, and every eligible engine gets the delegation.
- On an eligible engine, a delegation step runs first, as the root of the
  engine's user namespace with `CAP_CHOWN` in addition to the engine's
  capabilities:
  - it moves every engine process into a leaf cgroup;
  - it enables the available controllers for nested containers;
  - it hands the engine's own cgroup subtree to the engine user: the
    directory and its `cgroup.procs`, `cgroup.subtree_control` and
    `cgroup.threads` files, as in the kernel's delegation model.
- The engine's services then run as the engine user with exactly today's
  capabilities, as ambient ones, with no-new-privileges still on.
  - No engine process keeps the root identity after startup: the engine's
    init (`catatonit`) runs as the engine user instead of Podman's `--init`,
    which keeps it root.
  - `CAP_CHOWN` stays in the bounding set, where no-new-privileges keeps it
    unreachable; the exception documents it.
- The engine's own limit files stay unwritable from the engine and from
  nested containers. The session budgets keep bounding the engine and all its
  nested containers together. Where the engine has controllers (native Linux
  with the `systemd` manager), explicit nested limits are guaranteed for those
  controllers; on the Podman machine, which delegates no controller, they stay
  unavailable.
- Nested containers can run systemd as PID 1 (`podman run --systemd=always`)
  on native Linux and on the Windows Podman machine, with Rocky Linux 9 and
  Amazon Linux 2023 as the reference targets.
- The delegation is a new fixed hardening exception of the engine. It is
  documented, and the qualification probe checks it.
- Engine containment qualification gains two checks: the engine cannot change
  its own limits, and nested cgroups stay below the engine's cgroup.
- On an ineligible engine (cgroup v1, or an engine host whose Podman cannot
  create container cgroups), nothing is delegated. Systemd containers are
  unavailable there, the launch says so, and so does the README.
- The README section on container tests describes systemd containers, the new
  exception and the platforms where it applies.

Decisions already taken during exploration:
- **Native Linux and the Windows Podman machine are both in scope.** Host
  changes to delegate cgroups are never required.
- **The exception is the engine's own cgroup subtree, nothing more.** The
  engine stays unprivileged; `--privileged`, root engines and virtual machines
  are rejected.
- **Eligibility is measured, not inferred** from the cgroup manager: the
  Podman machine uses `cgroupfs` and still gives each container its own
  cgroup.
- **Target images with systemd are the project's own.** The Rocky Linux 9 and
  Amazon Linux 2023 targets of the `orbit-e2e-lab` toolchain already run
  `/sbin/init`; the operator builds them and adds them to the library.
- **The delegation step runs in the engine image (A1).** A host-side
  delegation by the launcher (A2) is dropped: the spike showed it is not
  needed, and it could not run through a remote `CONTAINER_HOST`.
- **The session budgets are protected by the kernel.** On native Linux the
  engine's `memory.max` and `pids.max` already belong to the engine user,
  because systemd delegates them, yet every write to them fails with `EPERM`.
  The `nsdelegate` mount option forbids writes to the files of a cgroup
  namespace root from inside the namespace, except the delegation files, so
  eligibility requires it.
- **Explicit nested limits are guaranteed** for every controller an eligible
  engine has.
- **The delegation is always on** for eligible engines: one engine
  configuration to qualify and document, and no new option.

Spike results, with an engine started with the launcher's options
(`setup/engine.py`) and the A1 delegation step:

| Check | Podman machine | Rocky Linux 9 |
| --- | --- | --- |
| Engine eligible | yes | yes, with `memory` and `pids` enabled for the subtree |
| Nested container gets its own cgroup | yes | yes |
| Systemd in Rocky Linux 9.9 and Amazon Linux 2023.12 targets | `running`, no failed unit, a transient unit active and journaled | the same |
| Explicit nested limits (`--memory=64m --pids-limit=32`) | unavailable: no controller | applied (`67108864`, `32`) |
| Writes to the engine's limit files, from the engine user without capabilities and from a nested root with the engine's cgroup namespace mounted read-write | denied (`EPERM`) | denied (`EPERM`) |
| Capabilities of the engine's services | as today, plus `CAP_CHOWN` in the bounding set | the same |
| `podman exec` into the engine | works; the process joins the cgroup root, which has no controllers | works; crun falls back to the init's leaf cgroup |
| SELinux | not active | disabled |

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session-container-engine`: the measured eligibility of an engine; the fixed
  hardening exceptions gain the delegated cgroup subtree; nested containers
  can run systemd on eligible engines; engine containment qualification
  covers the delegation; the documentation covers systemd containers and the
  platforms where they work.

## Impact

- Engine image: `launcher/engine/` gains the delegation step and starts
  `catatonit` and the services as the engine user (`capsh` is in the image;
  `setpriv` is not).
- Engine options: `setup/engine.py` (user, the added `CAP_CHOWN`, no
  `--init`).
- Launcher: `launcher/core.sh` verifies the engine's first process and
  arguments (`/run/podman-init` today) for the process rlimit fallback, and
  gains the notice for ineligible engines.
- Qualification: the `session-engine` probe and its report identity.
- Tests: `tests/test_engine.py` (`EngineOptionsTests`), the runtime
  `SessionEngineTests`, the launcher budget cases, and the `--guard` tests
  that request nested limits.
- Documentation: the README's container tests and Windows sections, and
  `docs/validation.md` with the spike results above.
- Shared files: propagated to every wrapper with `tools/propagate.py`.

## Open Questions

- **Ansible test run:** an Ansible run from a session through
  `CONTAINER_HOST`, with Molecule's Podman driver and with the
  `orbit-e2e-lab` targets, is still to be measured; it becomes a validation
  task of this change.
- **SELinux enforcing:** neither spike host enforces SELinux; behaviour on an
  enforcing host is unverified.
- **AppArmor hosts:** behaviour under an active AppArmor profile, which
  neither platform exercises.
- **Systemd without controllers:** which unit settings a test cannot exercise
  on the Podman machine (resource-control properties are ignored there), and
  how the README states it.
