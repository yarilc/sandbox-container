# Design

## Context

See proposal.md for the motivation and the decisions taken during exploration.
The current state that shapes the approach:

- The launcher core (`launcher/core.sh`) runs only on the Linux host of the
  engine and rejects named connections. Managed launches go through a Bash
  dispatcher written by setup (`~/.local/bin/<name>`), which runs
  `python3 -I <installation>/current/setup/launch.py`. `launch.py` checks the
  protected release and refuses writable mounts that overlap the installation
  or the managed command (`protect_mounts` in `setup/common.py`). It then
  runs the release's Bash entry.
- The Podman machine distribution (Podman 6.1.4, WSL provider) has Bash 5.3,
  Python 3.14 and GNU coreutils 9.10. It runs the rootless engine of `user`
  locally, with the `cgroupfs` manager. It has no systemd user manager, and its
  `XDG_RUNTIME_DIR` is `/mnt/wslg/runtime-dir`, which every distribution
  shares. Since `sandbox-ref-26`, budgets there are reported truthfully, and the
  process budget uses the rlimit fallback.
- Setup copies the `MANIFEST` inputs from the checkout into a new release, and
  already supports a checkout on a Windows mount ("Checkout on a Windows
  mount").
- Windows PowerShell 5.1 is the only PowerShell on a default Windows 11 Home
  installation. Its native argument passing drops empty strings and breaks
  embedded double quotes. Setting `$env:X = ''` deletes `X`. Text piped to a
  native command is re-encoded with `$OutputEncoding`.
- `launcher/` is a shared directory, so new files under `launcher/windows/`
  propagate with the reference tag. Files at the repository root, such as the
  entries and `.gitattributes`, do not.

## Goals / Non-Goals

**Goals:**

- One process chain from PowerShell to the unchanged core. Every data item
  crosses the Windows/WSL boundary in the environment, never on a command line.
- Shared code stays agent-neutral and platform-neutral. The only Windows
  branches are the new files and one optional protected path in `launch.py`.
- Everything except Windows PowerShell 5.1 itself is testable on Linux.

**Non-Goals:**

- Running the shim from a dedicated install folder, a PATH entry or a
  PowerShell profile function. That belongs to `add-windows-installer`.
- Any use of `podman.exe`, the machine's SSH connection, its API socket, or the
  WSLg runtime directory.
- PowerShell pipeline input.

## Decisions

### D1. Process chain

```
PowerShell 5.1 / 7
  <name>.ps1 (thin, identical)            Windows checkout
    -> launcher/windows/core.ps1 (shim)   reads agent/profile.json
         checks: modes, args, env names, pipeline input
         sets WRAPPER_WINDOWS_* + WSLENV for the child only
         wsl.exe -d <distro> -u <user> --exec /bin/sh -c 'cd && exec /bin/bash <bootstrap>'
-------------------------------------------------------- WSL boundary
  <installation>/current/launcher/windows/bootstrap.sh    release (ext4)
    decodes argv, translates cwd and entry dir (wslpath -a -u)
    cd <workspace>; exec <managed command> "${args[@]}"
      -> dispatcher -> python3 -I launch.py --managed-launcher ...
           protect_mounts(+ WRAPPER_WINDOWS_ENTRY)
           -> <name>.sh -> launcher/core.sh -> local rootless podman
```

Setup and help skip the bootstrap. They need no user data, so the shim runs
`wsl.exe -d D -u U --cd <checkout> --exec /bin/bash <name>.sh --container-setup`
(or `--container-help`). The only variable item on that command line is the
checkout path. It comes from `$PSScriptRoot`, cannot contain `"`, and the shim
refuses it when it is not a drive path or ends with `\`. This avoids the
PowerShell 5.1 quoting defects.

Alternatives considered:

- *Running the bootstrap from the checkout for every operation.* The checkout
  is on drvfs (0777) and is not a protected release. Setup already defines the
  release as the only code that runs launches.
- *The machine's SSH or API chain.* It is the part that fails with another
  distribution active.

### D2. Locating the release bootstrap

The shim starts `/bin/sh -c 'cd && exec /bin/bash <bootstrap>'` as the
selected user. `cd` without an operand changes to that user's home. The
bootstrap path is `.local/lib/<name>/current/launcher/windows/bootstrap.sh`,
relative to that home. When `<P>_WSL_INSTALLATION` is set, the path is
`<installation>/current/launcher/windows/bootstrap.sh`, and the installation
must match `^/[A-Za-z0-9._/-]+$`. `<name>` is validated by the profile rules
(`[a-z][a-z0-9-]*`), and the distribution and user names by
`^[A-Za-z0-9._-]+$`. Both path forms therefore need no quoting inside the fixed
shell command, which contains no `"` (Windows PowerShell 5.1 mangles embedded
double quotes in native arguments).

