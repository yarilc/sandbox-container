# Proposal

## Why

Three Windows paths have not run on a Windows host since sessions and setup
moved into the machine's systemd namespaces
(`support-machine-restricted-networking`):

- the installer (`windows-validate -Install`), whose setup now runs from the
  installed copy through `launcher/windows/enter.sh`;
- the refusals of a stopped machine and of a distribution that `wsl.exe` alone
  started, and the restart with Podman (`-StopMachine`);
- a restricted mode on an installation that setup prepared for unrestricted
  networking.

The last case also shows a wrong message. The shared launcher answers
`run bash /home/user/.local/lib/<name>/.../<name>.sh --container-setup and use
the managed launcher`, which is the Linux step; on Windows the step is
`<name>.ps1 --container-setup`.

## What Changes

- **Setup guidance from the Windows entry.** When the launch comes from the
  Windows entry (`WRAPPER_WINDOWS_ENTRY` set by the bootstrap), the launcher's
  "setup required" messages name `<name>.ps1 --container-setup` from Windows,
  instead of the Linux wrapper path and the managed launcher. Linux launches
  keep their message.
- **Validation on Windows with the final code**, recorded in
  `docs/validation.md`:
  - `tools/windows-validate.ps1 -Install -StopMachine` on Windows PowerShell
    5.1 and PowerShell 7;
  - an unrestricted setup, then the validation, which runs the refusal of an
    unprepared restricted mode with the new message; then an offline setup
    again.
- **Host CA trust on Windows, documented.** On a network that intercepts TLS,
  the Podman machine does not trust the Windows certificate store unless
  Podman imports it (`podman machine set --import-native-ca`, Podman 6.0 or
  later). Without it, setup's host CA trust has no interception CA to offer,
  and pulls, builds and sessions fail certificate verification. The operator
  verified the setup with the import on 2026-11-21. The Windows docs explain
  the import and the setup answers.
- Out of scope: `-Install` on an agent wrapper, which needs the Windows entry
  in that wrapper, so it follows the tag and propagation with the provider
  check.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `windows-launcher`: "Network modes from setup, without delegation" states
  that an unprepared restricted mode names the Windows setup step.

## Impact

- `launcher/core.sh` (shared): the setup guidance of the two "setup required"
  messages. It joins the same reference tag and propagation as the other
  Windows changes; the `--shared` runner mode covers it.
- `tests/test_launcher.py`: a case with `WRAPPER_WINDOWS_ENTRY` set.
- `tools/windows-validate.ps1`: the refusal case also checks the Windows step.
- `docs/launcher-contract.md`, `docs/launcher-test-map.md`,
  `docs/validation.md`.
- `README.md` and `docs/setup.md`: host CA trust with a Podman machine.
