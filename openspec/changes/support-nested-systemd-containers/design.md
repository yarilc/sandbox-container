# Design

## Context

See proposal.md for the motivation and the spike results; the logs are in
`.test-state/logs/systemd-spike-*.txt`, and the spike's scripts in
`.test-state/spike-systemd/`.

Today's engine start (`replace-podman-delegation-with-session-engine`):
- `setup/engine.py container_options` gives `--init`, `--user podman`,
  `--userns=keep-id:uid=1000,gid=1000` and
  `--cap-add=SETUID,SETGID,SYS_CHROOT` with no-new-privileges. Podman's init
  (`/run/podman-init`) is PID 1, and the image entrypoint
  `/usr/local/bin/sandbox-engine [port [process limit]]` is PID 2. It sets the
  process rlimit, then serves the API on loopback TCP and on the Unix socket.
- `launcher/core.sh core_engine_start`:
  - on the rlimit fallback, verifies the engine's command with
    `created_command_starts`: `.Path` is `/run/podman-init`, then
    `-- /usr/local/bin/sandbox-engine 2375 <limit>`;
  - checks readiness with `engine exec <id> podman --remote … info`;
  - reads the rlimit from `/proc/2/limits`, because "the entrypoint is PID 2
    under --init".
- `network/qualify.py engine_case` builds a probe engine with the same
  options. `ENGINE_STATE`, run with a plain `exec`, expects:
  - `CapBnd: 00000000000400c0` in `/proc/1/status`;
  - `uid=1000` for the `exec` process.
- `setup/toolchains.py` runs helper containers of the engine image with
  `--user podman --entrypoint podman`, so they never use the image entrypoint.
- The engine base image (`quay.io/podman/stable` v6.2.0, Fedora 45) has `capsh`
  (libcap) and `catatonit` (`/usr/libexec/podman/catatonit`). It has no
  `setpriv`, `su` or `runuser`.