The spike ruled out `wsl.exe --cd ~`: PowerShell 7.7 replaces a `~` native
argument with the Windows profile directory, also inside a splatted array, so
the home-relative path failed with 127. Windows PowerShell 5.1 passes `~`
unchanged. The `cd &&` form started in `/home/user` on both versions.

The bootstrap reads the managed command path from its release's `setup.json`
with one `python3 -I` call, then executes that command. Daily launches
therefore go through the same dispatcher and `launch.py` checks as on Linux.

Alternative considered: *Calling the dispatcher at `~/.local/bin/<name>`
directly.* Setup lets the user change that path, and argument decoding must
happen before the dispatcher runs.

### D3. Argument and data transport

The shim sets, for the child process only:

| Variable | Content |
|---|---|
| `WRAPPER_WINDOWS_ARGS` | base64 of the UTF-8 arguments, each followed by NUL; unset when there are none |
| `WRAPPER_WINDOWS_CWD` | raw `ProviderPath` of the current FileSystem location |
| `WRAPPER_WINDOWS_ENTRY` | raw path of the entry's directory |
| `WSLENV` | exactly these names plus the forwarded ones, each with `/u` |

NUL termination distinguishes no arguments from one empty argument. Base64
keeps the value ASCII. The shim leaves the variable unset when there are no
arguments, and the bootstrap treats an empty value the same way. The bootstrap
validates the base64 alphabet, decodes the value with
`base64 -d`, splits it with `mapfile -d ''` (Bash 4.4 or later, checked), and
refuses data whose last record is not NUL-terminated.

The shim refuses an encoded value longer than 32766 characters before calling
WSL. In the spike, 32766 characters reached the distribution on both
PowerShell versions. Windows PowerShell 5.1 refuses 32767 characters or more
when setting the variable, while PowerShell 7.7 accepts any length, so the
shim's own check is the only one that applies to both. PowerShell arrays, from unquoted commas, are refused.
Other non-string values are converted with `[string]`.

Standard input is not transported: `wsl.exe` inherits it. The thin entry passes
`$MyInvocation.ExpectingInput` to the shim, which refuses PowerShell pipeline
input. Windows PowerShell 5.1 also sets `ExpectingInput` when `cmd.exe`
redirects standard input to `powershell -File <name>.ps1`, although the bytes
still reach `wsl.exe` unchanged (validation round 5). No PowerShell pipeline
can feed a script that the process runs with `-File`. So the shim accepts the
input when standard input is redirected and the process command line
(`[Environment]::GetCommandLineArgs()`) runs the entry itself with `-File`,
before any `-Command` or `-EncodedCommand`. `$MyInvocation.PipelineLength`
cannot tell these cases apart: it is 1 for `'text' | & $entry` too, because the
input expression is not a command.

The `WRAPPER_WINDOWS_` prefix is agent-neutral, like `WRAPPER_INVOKED`, so the
alignment test does not flag it. The user's own `WSLENV` is replaced rather
than extended, so unrelated Windows settings cannot change the launcher's
environment in the distribution.

Alternatives considered:

- *PowerShell 7.3 native argument passing.* It is unavailable on Windows
  PowerShell 5.1, and `wsl.exe` would still parse the command line.
- *An argument file on `C:`.* It needs cleanup, and other processes of the
  user could read it for a short time.

