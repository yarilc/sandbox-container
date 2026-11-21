# Tasks

## 1. Manifest for the installer

- [x] 1.1 Add a `--manifest` mode to `setup/common.py` that prints `MANIFEST` NUL-separated and exits 0, with no other output or side effect (design D2). Add a `tests/test_setup.py` case that runs `python3 -I setup/common.py --manifest` from the checkout and compares the output with `common.MANIFEST`. Verify: the case passes, and `tests/test_setup.py` and `test_setup_wrapper.py` still pass.

## 2. User PATH helper

- [x] 2.1 Write `launcher/windows/user-path.ps1`, which defines functions only (design D5):
  - the pure functions that add or remove one entry;
  - `Get-UserPath` and `Set-UserPath`, which keep the registry value kind and broadcast `WM_SETTINGCHANGE`, with the Constrained Language Mode fallback message.

  Verify: shim-test cases that dot-source the file cover duplicates, case differences, `%VAR%` entries, a trailing `\`, empty segments and removal of the last entry, and PSScriptAnalyzer reports nothing.

## 3. Installer script

- [x] 3.1 Write `launcher/windows/install.ps1` for the install action (design D3, D4, D7):
  - take the lock;
  - query the manifest through `wsl.exe`, validate the names and check every payload file for carriage returns;
  - refuse a source inside the target, a reparse-point target or parent, and (on Windows) a target owned by another user;
  - write `install.json` as `incomplete`, write fresh files through `<file>.new` with a SHA-256 check, replace them (`File.Replace` or `File.Move`), and remove files that the previous list had and the new one does not;
  - mark `install.json` `complete` and update the `PATH` through `user-path.ps1`, announcing the change first.

  Verify: shim-test cases cover a first install, an update that removes a dropped file, an interrupted copy, a second concurrent install, a CRLF source, a source inside the target and a symlinked target, with the fake `wsl.exe` answering from `FAKE_WSL_MANIFEST` and `LOCALAPPDATA` set to a temporary folder.
- [x] 3.2 Add the uninstall action (design D8): remove the `PATH` entry, delete the listed files, `install.json` and empty folders, report what remains with `wsl --shutdown`, and name the machine installation that stays. Verify: shim-test cases cover uninstall from the installed copy and from a checkout, a missing installation, and a file that cannot be deleted (status 1, the `PATH` entry removed).

## 4. Shim integration

- [x] 4.1 In `launcher/windows/core.ps1`:
  - accept `--container-install` and `--container-uninstall` only alone;
  - run the line-ending, machine and runtime-directory checks before an install;
  - call `install.ps1`, then the installed entry's `--container-setup`, and print the next step;
  - refuse launches and setup from a folder whose `install.json` is not `complete`, keeping help and uninstall available;
  - list both options in the Windows help.

  Verify: shim-test cases cover each `windows-launcher` and `windows-installation` scenario that needs no Windows: options with other arguments, an install from the installed copy, setup failing after the copy, an incomplete copy refusing a launch, and help listing the options.
- [x] 4.2 Extend `tests/test_alignment.py` so that the identifier scan and the ASCII check cover `launcher/windows/install.ps1` and `user-path.ps1`. Verify: the alignment tests pass, and an identifier injected into either file is reported.

## 5. Documentation

- [x] 5.1 Document the installer:
  - the README's Windows section: install, the `PATH` change, updates, uninstall, unsigned scripts, the Mark of the Web with `-ExecutionPolicy Bypass` or `Unblock-File`, and new windows versus Windows Terminal;
  - `docs/setup.md`: setup from the installed copy;
  - `docs/launcher-contract.md`: the shim options, the installer steps and the layout;
  - `docs/launcher-test-map.md`: the new cases.

  Verify: the README commands match the shim's help, and no document says that the checkout must stay after an install.

## 6. Windows validation

- [x] 6.1 Add `-Install` to `tools/windows-validate.ps1` (design D9): it refuses to start when an installation exists; it installs from the checkout, checks the registry value and its kind, runs `<name> -c 'printf ok'` from a project in a child with the new `PATH`, and checks an install refused from the installed copy; then it uninstalls and checks that the `PATH` and the folder are gone. Verify: PSScriptAnalyzer passes, and a PowerShell 7 dry run against the fake `wsl.exe` completes.
- [x] 6.2 Have the operator run `tools/windows-validate.ps1 -Install` from a checkout on Windows PowerShell 5.1 and on PowerShell 7, with a started machine. Have them also check by hand that a new PowerShell window started from the Start menu runs `<name>`, and that a downloaded zip installs with `-ExecutionPolicy Bypass`. Verify: the results are recorded in `docs/validation.md` under a new "Windows installer (pending tag)" section, with every scenario passed or a limitation that the README states.

## 7. Integration checks

- [x] 7.1 Run the shared suites, `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .`, `git diff --check`, and the runner modes that `docs/propagation.md` requires for the changed shared files (`--shared`, `--setup`, `--setup-runtime`, `--qualification`). Verify: every result is recorded in the validation section, with no new failure compared with the branch head before this change.

## 8. Code review follow-up

- [x] 8.1 Harden `launcher/windows/install.ps1`:
  - names read back from `install.json` pass the input name rule;
  - file names compare case-insensitively on Windows;
  - `install.json` stays until the rest is removed, and an empty folder without it is removed;
  - the owner may be the user or `BUILTIN\Administrators`;
  - unexpected errors become prefixed messages with status 1;
  - the user `PATH` is read again just before it is written;
  - temporary `.pyc.<n>` files count as bytecode.

  Verify: new shim cases (names outside the folder, foreign files then a second uninstall, an empty folder, an unexpected error, temporary bytecode) pass and fail without the change.
- [x] 8.2 In the shim:
  - read the manifest from standard output only, with `python3 -I -B`;
  - accept only plain lowercase `launcher/windows/*.ps1` names;
  - run the uninstall before the pipeline-input and WSL-setting refusals;
  - give the install folder its own drive-path message.

  Verify: shim cases with a UTF-16 warning on stderr, an editor copy of a script and an invalid `<P>_WSL_DISTRO` during uninstall pass and fail without the change.
- [x] 8.3 Make the "Source deleted" case move the checkout away; give `tools/windows-validate.ps1 -Install` a `finally` that removes its `PATH` entry, and a full install path; correct the contract's lock order and document that the lock does not cover a setup from the installed copy during an update. Verify: `bash tools/powershell.sh .` passes with 59 cases.
- [x] 8.4 Have the operator rerun `tools/windows-validate.ps1 -Install` on Windows with these changes. Verify: the result is recorded in the validation section, with no failure.

Left as is: the duplicated in-folder check between the shim and the installer (finding 14).

## Workflow follow-up

- Merge `main` into `feature/windows-podman-machine` at every new reference tag, and rerun group 7 after each merge.
- When the branch is mature, merge it into `main`, create the annotated `sandbox-ref-N` tag on the merge commit, rename the validation sections to that tag, and update the parity table in `docs/network-contract.md`.
- Propagate the tag to the wrappers with `tools/propagate.py`.
- Archive the change and sync its specs after review.
