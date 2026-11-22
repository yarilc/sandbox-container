# Proposal

## Why

On Windows the sandbox runs only with unrestricted networking (phase 1,
`support-windows-podman-machine`). `offline` is the reference's default mode,
and `provider` is what the agent wrappers need to reach their model provider
through the egress proxy. Neither works on a Podman machine today.

Restricted modes need a same-host Unix launch service. The spike of this
change (task group 1) found the following on the machine:

- **The service exists.** The machine serves a rootless API at
  `/run/user/<uid>/podman/podman.sock`: `podman.socket` is activated by the
  user's systemd manager, persists across a restart of the distribution, and
  passes the platform rules (Netavark, Podman 6.1.4, x86_64, seccomp,
  Landlock ABI 3).
- **Setup does not find it.** Setup looks at
  `$XDG_RUNTIME_DIR/podman/podman.sock`. In a `wsl.exe` session that is
  `/mnt/wslg/runtime-dir`, a directory that every WSL distribution shares.
- **Sessions live in other namespaces.** The machine runs systemd, and with
  it the service, in PID and mount namespaces of its own (`unshare --pid
  --mount`). The machine's login shells enter them with
  `/usr/local/bin/enterns` (`sudo nsenter`), but the entry's
  `wsl.exe --exec` sessions do not.

As a result, the session's podman and the service use two different rootless
user namespaces on the same storage:

- a container that the service started is listed by the session's podman, but
  `podman exec` fails with "container is not running";
- with the machine's runtime directory, both sides replace each other's
  `pause.pid` on every command;
- the same split already exists for phase 1: Podman Desktop and `podman.exe`
  reach the service, not the sandbox sessions' namespace.

Inside systemd's namespaces everything is consistent, as measured in the
spike:

- one rootless user namespace for the session and the service;
- `systemctl --user` works;
- setup finds the service;
- the bind paths of `/mnt/c`, the home directory and `/run/user/<uid>` match.

This change makes the machine a supported host for `offline` and `provider`
by running the sessions and setup that the entry starts in those
namespaces.

## What Changes

- **Spike first** (done; tasks 1.1 to 1.3). It covered:
  - the service, its persistence and rootless state;
  - the bind paths and the namespaces;
  - the platform facts;
  - two ways into systemd's namespaces;
  - the restricted runner modes inside them.
- **Sessions and setup in the machine's systemd namespaces.** A new
  Windows helper enters them as the machine's own `enterns` does: `sudo -n
  nsenter --mount --pid`, then `sudo -n -u <user>` back to the user. It keeps:
  - the environment, carried in a private file under `/run/user/<uid>` that
    the inner part reads and removes;
  - the working directory;
  - the standard streams and the exit status.

  It sets `XDG_RUNTIME_DIR=/run/user/<uid>`. Unrestricted sessions take the
  same way, which closes the phase 1 split. Without passwordless `sudo`, the
  entry stops with guidance before any Podman command.
- **Restricted modes on Windows.**
  - The entry accepts `<P>_NETWORK=offline` and `provider`, as far as the
    profile allows them, and `--container-qualify`.
  - Setup offers them when the service answers, or when the user manager can
    start it.
  - The bootstrap accepts saved restricted modes.
  - Podman delegation stays refused on Windows, both from the environment and
    from saved preferences.
- **Interrupts in restricted sessions (shared guard).** The Windows run of
  task 5.2 showed that Ctrl+C does not end a restricted `-c 'sleep 60'`: the
  guard executes the application as PID 1 of the container, without the
  `--init` that unrestricted sessions have, and a PID 1 without a SIGINT
  handler ignores the signal. The same happens on Linux. After confinement the
  guard becomes a minimal init:
  - it runs the application as its child, in a process group that becomes the
    terminal's foreground group;
  - it forwards the signals it receives, reaps orphans, and exits with the
    application's status.
- **Setup endpoint default.** When a restricted mode is chosen and the saved
  endpoint is `local`, as after a phase 1 setup, setup proposes `default`.
- **Documentation and validation.**
  - Update the Windows section of the README and of `docs/setup.md`, the
    contract, the test map, and `tools/windows-validate.ps1`, whose mode cases
    change from refusals to launches.
  - Run the restricted runner modes inside the machine.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `windows-launcher`:
  - "Ordinary launches run the managed installation in the machine
    distribution" now runs in systemd's namespaces and allows the
    distribution's own launch service for restricted modes;
  - "Only unrestricted networking without delegation" becomes "Network modes
    from setup, without delegation";
  - "Saved preferences limited to unrestricted networking" becomes "Saved
    delegation refused";
  - a new requirement runs sessions and setup in the machine's systemd
    namespaces.
- `network-egress`: a new requirement runs the application under a confined
  init in restricted sessions.
- `container-setup`: a new requirement proposes a service endpoint for
  restricted modes.

## Impact

- Windows files:
  - a new helper `launcher/windows/enter.sh`, part of the release and of the
    checkout;
  - `launcher/windows/core.ps1`: mode refusals, help, and setup through the
    helper;
  - `launcher/windows/bootstrap.sh`: the managed command through the helper,
    and the check on saved preferences;
  - `tests/windows/shim_tests.ps1`, `tests/test_windows_bootstrap.py`, a new
    helper test, and `tools/windows-validate.ps1`.
- Shared code:
  - `setup/common.py` lists the helper among the release files;
  - `network/guard.c` runs the application as a child; the guard's digest
    changes, so existing restricted installations requalify after a setup
    refresh, while the guard revision stays (enforcement is unchanged);
  - `setup/setup.py` proposes the endpoint;
  - both need a new reference tag and propagation to the wrappers, with the
    `--guard`, `--network`, `--qualification`, `--setup` and
    `--setup-runtime` runner modes.
- Runner modes inside the machine: `--guard`, `--qualification`, `--network`
  and `--setup-runtime`. They need the guard toolchain image, built in the
  machine, and the pinned bases of the toolchain and proxy images.
- Behavior change for phase 1: unrestricted sessions also run in systemd's
  namespaces. Ctrl+C, window close, exit status, standard input and the
  terminal are validated again through the entry.
- Out of scope:
  - Podman delegation on Windows;
  - a launch service in the WSLg runtime directory for other WSL distributions
    (a separate Linux concern);
  - macOS;
  - shared runtime tests that assume delegated cgroup controllers or an
    unguarded AF_VSOCK, which fail on the machine's `cgroupfs` engine. They
    are recorded, not changed;
  - a change of the guard's enforcement (Landlock, seccomp, multiplexing).