Spike facts that shape the approach:
- On both platforms, crun gives the engine a private cgroup namespace. Its
  root is mounted read-write (the engine's `unmask=ALL`), with `nsdelegate`,
  and its directory and delegation files belong to the root of the engine's
  user namespace.
- On native Linux the engine's limit files (`memory.max`, `pids.max`) belong
  to the engine user already today, because systemd delegates them. Every
  write to them fails with `EPERM`: the kernel's `nsdelegate` rule forbids
  writes to a cgroup namespace root's files from inside it, except
  `cgroup.procs`, `cgroup.subtree_control` and `cgroup.threads`.
- `capsh --user=podman --caps=… --addamb=…` under no-new-privileges gives the
  services exactly today's capability sets; only the bounding set keeps
  `CAP_CHOWN`.
- With controllers enabled at the engine's root, `podman exec` still works:
  crun falls back to the cgroup of the container's init.
- Commands that the startup step runs before it hands over consume process
  IDs, so the engine program is no longer PID 2 once a step runs before it.

## Goals / Non-Goals

**Goals:**
- One startup path for every engine, in every wrapper and on both platforms,
  with the eligibility rule in one place.
- No process of the engine runs as root after startup.
- The session budgets and the launcher's budget and rlimit verification keep
  their strength.

**Non-Goals:**
- Host-side delegation (A2), cgroup v1 hosts, and any host change.
- Guaranteeing behaviour under an enforcing SELinux or an active AppArmor
  policy: they are preserved, not guaranteed, as for the rest of the sandbox.
- Molecule or Ansible configuration of projects, and package access for
  targets (`add-read-only-dependency-mirror`).
- Systemd in the qualification probe: the probe has no image store, and the
  runtime tests cover systemd.

## Decisions

### D1. A startup program in the engine image is the container's first process

The image's entrypoint becomes `/usr/local/bin/sandbox-engine-start
[port [process limit]]`. The launcher starts it without `--init`, as
`--user 0:0` (the root of the engine's user namespace) with
`--cap-add=SETUID,SETGID,SYS_CHROOT,CHOWN`. All other options stay as they are.

In order, it:
1. sets the process rlimit, when given;
2. measures eligibility (D2), and delegates when eligible (D3);
3. hands over with `capsh --user=podman
   --caps='cap_setuid,cap_setgid,cap_sys_chroot+eip'
   --addamb=cap_setuid,cap_setgid,cap_sys_chroot`;
4. replaces itself with `catatonit -- /usr/local/bin/sandbox-engine <port>`.

Through these `exec` calls the first process stays PID 1, and ends as
`catatonit` running as the engine user. `catatonit` reaps orphans as
`--init` did, but no root process remains. `sandbox-engine` keeps only the
port argument: the rlimit is set once, by the first process, and every later
process inherits it. The image keeps `USER podman`, so any other use of the
image stays unprivileged. Started as a user other than root, the startup
program skips the delegation and reports the engine as ineligible.

Alternatives:
- **Podman's `--init` with the startup program as PID 2.** This keeps the
  launcher's PID 2 check, but leaves a root `catatonit` with `CAP_CHOWN` for
  the engine's lifetime. Rejected by the proposal's decision.
- **`setpriv`** is not in the base image; adding a package is a build input
  change with no benefit over `capsh`.
- **Host-side delegation (A2)** cannot run through a remote `CONTAINER_HOST`,
  and needs a second code path for the Windows machine.

### D2. One eligibility rule, shared by the startup program and the launcher

A small program in the image, `/usr/local/bin/sandbox-engine-cgroup`, holds
the rule. Read-only, it reports `eligible`, `delegated` or
`ineligible: <reason>` from:
- `/proc/self/cgroup` = `0::/` (a private cgroup namespace);
- file system type `cgroup2fs`;
- the mount's own options include `rw`, and its superblock options include
  `nsdelegate`;
- the root directory belongs to `0:0` (eligible), or to `1000:1000` with the
  engine's processes below the root (delegated).

The startup program calls it before it delegates. After readiness, the
launcher runs it in the engine as the engine user. On `ineligible: <reason>`
it prints the notice of the spec ("Ineligible engines are announced"); on
`delegated` it prints nothing. Any other answer stops the launch, naming the
engine.

`nsdelegate` is part of the rule: without it, an engine user who owns a limit
file could raise it, which the spike showed on native Linux.

### D3. What the delegation writes

As root, and before any ownership change (root keeps no DAC override
afterwards), the startup program:
1. creates the leaf `engine/`, and moves every process of `cgroup.procs` into
   it;
2. writes `+<controller>` to `cgroup.subtree_control` for each controller in
   `cgroup.controllers`;
3. hands to `1000:1000` the root directory, its `cgroup.procs`,
   `cgroup.subtree_control` and `cgroup.threads`, and the leaf with the same
   three files.

It changes no other file. When any step fails on an eligible engine, the
program exits non-zero, so the engine never answers, and the launch stops as
the spec's lifecycle requirement says. It never falls back to a
non-delegated engine.

Nested Podman (cgroupfs inside the engine) then creates each container's
cgroup below the root, and crun gives it to the container's root. Systemd
creates `init.scope` and its slices there, and explicit limits apply for the
enabled controllers.

### D4. The launcher runs its commands in the engine as the engine user

`podman exec` now defaults to the container's configured user, which is root.
Every launcher command in the engine passes `--user podman`: readiness, the
rlimit read and the eligibility report. So do qualification's `exec` calls.

The rlimit check reads `/proc/1/limits`, because PID 1 set the limit and kept
it through its `exec` calls. On the rlimit fallback, `created_command_starts`
expects `.Path` `/usr/local/bin/sandbox-engine-start`, then `2375 <limit>`.
`init_program` stays for the agent's unrestricted sessions.

### D5. Qualification

`engine_case` keeps its options from `container_options` and changes as
follows:
- **`ENGINE_STATE`** runs as `--user podman`. It expects `CapBnd:
  00000000000400c1` and `Uid` 1000 for PID 1, and `NoNewPrivs: 1` and
  `Seccomp: 2` as before.
- **The engine's eligibility** (`sandbox-engine-cgroup`) is recorded in the
  report, bound to the engine image identity. `ineligible: <reason>` does
  not fail the gate.
- **Limit files.** For every engine, the gate writes each limit file of the
  engine's cgroup root back with its own value:
  - from the engine user with all capabilities cleared (`capsh --caps==`);
  - from a nested root on the probe root file system with
    `--cgroupns=host --security-opt=unmask=ALL`.

  Any write that succeeds fails the gate. The gate never writes
  `cgroup.kill` or `cgroup.freeze`.
- **On a delegated engine**, a nested probe container must run in a cgroup
  below the root (its `/proc/self/cgroup` seen with `--cgroupns=host` is not
  `0::/`).

The checks apply to an ineligible engine too, which also covers today's
unqualified reliance on `nsdelegate`.

### D6. Runtime tests and validation

`SessionEngineTests` gains:
- systemd cases with a fixture image built from
  `tests/systemd-sample.Containerfile`. Its base is Rocky Linux 9's init image,
  pinned by digest, which already starts systemd. The recipe has no build step,
  so it builds without network from an empty context, under a tag derived from
  the recipe's digest, and the cases repeat on any host that holds the pinned
  base. `SANDBOX_TEST_SYSTEMD_SAMPLE` overrides the fixture, and the run skips
  with guidance when the base is missing. `test_image_pins.py` checks the pin
  and the absence of build steps.

  Alternatives: a minimal base with `dnf install systemd` needs network at
  build time, and Rocky Linux repositories drop older versions at each minor
  release, so pinned package versions stop resolving. Amazon Linux 2023 has no
  init image, and its fixture would need such a networked build; it stays in
  the validation runs, with the operator's lab targets;
- nested limits, where the engine has `memory` and `pids`;
- the process listing of the "No privileged engine process after startup"
  scenario.

`docs/validation.md` records the spike and the post-implementation runs on
the Rocky Linux lab host and on the Windows machine, including an Ansible run
(Molecule's Podman driver and the `orbit-e2e-lab` targets) from a session.

## Risks / Trade-offs

- **[A root step exists at startup.]** It is a fixed program in the protected
  engine image. It runs before any API is served, takes no input other than
  port and limit, and ends in a capability-narrowing `exec`. → Process-listing
  test and qualification check that nothing root remains.
- **[`CAP_CHOWN` stays in the bounding set.]** No-new-privileges and the lack
  of file capabilities keep it unreachable; removing it would need `SETPCAP`.
  → Documented as part of the exception; qualification expects `0x400c1`.
- **[The engine user can create cgroups and move processes in its subtree.]**
  This is the delegation model: children cannot exceed the parent's limits,
  and `nsdelegate` stops migration out of the namespace. The nested
  containers' root is the engine user already, so no new principal gains
  anything.
- **[Reliance on `nsdelegate`.]** Without it the limit files are not
  protected. → Part of the eligibility rule, and the limit-file check of D5
  applies to every engine.
- **[RLIMIT_NPROC set before the hand-over.]** The startup program's own
  helpers count against the limit of the user-namespace root, not the engine
  user, and stay a handful. → A failing hand-over fails the engine start
  loudly.
- **[crun's fallback for `exec`.]** It was observed with crun 1.27. An engine
  host whose crun lacks it fails readiness and stops the launch, rather than
  degrading.
- **[Systemd without controllers on the Windows machine.]** Resource-control
  unit settings have no effect there. → README.
- **[SELinux enforcing and AppArmor are unverified.]** → Recorded as
  unavailable in `docs/validation.md` until an enforcing host runs the suite.

## Migration Plan

1. Implement and test in this repository, then build the engine image. The
   engine inputs identity changes, so setup rebuilds it under maintenance
   consent, and qualification runs again because the engine image identity
   and the qualified code change.
2. Validate on the Rocky Linux lab host and on the Windows Podman machine, and
   record both in `docs/validation.md`.
3. Tag and propagate the shared files with `tools/propagate.py` (dry run, then
   `--apply`), following `docs/propagation.md`.
4. Operators rerun setup.

**Rollback:** setup's last-working-release rollback restores the previous
engine image and options. Nothing persistent changes: engine storage is
per session.

## Open Questions

- Whether an enforcing SELinux host or an AppArmor host is available for
  validation; the outcome is recorded, and the approach does not depend on it.
