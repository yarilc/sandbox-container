# Proposal

## Why

On Windows, every session currently starts from a checkout:
`C:\...\sandbox-container\sandbox-container.ps1`, typed with its full path
from each project directory. The checkout has to stay in place, on drvfs,
where any Windows process of the user can modify the shim that starts the
sandbox. Phase 1 (`support-windows-podman-machine`) left a dedicated install
folder and a command on the `PATH` to this change.

## What Changes

- **Install from a checkout or a downloaded copy.** A new option,
  `<name>.ps1 --container-install`, given alone, copies a self-contained
  payload into a per-user folder, `%LOCALAPPDATA%\Programs\<name>`. The
  payload holds the thin entry, the shared Windows scripts, and every input
  that setup copies into a release. It then runs setup from that copy in the
  Podman machine, as `--container-setup` does today. Once it is installed, the
  checkout or downloaded folder can be deleted. The payload list comes from
  setup's own manifest, so there is one list to maintain.
- **Command on the user's `PATH`.** The installer adds the install folder to
  the user's `PATH` (`HKCU`, no administrator rights), keeps the existing
  entries and their `%VAR%` references, and announces the change to new
  windows. In any later PowerShell window, `<name>` starts a session from the
  current project directory. Unlike setup on Linux, which only prints `PATH`
  guidance, this changes the user environment, and the installer says so
  before it does.
- **Updates.** Running `--container-install` from a newer checkout replaces
  the installed copy and reruns setup. Running it from the installed copy
  itself is refused. A failed or interrupted copy leaves a state that the
  next install repairs, and two installs never run at once.
- **Uninstall.** `<name> --container-uninstall`, given alone, removes the
  `PATH` entry and the installed copy, and says that the installation inside
  the Podman machine stays until the machine is reset. A folder that is still
  in use, for example by a WSL process, is reported, not forced.
- **Checks before writing.** Install refuses, before changing anything:
  - a source with CRLF line endings, as setup does;
  - a stopped machine, or one that `wsl.exe` alone started;
  - a source inside the install folder;
  - a target that is not owned by the current user or is a reparse point.
- **Trust and execution policy.** Scripts stay unsigned. The installer writes
  new local files, so the installed copy runs under the default
  `RemoteSigned` policy. A downloaded copy still carries the Mark of the Web,
  so the README tells the user to run the first install with
  `-ExecutionPolicy Bypass` or after `Unblock-File`. Running the installer is
  the trust decision.
- **Help and documentation.** The Windows help lists both options. The README,
  the setup guide and the contract describe the install flow, updates,
  uninstall and the `PATH` change. `tools/windows-validate.ps1` gains an
  install, launch and uninstall cycle.

## Capabilities

### New Capabilities
- `windows-installation`: the per-user installation of the Windows entry. It
  covers the self-contained payload, the install folder, the `PATH` entry,
  updates from a newer source, uninstall, and the checks that run before any
  change.

### Modified Capabilities
- `windows-launcher`: help lists the install and uninstall options;
  `--container-install` and `--container-uninstall` must be used alone, like
  `--container-setup`; the line-ending check also runs before an install; and
  setup also runs from the installed copy.
- `shared-launcher`: the shared Windows files include the installer scripts,
  which are copied from the reference tag and contain no agent identifier,
  like the shim.

## Impact

- New shared files under `launcher/windows/`: the installer logic and a small
  user-`PATH` helper. The shim changes too, and `setup/common.py` gains a mode
  that prints its manifest, which makes the `--setup` runner modes required
  before tagging. The thin entry and `docs/propagation.md` do not change:
  wrappers receive the installer with the next reference tag.
- `tests/windows/shim_tests.ps1` gains install, update and uninstall cases
  against a temporary `LOCALAPPDATA`. `tests/test_alignment.py` scans the new
  files.
- The README's Windows section, `docs/setup.md`, `docs/launcher-contract.md`,
  `docs/launcher-test-map.md` and `tools/windows-validate.ps1` change.
- The user's Windows environment changes: one folder under
  `%LOCALAPPDATA%\Programs` and one `PATH` entry. Nothing is written in the
  PowerShell profile or system-wide.

Out of scope: code signing, packaging (zip releases, winget, MSI), a `.cmd`
launcher for `cmd.exe`, removal of the installation inside the Podman machine,
and macOS.
