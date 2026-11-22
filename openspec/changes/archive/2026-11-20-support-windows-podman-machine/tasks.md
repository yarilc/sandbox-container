# Tasks

## 1. Windows spikes

- [x] 1.1 Prepare a self-contained spike script, `windows-spike.ps1`, that the operator can copy to the Windows host. It is not committed. In the machine distribution it uses only `wsl.exe` and a throwaway `/tmp` directory. It covers:
  - `wsl.exe -d <distro> -u user --cd ~ --exec /bin/bash <relative path>`;
  - the base64/NUL round trip of `$args` through `WSLENV`, including `''`, `"`, `\`, `è`, an emoji, a bare `--`, `-x:y`, `a,b` and a number;
  - `$MyInvocation.ExpectingInput` with pipeline input, and stdin redirected from `cmd /c "... < file"`;
  - `$LASTEXITCODE` for `exit 7`, a missing user and a missing distribution;
  - `wsl.exe -l -q` with and without `WSL_UTF8=1`;
  - TTY presence (`test -t 0 -a -t 1`);
  - the INT count after one Ctrl+C, and the signal after closing the window;
  - restoration of `$env:` values after Ctrl+C.

  Verify: the script parses without errors on PowerShell 7 (`[System.Management.Automation.Language.Parser]::ParseFile` in a PowerShell container), and every check prints one result line.
- [x] 1.2 Have the operator run the spike on Windows PowerShell 5.1 and on PowerShell 7, with an Ubuntu distribution running. Record the outputs in a new `docs/validation.md` section titled "Windows Podman machine support (pending tag)". Verify: the section lists every check from 1.1 with its observed result on both PowerShell versions.
- [x] 1.3 Reproduce the `podman rm` timeout seen on Podman 6.1.4. Run ten unrestricted sessions in the machine distribution and end each with Ctrl+C, then list leftover containers. Verify: the validation section records whether the timeout reproduces. If it does, a follow-up task is added here before group 7 starts.
- [x] 1.4 Compare the spike results with `specs/windows-launcher/spec.md` and design D1–D6 and D13. Verify: either no contradiction is recorded, or the specs and design are updated (for example the interrupt scenario, `--cd ~`, or the bare `--` advice) and `openspec validate support-windows-podman-machine --strict` passes.

## 2. Line endings

- [x] 2.1 Add `.gitattributes` with `* text=auto eol=lf` to the reference. Verify: `git ls-files --eol` reports `i/lf w/lf` for every text file.
- [x] 2.2 Add a shared test to `tests/test_alignment.py` that fails on a carriage return in any repository text file, skipping `.git` and files that contain NUL. Verify: the test passes on the reference, and fails naming the file when a temporary copy gets one CRLF line.
- [x] 2.3 In `setup/setup.py`, refuse any `MANIFEST` source that contains `\r` before the release directory is created (design D11). The message names the file, `.gitattributes` and the LF re-checkout `git rm -r -q --cached . && git reset --hard` (verified to rewrite CRLF working files; `git add --renormalize .` does not). Verify: a new `tests/test_setup.py` case shows status 1, the message, no new release, and the previous `current` link unchanged.
- [x] 2.4 Document the line-ending requirement and the renormalization step in `docs/setup.md`, and the new tests in `docs/launcher-test-map.md`. Verify: `git diff --check` is clean and the documented command matches the setup message.

## 3. Windows folders in the core

- [x] 3.1 Add the case-insensitive Windows folder match of design D9 to `core_workspace_refusal` in `launcher/core.sh`. Verify: `bash -n launcher/core.sh` and `bash tools/shellcheck.sh .` pass.
- [x] 3.2 Add `tests/test_launcher.py` cases that run the entry under `unshare -rm` with a tmpfs on `/mnt`, skipping without unprivileged namespaces. They cover every refused root in two letter cases, the worktree parent equal to a profile, the override with its warning, and an accepted project below a profile. Verify: the cases pass, or skip with the stated reason, on the runner, and the fake engine records no query for refused roots.
- [x] 3.3 Update the wrapper help in `launcher/core.sh`, the README section on sensitive workspaces, `docs/launcher-contract.md` and `docs/launcher-test-map.md`. Verify: the help test still passes without engine queries, and the README lists the same folders as the spec.

## 4. Setup without a launch service

- [x] 4.1 In `setup/setup.py`, factor the systemd user-manager check out of `prepare_service`, and add the read-only service probe of design D10 (candidates `CONTAINER_HOST`, the saved endpoint and the default endpoint, then the manager). Verify: unit cases with the fake engine and a `systemctl` stub cover each candidate answering, none answering with a usable manager, and none answering without one.
- [x] 4.2 Change the questionnaire so that, when the probe finds neither a service nor a manager, setup explains the reason, asks for explicit confirmation of unrestricted networking, sets the local endpoint, and skips the delegation and endpoint questions. Declining exits with status 1 and generic guidance. Verify: `tests/test_setup.py` and `tests/test_setup_wrapper.py` cases cover first run, rerun with saved offline, and decline. They show that no prompt mentions delegation, that no path derived from `XDG_RUNTIME_DIR` is printed, and that the saved preferences have `network=unrestricted`, `podman=false` and `endpoint=local`.
- [x] 4.3 Check that hosts with a service or a manager keep today's flow. Verify: the existing questionnaire, service-preparation and first-setup tests pass unchanged.
- [x] 4.4 Document the rule in `docs/setup.md` (network choice, how to make a service available, Podman machine as the example), and the tests in `docs/launcher-test-map.md`. Verify: the documented prompts match the test transcripts.
- [x] 4.5 Keep `CONTAINER_HOST` unset for the local endpoint. Podman 6 treats a set but empty `CONTAINER_HOST` as a remote context, which failed the smoke check on the machine (exit 125). `runtime_environment` in `setup/common.py` no longer sets an empty `CONTAINER_HOST`, and `core_engine` in `launcher/core.sh` unsets an empty `CONTAINER_HOST` or `CONTAINER_CONNECTION`. Verify: `test_local_endpoint_leaves_container_host_unset` and `test_empty_engine_context_reaches_podman_unset` pass, and fail without the change.

## 5. Bootstrap

- [x] 5.1 Write `launcher/windows/bootstrap.sh`, implementing design D2, D3 and D7. It:
  - checks for Bash 4.4 or later, `base64`, `wslpath` and `python3`;
  - validates and decodes `WRAPPER_WINDOWS_ARGS`;
  - classifies and translates `WRAPPER_WINDOWS_CWD` and `WRAPPER_WINDOWS_ENTRY`;
  - reads `command` from its release's `setup.json`;
  - exports the translated entry directory, unsets the other transport variables, runs `cd` into the workspace and executes the command.

  Verify: `bash tools/shellcheck.sh .` reports no finding for it.
- [x] 5.2 Add `launcher/windows/bootstrap.sh` to `MANIFEST` in `setup/common.py`. Verify: a setup test shows the file in the new release with mode 0700, and the protected-release checks still pass.
- [x] 5.3 Add `tests/test_windows_bootstrap.py` and list it in `SHARED_TESTS` (design D12). Verify: `python3 -m unittest tests.test_windows_bootstrap -v` passes. The cases cover empty, spaced and non-ASCII arguments, no arguments, a malformed or non-terminated payload, every row of the D7 table, a missing `setup.json`, old Bash, and the absence of the transport variables in the command's environment.
- [x] 5.4 Describe the bootstrap's inputs and refusals in `docs/launcher-contract.md`, and its tests in `docs/launcher-test-map.md`. Verify: every refusal message in the bootstrap appears in the contract.

## 6. Entry directory protection in managed launches

- [x] 6.1 Extend `protect_mounts` in `setup/common.py` with the optional `WRAPPER_WINDOWS_ENTRY` path of design D8: overlap in both directions with every writable mount, case-insensitive under `/mnt/<letter>/`, and no `trusted()` check. Verify: new `tests/test_setup.py` cases refuse a workspace containing the entry, a workspace inside it, a saved-worktree parent containing it, and a state directory inside it. They also accept a sibling without worktree scope and leave the behavior unchanged when the variable is unset.
- [x] 6.2 Document the rule in `docs/launcher-contract.md` and the tests in `docs/launcher-test-map.md`. Verify: `git diff --check` is clean.

## 7. Shim, PowerShell entry and checks

- [x] 7.1 Write `launcher/windows/core.ps1` per design D1–D6 and D13. It:
  - reads the profile;
  - selects and validates the distribution, user and installation;
  - refuses unsupported modes, `--container-qualify`, pipeline input and array arguments;
  - checks the checkout's line endings before setup;
  - routes help, setup and launches;
  - encodes the arguments and forwards the names of D4;
  - sets and restores the child environment;
  - diagnoses failures with the probes of D6;
  - returns the exit status.

  It stays ASCII-only. Verify: the file parses on PowerShell 7 (`[System.Management.Automation.Language.Parser]::ParseFile` reports no error).
- [x] 7.2 Add the thin entry `sandbox-container.ps1`. Verify: the entry contains no profile value and only runs the shim with `$PSScriptRoot`, `$args` and `$MyInvocation.ExpectingInput`.
- [x] 7.3 Extend `tests/test_alignment.py`: the PowerShell entry is thin and agent-neutral, it equals a fixed expected text that every wrapper must match, and the shim and the bootstrap contain no profile identifier. Verify: the tests pass, and fail when a temporary copy adds the profile name to the shim.
- [x] 7.4 Add `tools/powershell.Containerfile` (digest-pinned `mcr.microsoft.com/powershell`, plus a pinned PSScriptAnalyzer package with its verified SHA-256) and `tools/powershell.sh <checkout>`. The script runs the analyzer at warning level on the tracked `*.ps1` files and runs `tests/windows/shim_tests.ps1`, with `--network=none`. Verify: `bash tools/powershell.sh .` exits 0 on the reference, and reports a file and line for a planted `Invoke-Expression`.
- [x] 7.5 Write `tests/windows/shim_tests.ps1` with a fake `wsl.exe` (design D12). It covers every `windows-launcher` scenario that can be checked without Windows: argument encoding and the 32766-character limit, forwarded and skipped names, empty values, environment restoration (including removal of variables that were absent), mode, qualify and pipeline refusals, distribution, user and installation diagnosis, help with and without a distribution, setup routing and the CRLF refusal. Verify: all cases pass through `tools/powershell.sh`, and each case names its spec scenario.
- [x] 7.6 Document the Windows entry:
  - a Windows section in the README: prerequisites, setup, daily launch, `<P>_WSL_*`, unrestricted-only, pipeline input, quoting of `--`, empty variables, `podman machine stop`, Podman Desktop status, drvfs performance, and CRLF in user projects;
  - a Windows section in `docs/setup.md`;
  - the Windows entry in `docs/launcher-contract.md`;
  - the adoption steps for `<wrapper>-container.ps1` and `.gitattributes` in `docs/propagation.md`;
  - the PowerShell check in `AGENTS.md`;
  - the replacement of "Podman Machine ... unsupported" in the README.

  Verify: no document states that Podman machine is unsupported on Windows, and the README's commands match the shim's help.

- [x] 7.7 Require a machine started by Podman (design D6), after round 3 showed that a distribution started by `wsl.exe` alone has no `/run/user/<uid>` and no working `podman`:
  - the shim tells running, stopped and missing distributions apart with `wsl.exe -l --running -q`, then `wsl.exe -l -q`, and never starts a stopped one; launch and setup refuse a stopped machine, and help prints the guidance and exits 0;
  - before setup, the shim probes that `/run/user/<uid>` is a writable directory;
  - the bootstrap refuses a missing or read-only `/run/user/<uid>` before any Podman command;
  - README, `docs/setup.md`, `docs/launcher-contract.md`, the test map and the `-StopMachine` cases of `tools/windows-validate.ps1` follow.
  Verify: three new shim cases and `test_distribution_started_without_the_machine_stops_before_the_command` pass, and fail when the checks are removed.

## 8. Windows host validation

- [x] 8.1 Write `tools/windows-validate.ps1`, a reference-only operator script. It runs the `windows-launcher` scenario matrix against the installed entry: setup state, launch, arguments, environment, working-directory refusals, Windows folder refusals, mode refusals, entry-directory overlap, exit status, redirected input, missing installation and help. It also prints a paste-ready summary and removes what it created. Verify: it passes PSScriptAnalyzer through `tools/powershell.sh`, and a PowerShell 7 dry run against the fake `wsl.exe` completes.
- [x] 8.2 Have the operator run setup and `tools/windows-validate.ps1` on Windows PowerShell 5.1 and on PowerShell 7, with an Ubuntu distribution running. Have them also check Ctrl+C and window close by hand, and list the session's containers afterwards. Verify: the validation section records both summaries, with every scenario passed or a stated limitation that matches the README.
- [x] 8.3 Have the operator run `bash tests/run-runtime.sh` in unrestricted mode inside the machine distribution, from a checkout copy on its ext4 file system. Verify: the result is recorded in the validation section.
- [x] 8.4 Make `test_effective_hardening_and_budgets_in_every_unrestricted_variant` in `tests/test_runtime.py` follow the engine, after task 8.3 showed that it assumes delegated cgroup controllers: it derives the delegated controllers and the process mechanism with `network/agent_budgets.py`, as the launcher does, expects cgroup limits only for delegated controllers, the process rlimit under the fallback and the matching notices, and checks enforcement with a budget of 128 and 200 processes. Document that a small budget can leave too few tasks to start a container under the fallback. Verify: the test passes with the engine of the runner and, run by the operator, in the machine distribution.

## 9. Integration checks

- [x] 9.1 Run the shared suites:
  - `test_launcher.py`, `test_wrapper.py`, `test_session.py`, `test_setup.py`, `test_setup_wrapper.py`, `test_qualification.py`, `test_agent_profile.py`, `test_alignment.py` and `test_windows_bootstrap.py`;
  - `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .` and `git diff --check`.

  Verify: no new failures compared with `main` on the same runner, with environment failures listed as such.
- [x] 9.2 Run the runner modes that `docs/propagation.md` requires for the changed shared files: `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--guard` and `--network`. Verify: every mode is recorded in the validation section as passed or unavailable, and none fails.

## 10. Code review follow-up

- [x] 10.1 Refuse, besides the exact Windows roots, a profile's `Documents`, `OneDrive` (also `OneDrive - <organization>`) and `OneDrive/Documents`, and the whole `AppData` tree, where Windows runs user code (PowerShell profile and modules, startup folder). Update the `workspace-mounts` scenarios, the core help, the README, the contract and design D9, and move the `tools/windows-validate.ps1` work folder next to the checkout, with Documents and AppData cases. Verify: the Windows-folder launcher test refuses the new folders and still accepts projects below `Documents` and `OneDrive`, and fails with the old match.
- [x] 10.2 In the shim, forward only `<P>_*` names of letters, digits and `_`, and the configuration-directory variable only with a distribution path, each with a notice otherwise; treat any abbreviation of a command option before `-File` as a pipeline (design D3, D4). Read the shim tests' work folder from `SANDBOX_TEST_TMPDIR`. Verify: the new shim cases pass and fail without each rule.
- [x] 10.3 In the bootstrap, refuse a release whose saved preferences select networking other than unrestricted, or delegation, and remove the `WRAPPER_WINDOWS_RUNTIME_DIR` override; the tests replace the runtime path in their copy. Verify: `test_saved_restricted_preferences_stop_before_the_command` passes and fails without the check.
- [x] 10.4 In setup, treat an `OSError` from the socket probe as an unusable candidate, announce a saved delegation that cannot be kept, and check the copied bytes for carriage returns in `copy_inputs`. Fix the `core_engine` comment on Podman machine. Verify: `test_unreadable_socket_candidate_is_not_a_service`, `test_saved_delegation_without_a_service_is_announced` and the extended CRLF test pass and fail without the change.
- [x] 10.5 Rerun group 9 locally and the Windows validation (`tools/windows-validate.ps1` in both editions after a new setup). Verify: results recorded in the validation section, with no new failure.

Left for later changes: case-insensitive `overlap()` on drive mounts (finding 9, older than this change), and the questionnaire and probe simplifications (findings 12 and 13). Setup without a service on Linux keeps offering only unrestricted networking (finding 5), as the `container-setup` spec requires.

## Workflow follow-up

- Merge `main` into `feature/windows-podman-machine` at every new reference tag, and rerun group 9 after each merge.
- Continue with `add-windows-installer` on the same branch.
- When the branch is mature, merge it into `main` and create the annotated `sandbox-ref-N` tag on the merge commit. Rename the validation section to that tag and update the `Reference (...)` cell of the parity table in `docs/network-contract.md`.
- Propagate the tag to the wrappers with `tools/propagate.py`, copying `<wrapper>-container.ps1` and `.gitattributes` as the adoption steps say.
- Archive the change and sync its specs after review.
