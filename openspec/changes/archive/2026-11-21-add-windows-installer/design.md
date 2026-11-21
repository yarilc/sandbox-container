# Design

## Context

- The Windows entry (`<name>.ps1`) and the shim (`launcher/windows/core.ps1`)
  run from wherever the user put the checkout. Setup and help run that
  checkout's Bash entry inside the machine distribution with
  `wsl.exe --cd <entry directory>`. Launches run the release bootstrap and pass
  the entry directory as `WRAPPER_WINDOWS_ENTRY`, so that no writable mount
  contains it (archived change `support-windows-podman-machine`, D8).
- Setup copies the files in `MANIFEST` (`setup/common.py`) into each release.
  That list depends on the profile: the wrapper's Bash entry, the profile and
  policy files, and the profile's `install.files`.
- Since task 10.1 of that change, every folder inside a profile's `AppData` is a
  refused workspace, so a launch never mounts `%LOCALAPPDATA%\Programs`.
- The validation saw two things: a WSL process can keep, as its current
  directory, a Windows folder that a session or setup started from, until
  `wsl --shutdown`; and an antivirus can quarantine individual files while
  they are written.
- Windows PowerShell 5.1 runs on .NET Framework, so `File.Move` has no
  overwrite flag. `Environment.SetEnvironmentVariable(..., 'User')` writes a
  `REG_SZ`, which would stop `%VAR%` references in the user's `PATH` from
  expanding.

## Goals / Non-Goals

**Goals:**

- One command from a checkout or a downloaded folder that copies, sets up and
  exposes the sandbox. The copy keeps working after the source is deleted.
- Shared, agent-neutral installer code, tested on Linux like the shim. The
  only parts that need Windows are the registry access and the broadcast.
- No state that the next install cannot repair.

**Non-Goals:**

- Versioned side-by-side installs or rollback on the Windows side. The
  machine installation already keeps releases and rolls back.
- Installing prerequisites (WSL, Podman Desktop, the machine).
- Removing the machine installation. Linux setup has no uninstall either.

## Decisions

### D1. Installer as shim options, in a separate script

The shim recognizes `--container-install` and `--container-uninstall`. Each
must be the only argument, like `--container-setup`. The shim runs the shared
checks first: line endings, the machine state and its runtime directory. It
then calls `launcher/windows/install.ps1` with the entry directory, the
profile values and the action. The installer code stays out of every launch,
and the thin entry does not change.

Alternative considered: *a separate `install.ps1` at the root of each
wrapper.* It adds a per-wrapper file that propagation does not copy, and it
duplicates the shim's checks.

### D2. Payload from setup's manifest

The installed copy holds `MANIFEST` and the Windows-only files: `<name>.ps1`
and `launcher/windows/*.ps1`. To get `MANIFEST` without a second list,
`setup/common.py` gains a `--manifest` mode that prints the list
NUL-separated. The installer runs it in the distribution, from the source:

```
wsl.exe -d <distro> -u <user> --cd <source> --exec python3 -I setup/common.py --manifest
```

Each name must be relative and contain no `..`, and the source file must be a
regular file and not a reparse point. Otherwise the install stops before it
writes anything. Every payload file is checked for carriage returns, with the
same message as setup.

Alternatives considered:

- *A second list in PowerShell.* It would drift from `MANIFEST`, which changes
  with every profile.
- *Copying the whole checkout.* That includes tests, docs and `.git`, none of
  which setup needs.

### D3. Layout, lock and atomicity

