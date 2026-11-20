# Proposal

## Why

Windows users with Podman Desktop cannot use the sandbox. The launcher
requires the engine on the same Linux host and rejects named connections, and
Podman machine is listed as unsupported. Running the wrapper from another WSL
distribution is not an option either. With an Ubuntu distribution active, the
machine's access chain fails: SSH connects, but the rootless API socket inside
the machine does not exist, because the machine distribution runs without
systemd as PID 1 and has no user manager. Spikes on Podman 6.1.4 (WSL provider)
showed that the machine distribution itself is a usable host for the
unchanged launcher core. It provides Bash 5.3, Python 3.14 and GNU
coreutils 9.10. Its local rootless engine works without that chain, and
binds of `/mnt/c` workspaces with `--userns=keep-id` work. Since
`sandbox-ref-26`, budgets on its `cgroupfs` engine are reported truthfully and
the process budget uses the rlimit fallback.

This is phase 1 of Podman machine support: Windows, unrestricted networking
only. It lives on the `feature/windows-podman-machine` branch until it is
mature enough to merge.

## What Changes

- **Windows entry.** A thin PowerShell entry per wrapper (`<wrapper>.ps1`,
  identical in every wrapper, like the Bash entry) runs a shared shim
  (`launcher/windows/core.ps1`). The shim runs the unchanged core inside the
  Podman machine's WSL distribution through `wsl.exe --exec`. It needs no other
  distribution and does not use the machine's SSH or API chain, so it works
  with other WSL distributions active.
- **Installation flow.** `<wrapper>.ps1 --container-setup` runs the existing
  setup from the Windows checkout inside the machine distribution. The
  protected installation, preferences, image and managed launcher live there,
  on its ext4 file system. Daily launches call the managed installation. When
  the installation is missing, for example after the machine was reset, the
  shim asks the user to rerun setup.
- **Argument and environment transport.** The shim encodes the arguments as
  NUL-separated UTF-8 in base64 and passes them in a variable forwarded through
  `WSLENV`, together with the `<P>_*` variables and the names listed in
  `<P>_ENV_VARS`. A fixed bootstrap (`launcher/windows/bootstrap.sh`) decodes
  them, so the `wsl.exe` command line carries no user data. Arguments larger
  than the Windows variable limit fail with a clear error.
- **Working directory.** The shim passes the raw Windows path. The bootstrap
  translates it with `wslpath -a`. UNC paths, drives not mounted in the
  distribution and paths inside other WSL distributions are refused with a
  specific message.
- **Code outside the sandbox stays out of reach of the session.** Daily
  launches run the bootstrap only from the protected release in the
  distribution. Checkout scripts run in the distribution only for
  `--container-setup` and help. A launch is refused when its workspace, a
  worktree parent or another writable mount overlaps the shim's own
  directory.
- **Supported modes.** Phase 1 supports unrestricted networking without Podman
  delegation. The shim refuses other network modes and
  `<P>_PODMAN=1` with a message about the platform. Setup also gains a generic
  rule: when no same-host Unix service is reachable and none can be started
  (no usable systemd user manager), it offers only `unrestricted` and explains
  why, instead of defaulting to `offline` and ending in service instructions
  that cannot be applied.
- **Sensitive Windows folders.** The core refuses, as exact workspace roots
  matched case-insensitively, `/mnt/<drive>/Users`, every profile
  `/mnt/<drive>/Users/<name>`, its `AppData`, `/mnt/<drive>/Windows`,
  `/mnt/<drive>/Program Files`, `/mnt/<drive>/Program Files (x86)` and
  `/mnt/<drive>/ProgramData`. The existing unsafe-workspace override applies.
  This also protects users who run the wrapper from any WSL distribution.
- **Machine selection.** The defaults are the `podman-machine-default`
  distribution and the `user` account, overridable with
  `<P>_WSL_DISTRO` and `<P>_WSL_USER`. The installation is expected at the
  setup default in that user's home, or at `<P>_WSL_INSTALLATION` when setup
  used another directory. A missing distribution or user fails with guidance
  to create the machine with Podman Desktop. A stopped machine fails with
  guidance to start it with Podman, because `wsl -d` would start the
  distribution without the user's runtime directory, where no `podman` command
  works.
- **Line endings.** Each repository gets a `.gitattributes` that keeps scripts
  LF. Setup refuses release files that contain carriage returns and says why.

Details settled with defaults, to be confirmed by spikes during implementation:
terminal, setup prompts, Ctrl+C and window close (INT/HUP) and exit codes
through `wsl.exe`; stdin from Windows PowerShell 5.1 pipelines, which convert
text and will likely be a documented limitation; and the `podman rm` timeout
seen once during cleanup on Podman 6.1.4.

To be documented: Git for Windows clones seen by Linux Git in the container
(`core.autocrlf` is global on Windows), drvfs performance on large trees, the
machine shown as stopped in Podman Desktop while a session runs, and
`podman machine stop` ending sessions.

Out of scope: the Windows installer (a separate change on the same branch),
PowerShell execution policy and script signing, restricted networking and
delegation on the machine, and macOS. A later restricted-mode phase must never
derive sockets or runtime directories from the machine's `XDG_RUNTIME_DIR`,
which is the WSLg directory shared by every distribution.

## Capabilities

### New Capabilities

- `windows-launcher`: the Windows entry and shim. It covers machine and user
  selection, argument and environment transport, working-directory
  translation, refusal of unsupported paths and modes, the bootstrap from the
  protected release, and setup started from a Windows checkout.

### Modified Capabilities

- `workspace-mounts`: "Sensitive workspace roots are refused" adds the Windows
  system and profile folders under WSL drive mounts, matched
  case-insensitively.
- `container-setup`: setup offers only unrestricted networking when no
  same-host service is reachable or startable, and refuses release files with
  carriage returns.
- `shared-launcher`: the shared launcher gains the Windows shim and bootstrap,
  and every wrapper gains an identical thin PowerShell entry. Their checks are
  PSScriptAnalyzer, ShellCheck and the shared tests.

## Impact

- Shared files, which need a new `sandbox-ref-N` tag after merging:
  `launcher/windows/core.ps1`, `launcher/windows/bootstrap.sh`,
  `launcher/core.sh` (sensitive Windows folders), `setup/` (network choice
  without a service, carriage-return check, bootstrap in the release) and the
  shared tests.
- Per wrapper: the new `<wrapper>.ps1` entry and `.gitattributes`. The adoption
  steps in `docs/propagation.md` must name them, because propagation copies
  only shared directories.
- Tests: Linux unit tests for the bootstrap and the new core rules. The shim is
  checked with PSScriptAnalyzer and logic tests in a digest-pinned PowerShell
  container (PowerShell 7). Windows PowerShell 5.1 is validated on a real
  Windows host by the operator.
- Documentation: a Windows section in the README and setup guide. The "Podman
  Machine unsupported" statements change to "supported on Windows,
  unrestricted only".
- The `feature/windows-podman-machine` branch merges `main` at every new
  reference tag to limit drift in the shared files.
