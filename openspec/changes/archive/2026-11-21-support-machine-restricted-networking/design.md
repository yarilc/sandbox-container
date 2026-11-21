# Design

## Context

- **Restricted modes and their requirements.** `offline` and `provider` need
  a verified same-host Unix launch service. `network/platform_check.py`
  requires `true linux true` through a `unix://` endpoint, Netavark, Podman
  4.9 or later, x86_64, standard seccomp and Landlock ABI 3 or later. They
  also need the static guard (built with the toolchain image), the protected
  installation and the local qualification.
- **How setup finds the service.** Setup probes `CONTAINER_HOST`, the saved
  endpoint and the default endpoint `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`,
  then a usable systemd user manager (`systemctl --user`). The launcher's
  delegation default uses the same directory.
- **The machine's structure** (spike, rounds 2 and 3):
  - WSL's `/init` is PID 1 of the distribution. At machine start, Podman runs
    `unshare --kill-child --fork --pid --mount --mount-proc --propagation
    shared /lib/systemd/systemd`: systemd is PID 1 of child PID and mount
    namespaces.
  - The user's systemd manager, `podman.socket` and the service run there.
    `/run/user/<uid>` is the tmpfs of the user's login in that namespace,
    propagated to the parent.
  - `/etc/profile.d/enterns.sh` and `/usr/local/bin/enterns` take login shells
    into the namespaces: `sudo nsenter -m -p -t <systemd> --wd=$PWD`, then
    `sudo -u $USER`. The user `user` has passwordless `sudo`.
  - `wsl.exe --exec` runs no profile, so phase 1's sessions, setup and help
    stay in `/init`'s namespaces.