### D4. Forwarded names

The shim forwards these names:

- `<P>_*` names made of letters, digits and `_`, except `<P>_WSL_*`. Windows
  names may contain `:` or `/`, which would split `WSLENV` and import other
  variables, so other names get a notice instead;
- the profile's `config_dir_env`, only when its value is a distribution path
  (starting with `/`): users often set it to a Windows path for the native
  agent, which would stop every launch. The configuration directory saved by
  setup then applies, and the shim prints a notice;
- the profile's `approval_bypass_env`;
- the valid identifiers listed in `<P>_ENV_VARS`.

It never forwards these, and prints one notice for each one it skips:

- `WSLENV` and `WRAPPER_WINDOWS_*`;
- names that change how Bash, Python or the dynamic loader start: `BASH_ENV`,
  `ENV`, `SHELLOPTS`, `BASHOPTS`, `CDPATH`, `GLOBIGNORE`, `IFS`, `PS4`, `LD_*`
  and `PYTHON*`;
- the distribution's identity and engine selection: `PATH`, `HOME`, `USER`,
  `LOGNAME`, `SHELL`, `PWD`, `OLDPWD`, `TMPDIR`, `XDG_*`, `WSL_*`,
  `CONTAINER_*` and `CONTAINERS_*`.

A variable with an empty value is not forwarded. Windows PowerShell 5.1
removes a variable when it is assigned an empty value, while PowerShell 7.7 can
hold one. Skipping empty values gives both versions the same meaning: unset.

Saved preferences are not Windows variables: setup could save offline
networking or delegation if a service in the shared WSLg runtime directory
answered its probe. The bootstrap therefore refuses a release whose
`setup.json` selects anything but unrestricted networking without delegation.

The core applies its own reserved-name rules afterwards, as on Linux. Path
variables, such as `<P>_STATE_DIR`, are distribution paths and are not
translated: no `/p` flag.

### D5. Child environment and process call

The shim saves the previous value or absence of every variable it sets, calls
`& wsl.exe ...` and restores them in `finally`. A variable that was absent is
removed with `Remove-Item Env:<name>`. Passing `$null` to
`[Environment]::SetEnvironmentVariable` does not work: PowerShell converts it
to an empty string, and in the spike PowerShell 7.7 then kept the variable
defined and empty. The native call operator keeps the console handles,
terminal allocation, Ctrl+C delivery and `$LASTEXITCODE` exactly as for any
native command. The shim exits with that code.

Observed in the spike, on both versions unless stated:

- Ctrl+C reaches the Linux process as one SIGINT. `wsl.exe` returns 130,
  PowerShell continues the script and `finally` runs.
- Closing the window ends PowerShell without running `finally`. The session
  environment ends with it. On both versions the Linux process received one
  SIGHUP and kept running for the 12 s the probe was given after `wsl.exe` had
  ended. The core's HUP trap therefore completes the bounded shutdown (20 s
  deadline) in the distribution.

Alternative considered: *`System.Diagnostics.Process` with a private
environment.* It leaves the session untouched without restore logic. However,
`WaitForExit` blocks PowerShell's Ctrl+C handling, and console inheritance needs
more code. The spike showed restoration works with `Remove-Item`, so it is not
needed.

### D6. Distribution, user and installation diagnosis

Before a launch, setup or help, the shim runs `wsl.exe -l --running -q` with
`WSL_UTF8=1` and strips NUL characters, to cover older WSL versions that write
UTF-16. Only when the distribution is not listed there does it run
`wsl.exe -l -q`, to tell a stopped distribution from a missing one. Neither
call starts anything. A missing distribution is refused with the Podman
Desktop guidance. A stopped one is refused with `podman machine start`, and
help prints that guidance and exits with status 0.

The shim must not start a stopped distribution itself. `wsl.exe` would start
it without the Podman machine's own start sequence, which creates the user's
runtime directory `/run/user/<uid>`. In such a distribution every `podman`
command fails with status 125 (`mkdir /run/user/1000: permission denied`),
because the engine's database keeps the run root
`/run/user/1000/containers`. Round 3 of the validation hit this. The same
state remains after any other `wsl.exe` command starts the distribution, so
two checks refuse it before any Podman command:

