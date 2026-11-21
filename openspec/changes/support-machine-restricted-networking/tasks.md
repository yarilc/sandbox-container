# Tasks

## 1. Spike in the machine

- [x] 1.1 Write the operator bundle (design D1):
  - `machine-spike.sh`, the inventory of A1, A2, A3 and A6, with a restart check;
  - `machine-runtime.sh <mode>`, which runs `tests/run-runtime.sh` with `--guard`, `--qualification`, `--network` or `--setup-runtime` against the machine's socket, building the guard toolchain image when it is missing;
  - the PowerShell launchers and a README.

  Verify: ShellCheck and PSScriptAnalyzer pass on the scripts, and a dry run of `machine-spike.sh` on this runner completes.
- [x] 1.2 Have the operator run the bundle on Windows with a machine started by Podman, in rounds until A1 to A6 are settled; round 3 adds `machine-chain.sh` (two ways into systemd's namespaces) and round 4 the missing Python base. Verify: a new `docs/validation.md` section, "Windows restricted networking (pending tag)", records every check of A1 to A6, both ways and each runner mode with its result.
- [x] 1.3 Update the proposal, specs, design and tasks with the spike results, or stop the change when A2 or A3 fails. Verify: `openspec validate --strict` passes, and the design names the outcome of each assumption.

## 2. Way into the machine's systemd namespaces

- [x] 2.1 Add `launcher/windows/enter.sh` (design D2): direct run when PID 1 is systemd, the machine's systemd found by `NSpid`, the `sudo -n` check, the private environment file, `sudo -n nsenter --mount --pid --wd`, then `sudo -n -u <user>` and the inner part that restores the environment with `XDG_RUNTIME_DIR=/run/user/<uid>`. List it in `setup/common.py` and `tests/test_alignment.py`. Verify: a new `tests/test_windows_enter.py`, with a synthetic `/proc` and fake `sudo` and `nsenter`, covers the exact commands, the environment (a 30000-character value, quotes, non-ASCII), the directory, stdin, exit status, the direct run, missing systemd, a password-protected `sudo`, that a successful start leaves no environment file, and that the next start removes the file of a failed one.
- [x] 2.2 In `launcher/windows/bootstrap.sh`, run the managed command through the helper. Verify: `tests/test_windows_bootstrap.py` shows the managed command receiving the same arguments, directory and environment through a fake helper path, and `XDG_RUNTIME_DIR=/run/user/<uid>`.
- [x] 2.3 In `launcher/windows/core.ps1`, start setup through the helper from the checkout; help stays a direct run. Verify: shim cases show the exact `--exec /bin/bash launcher/windows/enter.sh <name> /bin/bash <wrapper> --container-setup` arguments, also for the setup after an install, help unchanged, and the checkout check requires the helper.

## 3. Restricted modes on Windows

- [x] 3.1 In the shim, pass `<P>_NETWORK` and `--container-qualify` on to the launcher, keep the delegation refusal, and update the Windows help (design D4). Verify: shim cases cover offline and provider forwarding, qualification, the delegation refusal and the help text.
- [x] 3.2 In the bootstrap, refuse saved delegation only. Verify: bootstrap cases accept saved `offline` and `provider` and refuse `podman: true`.

## 4. Documentation

- [x] 4.1 Update the README's Windows section, `docs/setup.md`, `docs/launcher-contract.md`, `docs/launcher-test-map.md` and `AGENTS.md`:
  - the supported modes;
  - the prerequisites: a rootless machine started by Podman, its launch service, passwordless `sudo`;
  - the way into systemd's namespaces.

  Verify: no document still says that Windows supports only unrestricted networking, and the README matches the shim's help.

## 5. Validation

- [x] 5.1 Change `tools/windows-validate.ps1`:
  - mode cases that follow the saved mode: after an offline setup, an offline launch with no network access and qualification; after an unrestricted setup, a restricted mode refused with setup guidance; in both, the delegation refusal;
  - a check that the machine's service can run a command in a running session's container and remove it;
  - the terminal size among the steps by hand (`-c 'stty size'`), since the cases run without a terminal.

  Verify: PSScriptAnalyzer passes, and a dry run against the fake `wsl.exe` completes.
- [x] 5.3 Run the shared suites, `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .`, `git diff --check` and the runner modes that `docs/propagation.md` requires for the changed files on this runner. Verify: the results are recorded, with no new failure compared with the branch head.

## 6. Interrupts in restricted sessions and the setup endpoint

- [x] 6.1 Make the guard a confined init (design D6) in `network/guard.c`: block the waited signals, fork, put the child in a new process group and make it the terminal's foreground group, close standard input and output and the proxy channel in the guard, forward signals, reap orphans, and exit with the application's status or 128 plus the signal. Verify: new `tests/test_guard.py` runtime cases through the production guard: Ctrl+C in a terminal ends `sleep` with status 130; an application with a SIGINT handler counts exactly one SIGINT; TERM sent to the container reaches the application; status 37 with a background process returns at once; the waiting guard has no fd 0, 1 or 3. The existing guard, mocked component and revision tests pass.
- [x] 6.2 In `setup/setup.py`, propose `default` when the workflow needs a service and the saved endpoint is `local` (design D7). Verify: a `tests/test_setup.py` case moves a saved unrestricted `local` installation to offline with the proposed endpoint and saves `default`, and an unrestricted rerun still proposes `local`.
- [x] 6.3 Document the init in `network/README.md`, the README's hardening section and `docs/network-contract.md`, and update the test map. Verify: the documents describe the process model, and no document says that restricted sessions run the application as PID 1.
- [x] 6.4 Run, on this runner, `--shared`, `--setup`, `--setup-runtime`, `--guard`, `--network` and `--qualification`, ShellCheck, PowerShell and `git diff --check`. Verify: the results are recorded in `docs/validation.md`, with no new failure compared with the branch head.

## 7. Windows validation with the final code

- [x] 7.1 Have the operator run offline setup and `tools/windows-validate.ps1` on Windows PowerShell 5.1 and PowerShell 7, plus the manual Ctrl+C and window-close checks, and the runner modes in the machine again with the final code. Verify: the validation section records both summaries, the manual checks and the runner modes; failures other than the recorded environment limits (cgroupfs budget test, AF_VSOCK control) block the change. The manual checks include Ctrl+C on an offline `-c 'sleep 60'` (status 130) and on `sleep 60` typed in an offline interactive shell.

## Workflow follow-up

- Merge the branch into `main` with the other Windows changes, tag it, and propagate it to the wrappers. Run `--network` with a real provider check in an agent wrapper on Windows after propagation.
- Archive the change and sync its specs after review.