| Path | Content |
|---|---|
| `%LOCALAPPDATA%\Programs\<name>\` | the payload, at the same relative paths as in the source |
| `%LOCALAPPDATA%\Programs\<name>\install.json` | `state` (`incomplete` or `complete`), the file list, the source path, the time |
| `%LOCALAPPDATA%\Programs\<name>.lock` | exclusive lock while an install or uninstall runs |

`LOCALAPPDATA` comes from the environment, which Windows always sets. Only
when it is unset does the installer fall back to `GetFolderPath`. The tests use
the environment value to point it at a temporary folder.

The order is:

1. Take the lock: a `FileStream` with `FileShare.None` and
   `DeleteOnClose`. A second install or uninstall fails with status 1.
2. Run the checks of the `windows-installation` spec.
3. Write `install.json` with `state: incomplete`.
4. For each file, write the bytes read from the source to `<file>.new`, verify
   them by SHA-256, then replace the target. 5.1 has no overwrite flag on
   `File.Move`, so the installer uses `File.Replace` when the target exists
   and `File.Move` otherwise.
5. Remove the files that the previous `install.json` listed and the new
   payload does not.
6. Rewrite `install.json` with `state: complete`.

The shim refuses launches and setup when its own folder has an
`install.json` that is not `complete`. Help and uninstall stay available.

The installer replaces files one by one instead of swapping the whole folder.
A folder swap needs a rename, and a rename fails while a WSL process keeps the
folder as its current directory, as setup's `--cd` can cause. A per-file
replace is still not atomic, which is why the `incomplete` marker and the
refusal exist.

### D4. Fresh local files

The installer reads source bytes and writes new files. It does not use
`Copy-Item`, which keeps alternate data streams on NTFS. The installed copy
therefore has no Mark of the Web and runs under `RemoteSigned`. This is the
behavior of any installer: running it is the trust decision, and the README
says so. The SHA-256 check in D3 also catches a file that an antivirus removed
or changed while it was written. The installer then stops and names the file.

### D5. User PATH

`launcher/windows/user-path.ps1` defines functions only:

- pure string functions that add or remove one entry. They split on `;`,
  compare case-insensitively after `%VAR%` expansion and a trailing `\` trim,
  and leave every other entry byte for byte;
- `Get-UserPath` and `Set-UserPath`. They read `HKCU\Environment\Path` with
  `DoNotExpandEnvironmentNames`, keep its value kind (`ExpandString` for a new
  value), write it back, and broadcast `WM_SETTINGCHANGE` ("Environment") with
  `SendMessageTimeout` through `Add-Type`.

The installer prints the folder it adds before writing, and also adds it to the
current session's `$env:Path`. It refuses a resulting value longer than 32766
characters. When `Add-Type` is blocked, for example in Constrained Language
Mode, the value is still written, and the message says to sign out and back in.

Alternatives considered:

- *`[Environment]::SetEnvironmentVariable('Path', ..., 'User')`.* It writes a
  `REG_SZ` and breaks `%VAR%` entries.
- *A function in the PowerShell profile.* It writes into `Documents`, which
  holds the profile and is a refused workspace because Windows runs user code
  there.

### D6. Setup after the copy

When the copy is complete, the shim runs the installed entry's own
`--container-setup` in the same process, so setup reads the installed copy.
It then prints that new PowerShell windows can run `<name>` from a project
directory. When setup fails, the copy and the `PATH` entry stay, and the
message names `<name> --container-setup`.

### D7. Refusals specific to installs

- **The source is the install folder or lies inside it.** Reinstalling from
  the installed copy would copy files onto themselves, so updates come only
  from a newer source.
- **The install folder or its parent is a reparse point.** Writing through a
  junction could land anywhere. The check uses the `ReparsePoint` attribute,
  which .NET also reports for symlinks on Linux, so the tests cover it.
- **The install folder belongs to another user.** The owner from `Get-Acl`
  must be the current user's SID. This check runs only on Windows.
- **The install folder exists, is not empty and has no `install.json`.** The
  installer did not create it, so it may hold the user's own files.

### D8. Uninstall

Uninstall takes the lock, then:

1. removes the `PATH` entry;
2. deletes the files that `install.json` lists, the `__pycache__` folders
   beside them that hold only `.pyc` files (setup runs Python from the
   installed copy, round 8), then `install.json`, then the empty folders;
3. reports what could not be deleted, with `wsl --shutdown` as the way to
   release a folder still in use, and exits with status 1 in that case.

It names the machine installation (`~/.local/lib/<name>` and the managed
command), which stays until the machine is reset. It works from the installed
copy and from a checkout. PowerShell reads a script whole before running it,
so the installed entry can delete its own files.

### D9. Tests

- `tests/windows/shim_tests.ps1` sets `LOCALAPPDATA` to a temporary folder.
  The fake `wsl.exe` answers the manifest query from `FAKE_WSL_MANIFEST`. The
  synthetic checkout's `user-path.ps1` keeps the real string functions and
  replaces `Get-UserPath` and `Set-UserPath` with a file store. The cases cover:
  - install, update and uninstall;
  - an interrupted copy (a fake that fails mid-list);
  - the lock, a reparse-point target and a source inside the target;
  - a CRLF source, a refused combination of arguments, and the `PATH`
    strings: duplicates, `%VAR%` entries and a trailing `\`.
- A Python test checks that `setup/common.py --manifest` prints `MANIFEST`
  exactly, NUL-separated.
- `tools/windows-validate.ps1 -Install` covers what needs Windows: it installs,
  checks the registry value and its kind, launches `<name>` from a project in a
  child that reads the new `PATH`, then uninstalls. It refuses to start when an
  installation already exists.

## Risks / Trade-offs

- [The window that ran the install may not find the command, for example
  after `powershell -ExecutionPolicy Bypass -File ...`, which runs the install
  in a child process.] → The message says to open a new window or Terminal
  tab. In round 8, new Windows Terminal tabs found the command without a
  Terminal restart.
- [A WSL process keeps a folder of the installed copy in use.] → Files are
  replaced one by one, and uninstall reports the folder with `wsl --shutdown`.
- [An antivirus quarantines a payload file.] → The SHA-256 check stops the
  install and names the file. The copy stays `incomplete`, so the shim
  refuses launches until the install completes.
- [Unsigned scripts under policies stricter than `RemoteSigned`.] → They are
  unsupported and documented. `AllSigned` needs signing, which is out of
  scope.
- [The user's `PATH` is close to the size limit.] → The installer refuses
  before writing and names the limit.
- [The lock covers installs and uninstalls, not a setup or launch that runs
  from the installed copy while an update replaces its files.] → Documented in
  the contract and the README: run updates when no setup runs from the copy.
  The `incomplete` marker refuses only setups and launches that start during
  the copy.
- [The manifest query runs Python from the source on drvfs inside the
  distribution.] → Setup already runs the source's Bash and Python there. A
  source that is not on a drive is refused, as it is for setup.

## Migration Plan

Checkouts keep working without an install. Installing adds the folder and
the `PATH` entry, and uninstalling removes both. Wrappers receive the installer
with the next reference tag. No per-wrapper file is added.