- The bootstrap checks that `/run/user/<uid>` is a writable directory. This
  covers ordinary launches without another `wsl.exe` call. The tests replace
  that path in their copy of the bootstrap; the installed bootstrap has no
  override.
- Setup runs from the checkout, not through the bootstrap, so the shim first
  probes with `--exec /bin/sh -c 'test -d /run/user/$(id -u) -a -w
  /run/user/$(id -u)'`.

Both refusals ask the user to run `wsl --terminate <distro>`, then start the
machine with Podman Desktop or `podman machine start`. The shim does not run
`podman.exe` itself (non-goal).

User and installation problems are diagnosed only after a failure, so a normal
launch makes one more `wsl.exe` call than the launch itself:

- `wsl.exe` failing on its own (exit code -1) leads to a probe with
  `--exec /bin/true` as the user, which tells a missing user apart. In the
  spike a missing user and a missing distribution both gave -1, with
  `Wsl/WSL_E_USER_NOT_FOUND` or `Wsl/Service/WSL_E_DISTRO_NOT_FOUND` on stderr.
- Exit code 127 leads to a probe with
  `--exec /bin/sh -c 'cd && test -f <bootstrap>'`, which tells a missing
  installation apart. When the bootstrap exists, the 127 came from the session
  and is returned unchanged. A missing script gave 127 in the spike.

The probes capture `wsl.exe` output with `2>&1`, so they run with
`$ErrorActionPreference = 'Continue'` in their own scope. Under `Stop`, Windows
PowerShell 5.1 turns redirected native stderr into a terminating
`NativeCommandError`; PowerShell 7.7 does not. The launch call itself does not
redirect stderr.

Alternative considered: *the `HKCU:\...\Lxss` registry keys for the
distribution list.* They need no process, but they are an undocumented layout.

### D7. Working directory and entry directory translation (bootstrap)

The bootstrap classifies the raw Windows path before translation:

| Raw path | Result |
|---|---|
| `\\wsl$\...`, `\\wsl.localhost\...` | refused: path inside a WSL distribution |
| `\\?\...`, `\\.\...`, other `\\...` | refused: network or device path |
| `X:\...` | `wslpath -a -u`; refused naming the drive when the result is not an existing directory |
| anything else | refused: not a file system path |

The shim already refuses non-FileSystem providers such as `HKCU:`. The
bootstrap repeats the check, because it is the component that the shared tests
cover. The entry directory gets the same translation and must be on a drive.
The bootstrap exports the translated entry directory as
`WRAPPER_WINDOWS_ENTRY` and unsets the other two variables. It then runs `cd`
into the workspace. The core keeps using `pwd -P`, so the workspace rules apply
to the translated physical path.

### D8. Entry directory outside writable mounts (`launch.py`)

`protect_mounts` gains one optional path: `WRAPPER_WINDOWS_ENTRY` when set. It
reuses the existing overlap test against every writable mount: the workspace or
worktree parent, including the saved worktree preference, and the state or
configuration and shared directories. The test applies in both directions.
Under `/mnt/<letter>/` the comparison is case-insensitive.

The path gets no `trusted()` ownership check, because drvfs cannot pass one.
Its protection is that the session can never write to it.

Alternatives considered:

- *A check in the shim.* The shim cannot see the saved worktree preference or
  the state mounts.
- *A check in the core.* The managed-launch overlap rule already lives in
  `launch.py`.

### D9. Windows folders in the core

`core_workspace_refusal` lowercases the physical mount source and adds one
match:

```
^/mnt/[a-z](/users(/[^/]+(/documents|/onedrive( - [^/]+)?(/documents)?|/appdata(/.*)?)?)?|/windows|/program files( \(x86\))?|/programdata)$
```

`Documents` and `OneDrive` (or its `Documents`) hold the PowerShell profile
and modules, and `AppData` holds the startup folder: code written there runs
on Windows, outside the sandbox, so the whole `AppData` tree is refused, and
the other folders as exact roots. Projects below `Documents` stay accepted.