- **What goes wrong outside.**
  - In `/init`'s namespaces `systemctl --user` fails ("Transport endpoint is
    not connected").
  - The session's podman starts its own rootless user namespace (a second
    `catatonit`) on the service's storage. A container started by one side
    is listed by the other, but `podman exec` fails ("container is not
    running").
  - With `XDG_RUNTIME_DIR=/run/user/<uid>`, both sides replace each other's
    `pause.pid` on every command. Phase 1 used the WSLg directory, which kept
    the two `pause.pid` files apart by accident, but not the user namespaces.
- **What phase 1 refuses.** The shim refuses `<P>_NETWORK` other than
  `unrestricted`, `<P>_PODMAN=1` and `--container-qualify`. The bootstrap
  refuses saved preferences other than unrestricted without delegation.

## Goals / Non-Goals

**Goals:**

- `offline` and `provider` on the machine, with the unchanged shared
  launcher, setup, guard, qualification and session code.
- One engine: sessions, setup, the machine's service, Podman Desktop and
  `podman.exe` share one PID namespace and one rootless user namespace.
  Help queries no engine and stays outside.
- Only the machine's own service: never a socket in the shared WSLg
  directory.

**Non-Goals:**

- Podman delegation on Windows.
- Changing how Linux hosts or other WSL distributions derive the default
  endpoint.
- Starting a service from the entry when the machine has none.
- Adapting the shared runtime tests to an engine without delegated cgroup
  controllers.

## Assumptions and spike outcomes

| # | Assumption | Outcome (spike) |
|---|---|---|
| A1 | The machine serves a rootless API at `/run/user/<uid>/podman/podman.sock`, through the user's systemd manager, after a restart too. | Holds: socket-activated `podman.socket`, present after `wsl --terminate` and `podman machine start`. Setup's probe finds it with the machine's runtime directory, and the user manager works inside systemd's namespaces. |
| A2 | The service sees the session's files and containers. | Files hold from every namespace: binds of `/mnt/c/...`, `/home/user` and `/run/user/<uid>` match. Containers hold only inside systemd's namespaces (decision D2). |
| A3 | Netavark, rootless, seccomp and Landlock ABI 3 or later. | Holds: `platform_check` eligible (Podman 6.1.4, kernel 6.6.87.2), Landlock ABI 3. |
| A4 | The guard toolchain builds in the machine, and `--guard` passes. | Holds: the toolchain built, and 18 of 19 guard tests passed (round 4). The failure is the unguarded control of `test_existing_late_sockets_and_aliases_across_bind_roots`: the machine's default seccomp profile refuses `socket(AF_VSOCK)`, which `seccomp=unconfined` and the distribution allow. The platform is stricter than the test assumes. |
| A5 | `--qualification`, `--network` and `--setup-runtime` pass with the `cgroupfs` budget rules. | Holds: `--qualification` and `--setup-runtime` passed. In `--network` the offline and provider sessions, TLS binding, readiness and fail-closed cases passed. The 3 failing tests read cgroup interfaces (`memory.max`, `pids.events`) or expect a memory limit, which `cgroupfs` does not apply; the launcher's notices state it, and the process budget reached its rlimit. These are the engine limits recorded since `sandbox-ref-26`. |
| A6 | The machine is rootless. | Holds: `Rootful: false`; no `/run/podman/podman.sock`. |

## Decisions

### D1. Spike in the machine, before the code

Throwaway operator scripts, not committed, ran in four rounds; the results
are in `docs/validation.md`.

- Round 1: the inventory. It misread values because Podman's warnings went to
  the same stream.
- Round 2: the inventory, with the namespaces.
- Round 3: two ways into systemd's namespaces, the inventory and the suites
  inside them.
- Round 4: the suites again, with the missing base pulled.

### D2. A helper enters the machine's systemd namespaces

The new `launcher/windows/enter.sh` runs `<command> [args...]` as the calling
user inside systemd's PID and mount namespaces:

1. If PID 1 is already `systemd`, it runs the command directly, with
   `XDG_RUNTIME_DIR=/run/user/<uid>`.
2. Otherwise it finds the machine's systemd: a process named `systemd` whose
   `NSpid` is `<pid> 1`. When there is none, it stops with the machine
   guidance.
3. It checks `sudo -n true`; when `sudo` needs a password, it stops with
   status 1 and names the requirement.
4. It writes the environment (`env -0`) to a new mode-0600 file in the
   mode-0700 directory `/run/user/<uid>/windows-entry`. The file name holds
   the helper's PID, which `exec` hands to `sudo`; files whose PID no longer
   runs are left from a failed start and are removed first.
5. It runs `sudo -n -- nsenter --target <pid> --mount --pid --wd=<cwd> --
   sudo -n -u <user> -- /bin/bash <helper> --inner <file> <command>...`.
6. The inner part reads the file, removes it, and runs `env -i <saved
   variables> XDG_RUNTIME_DIR=/run/user/<uid> <command>...`.

Arguments stay an argument vector at every step; root runs only the fixed
`nsenter` and `sudo -u` with the user's directory, the file name and the
command vector. The environment never reaches root's command line.

Users:

- the bootstrap ends with `exec /bin/bash <release>/launcher/windows/enter.sh
  <name> <managed command> <arguments>`;
- the shim starts setup as `--cd <checkout> --exec /bin/bash
  launcher/windows/enter.sh <name> /bin/bash <wrapper> --container-setup`;
  help queries no engine and stays a direct run, so it works without `sudo`;
- the helper is a release file (`setup/common.py`) and a shared file
  (`tests/test_alignment.py`).

Why this way:

- It is the machine's own `enterns` path, so the session, the service and
  Podman's own connections share one engine.
- In round 3 the `sudo` way passed every automated check, Ctrl+C (status 130,
  no leftover) and window close (no leftover).
- The `nsenter --setuid --setgid` way passed the automated checks, but:
  - it lost the supplementary groups;
  - Ctrl+C gave status 2 and left a container in the `Created` state;
  - window close left a `conmon` process.

Alternatives considered:

- *Only the service, from `/init`'s namespaces* (every restricted engine
  operation through `CONTAINER_HOST`, with a client runtime directory apart
  from `/run/user/<uid>`). It keeps two user namespaces on one storage, a
  configuration that Podman warns against ("Failed to join existing conmon
  namespace"). Unrestricted sessions and Podman Desktop would still not
  manage each other's containers.
- *`podman machine ssh`*. The entry would depend on the machine's SSH
  connection, which phase 1 excluded.

### D3. Runtime directory

Inside the namespaces, `XDG_RUNTIME_DIR=/run/user/<uid>`. Then:

- the default endpoint, `systemctl --user` and Podman's run root agree with
  the service;
- `pause.pid` is shared with the service, as Podman expects;
- the WSLg directory stays unused.

Shared code does not change.

### D4. Mode checks on Windows

The shim drops its refusals of `<P>_NETWORK` and `--container-qualify`,
because the launcher validates both. It keeps the delegation refusal: the
delegated socket would control the machine's whole engine. The Windows help
lists the modes and states that restricted modes need setup in the machine.
The bootstrap refuses saved delegation only.

### D5. Missing service

The shim adds nothing. Inside systemd's namespaces setup's existing paths
apply:

- the service answers;
- or the user manager can start it (`systemctl --user enable --now
  podman.socket`);
- or only unrestricted networking is offered (phase 1, D10).

A restricted launch on an unrestricted installation stops with the
launcher's setup guidance before any engine query.

### D6. The guard as a confined init

Restricted containers have no `--init`: the guard refuses the engine's init
mount below `/run` (U12), and the guard is the entrypoint. It executes the
application, which becomes PID 1 of the container's PID namespace. The kernel
drops a signal to a namespace's PID 1 that has no handler for it, so Ctrl+C,
and the TERM of the launcher's shutdown, leave `sleep` running. Measured on
the Windows machine (task 5.2) and on Linux with plain Podman (`sleep 20`
without `--init`: Ctrl+C ignored, status 0 after 20 s; with `--init`: status
130 after 0.3 s).

After Landlock, the seccomp filter and the runtime environment, the guard:

1. resets SIGCHLD to its default action and blocks the signals it waits for:
   HUP, INT, QUIT, TERM, USR1, USR2, WINCH and CHLD;
2. forks:
   - the child restores the signal mask and moves to a new process group;
   - when standard input is a terminal, it makes that group the terminal's
     foreground group (`tcsetpgrp`, with SIGTTOU ignored for the call; a
     terminal that is not the controlling one is left alone);
   - it then executes the application, as before;
3. the guard closes standard input and output, and the provider's proxy
   channel (fd 3), which only the relay in the child uses;
4. it waits for signals (`sigwaitinfo`):
   - on CHLD it reaps every exited child, and when the application has
     exited, it exits with its status, or 128 plus the signal number;
   - every other signal goes to the application (`kill`).

A terminal's Ctrl+C reaches only the foreground group, so the application gets
it once, and the guard forwards only what is sent to the container. When the
guard exits, the kernel ends the rest of the PID namespace, as `--init` does.

The guard keeps its Landlock and seccomp restrictions, which the child
inherits. The seccomp filter restricts only socket creation, `io_uring` and
`pidfd_getfd`, so `fork`, `setpgid`, `tcsetpgrp`, `kill` and `wait4` stay
available. The revision stays `abi3-seccomp-mux-v1`, because the enforcement
and the multiplex protocol are unchanged; the guard's digest changes, so the
qualification identity changes and setup recompiles and requalifies.

Alternatives considered:

- *`podman --init`*: the engine mounts its init below `/run`, which the guard
  rejects for restricted sessions (U12).
- *The relay as init*: it runs only in provider mode, in Python, after the
  guard.

### D7. Setup proposes the service endpoint

When the selected network mode or delegation needs a same-host Unix service
and the saved endpoint is `local`, setup proposes `default`, so a user who
moves a phase 1 Windows installation to offline networking accepts the
proposed value instead of seeing it refused. Unrestricted reruns keep the
saved endpoint.

## Risks / Trade-offs

- [The namespaces, `enterns` and passwordless `sudo` are details of Podman's
  machine image, and a release could change them.] → The helper runs directly
  when systemd is PID 1 and stops with guidance when `sudo` needs a password
  or systemd is missing; it never falls back to `/init`'s namespaces.
- [`sudo` allocates a pseudo-terminal (`use_pty`).] → Round 3 showed status,
  streams, Ctrl+C and window close through it. The Windows validation repeats
  them through the entry, with the terminal size.
- [Every launch logs two `sudo` entries in the machine's journal.] →
  Accepted; it is how the machine's own login shells enter.
- [Phase 1 behavior changes for unrestricted sessions.] → The full
  `windows-validate` run covers them again.
- [An environment file could remain if the inner part never starts.] → It is
  mode 0600 in a mode-0700 directory on the runtime tmpfs, which a restart
  clears, and the next start removes it. The helper's tests check that a
  successful start leaves none and that the next start removes the file of a
  failed one.
- [Shared runtime tests assume delegated cgroup controllers, and an unguarded
  `AF_VSOCK`.] → Recorded as environment limits, as in phase 1; not changed
  here.
- [The guard now stays alive next to the application.] → It holds no proxy
  channel or standard input and output, runs under the same restrictions, and
  only waits, reaps and forwards. It exits as soon as the application exits.
- [A guard change touches every wrapper.] → It is shared code: a new reference
  tag, propagation, and the `--guard`, `--network` and `--qualification`
  runner modes before tagging.

## Migration Plan

Existing Windows installations keep their saved unrestricted preferences. The
first launch after the update runs in systemd's namespaces: containers that
phase 1 started from `/init`'s namespaces should be gone, because sessions
remove their containers on exit. A user who wants a restricted mode runs
`--container-setup` again. Rolling back to phase 1 makes the bootstrap refuse
saved restricted preferences, with the guidance to run setup again.

## Open Questions

None. The spike settled A1 to A6 (`docs/validation.md`, "Windows restricted
networking").