The match does not depend on WSL detection, so it also protects launches from
any distribution. The existing exact override applies unchanged.

### D10. Setup without a launch service

A new read-only probe runs before the network question. It checks candidate
endpoints in this order:

1. `CONTAINER_HOST`;
2. the saved endpoint;
3. the default endpoint.

Each candidate goes through `verify_socket`, with the existing timeout. The
probe then checks for a usable systemd user manager: `systemctl` is present
and `systemctl --user show-environment` succeeds. This factors the check that
`prepare_service` already uses.

When neither holds:

- setup explains the situation;
- it asks `Continue with unrestricted networking?` (default no) as the explicit
  selection;
- it sets `podman=False` and `endpoint='local'`, and skips the delegation and
  endpoint questions.

The local endpoint leaves `CONTAINER_HOST` unset in the smoke and launch
environments; an empty value is not enough, because Podman 6 then selects a
remote context and fails (seen on the machine, exit 125). The launcher also
unsets an empty `CONTAINER_HOST` or `CONTAINER_CONNECTION` before its first
engine query.

If the user declines, setup exits with status 1 and the generic guidance, which
points to the setup guide and names no socket path. `prepare_service` and
`manual_service` stay unchanged for hosts where a service exists or can be
started.

### D11. Line endings

- A `.gitattributes` with `* text=auto eol=lf` goes in the reference and in
  each wrapper.
- Setup scans each `MANIFEST` source for `b'\r'` before `copy_inputs` and
  stops on the first match. No tracked file contains CR today.
- The shim checks the three files Bash reads before setup's Python can run:
  the Bash entry, `launcher/core.sh` and `agent/launcher.sh`. Without this
  check, a CRLF entry would fail with `$'\r': command not found` before any
  explanation.
- A shared test scans the repository's text files and fails on CR.

### D12. Tests and tools

- **Bootstrap.** `tests/test_windows_bootstrap.py` is a new shared test and is
  added to `SHARED_TESTS`. It builds a temporary release containing the
  bootstrap, a `setup.json` and a fake managed command, which dumps argv, cwd
  and environment. A fake `wslpath` on `PATH` maps drive paths to temporary
  directories. Scenarios: decoding, including empty and non-ASCII arguments;
  every row of the D7 table; a malformed payload; Bash older than 4.4 through a
  stubbed version check; the unset transport variables.
- **`launch.py`.** The overlap tests go in `tests/test_setup.py`, using the
  existing protected-tree fixtures.
- **Core.** The Windows folders tests go in `tests/test_launcher.py`. Each one
  runs the entry inside `unshare -rm` with a tmpfs on `/mnt`, and skips without
  unprivileged namespaces, as the drive-root test skips without `/mnt`.
- **Setup.** The no-service rule and the CR refusal go in `tests/test_setup.py`
  and `tests/test_setup_wrapper.py`, with the fake engine and a missing or
  failing `systemctl` stub.
- **Shim.** `tools/powershell.sh <checkout>` is reference-only, like
  `tools/shellcheck.sh`. It builds or reuses a local tool image from
  `tools/powershell.Containerfile`: a digest-pinned
  `mcr.microsoft.com/powershell` base plus a pinned PSScriptAnalyzer package
  whose SHA-256 is verified at build time. It runs the image with
  `--network=none`, executes `Invoke-ScriptAnalyzer -Severity Warning` on the
  tracked `*.ps1` files, and runs `tests/windows/shim_tests.ps1`. That file is
  plain PowerShell with a small assert helper, so Pester, a second pinned
  module, is not needed. The tests run the real entry, with a fake `wsl.exe`
  first on `PATH`. The fake records argv and the variables `WSLENV` lists, and
  simulates `-l -q` output (UTF-8 and UTF-16) and exit codes.
- **Windows PowerShell 5.1.** `tools/windows-validate.ps1` is an operator
  script run on a real Windows host. It checks the scenario matrix, prints a
  summary for `docs/validation.md` and cleans up after itself.

### D13. Help text

The shim prints a short Windows section built from the profile:

- the `<P>_WSL_*` variables;
- the unrestricted-only limit;
- the pipeline-input limit.

It then runs the checkout's wrapper help in the distribution. When the
distribution is missing, it prints the Windows section and the machine
guidance, and exits 0.

## Risks / Trade-offs

- [Spikes may contradict defaults: Ctrl+C and window close through `wsl.exe`,
  `--cd ~` combined with `--exec`, exit codes, redirected stdin from `cmd`, and
  `--` consumed by PowerShell before `$args`.] → The spikes ran on Windows
  PowerShell 5.1 and PowerShell 7.7 (`docs/validation.md`). They replaced
  `--cd ~` (D2), fixed the size limit (D3), empty values (D4), restoration and
  window close (D5) and probe stderr (D6).
- [A Podman socket from another distribution under the shared
  `/mnt/wslg/runtime-dir` could answer the setup probe on the machine.] →
  Setup would then offer restricted modes. The smoke container, however, binds
  machine-only paths and fails, so no installation can be published that way.
  The Windows entry also refuses explicit restricted modes. Phase 2 must stop
  deriving the default endpoint from that directory.
- [The shim runs from a drvfs checkout that any Windows process of the user can
  modify.] → The trust level is the same as any user-installed script. The
  session cannot reach the checkout (D8). The installer change moves the shim
  to a dedicated folder.
- [Windows PowerShell 5.1 cannot hold empty variables, so a Windows user
  cannot express "set but empty" for `<P>_*`.] → An empty value means unset on
  both versions (D4). The help and the README state it.
- [PowerShell consumes a bare `--`, confirmed on both versions.] → The README
  says to quote it (`'--'`) when Bash must receive it.
- [`podman machine stop` (`wsl --terminate`) ends running sessions, and Podman
  Desktop shows the machine as stopped while `wsl.exe` alone runs its
  distribution.] → Documented; the entry refuses a distribution that Podman
  did not start (D6).
- [drvfs is slow on large trees, and Git for Windows clones with
  `core.autocrlf=true` look modified to Linux Git in the session.] →
  Documented with the `.gitattributes` and `core.autocrlf` advice for user
  projects.
- [The new Windows folder refusal changes behavior for WSL users who launch
  from a profile root today.] → The refused set is exact roots only, and the
  existing override applies. The validation record and README call out the
  change.
- [An update of the machine image could drop Bash 4.4+, Python 3 or base64.] →
  The bootstrap checks the Bash version and the tools it needs, and fails with
  the missing tool's name.
- [The `podman rm` timeout seen once on Podman 6.1.4.] → Ten interrupted
  sessions on Podman 6.1.4 ended with status 130 in about 2 s, with no leftover
  container and no timeout. No fix follows unless it reappears.

## Migration Plan

1. Work stays on `feature/windows-podman-machine`. `main` is merged in at every
   new reference tag.
2. Existing Linux and WSL installations need no action. A rerun of setup applies
   the CR check and the no-service rule. Launches from exact Windows profile or
   system roots are refused unless the override is set.
3. Existing Windows clones made before `.gitattributes` existed need one LF
   re-checkout. In a clean checkout, run
   `git rm -r -q --cached . && git reset --hard`, or clone again.
   `git add --renormalize .` only fixes the index, not CRLF working files. The
   shim and setup name that step.
4. When the branch merges into `main`, the merge commit gets a new
   `sandbox-ref-N` tag. The validation section and the parity cell name it.
   Each wrapper adopts it and copies `<wrapper>-container.ps1` and
   `.gitattributes`, as `docs/propagation.md` will list.
5. Rollback: Windows support is additive. On Linux, setup's last-working-release
   rollback is unchanged. On Windows, removing the machine distribution or the
   installation is enough.

## Open Questions

- The PSScriptAnalyzer rules to exclude, if any, for example
  `PSAvoidUsingWriteHost` if the help output needs it. This is settled when the
  tool first runs.
- Whether `wsl.exe` returns -1 for every failure of its own, or uses other
  codes too. This only refines the D6 probes.
