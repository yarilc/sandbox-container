# Tasks

## 1. Credential variables from Windows

- [x] 1.1 In `launcher/windows/core.ps1`, read each `auth.<method>.credential_env` with the profile name rule. Add the names to the forwarded set next to the approval-bypass variable. A reserved name gets one notice and is not forwarded. When the profile has credential variables, add one line naming them to the help's Windows part (design D1). Verify: new cases in `tests/windows/shim_tests.ps1` with the fixture agent profile:
  - `FIXTURE_API_KEY` set reaches the launch call with `/u` in `WSLENV`;
  - unset or empty, it is not forwarded;
  - the shell profile forwards no credential variable;
  - `WSLENV` is restored after the launch;
  - the help names the variable.

  `bash tools/powershell.sh .` passes with no finding.
- [x] 1.2 Update the forwarding list in `docs/launcher-contract.md` (Windows entry), the Windows variable paragraph in `README.md`, and the shim row in `docs/launcher-test-map.md`. Verify: each names the credential variables, and the README says that `$env:<KEY>` before the entry supplies an API key as on Linux.

## 2. Antivirus documentation

- [x] 2.1 Replace the antivirus bullet in the README's "Limits on Windows" with the observed facts and the workaround (design D3). Add the same advice to the header comment of `tools/windows-validate.ps1`, and record the operator's report in `docs/validation.md`. Verify: the three texts name Bitdefender's Advanced Threat Control, the validation script and bundle extraction, the unaffected setup, installer and sessions, and the workaround. `bash tools/powershell.sh .` still passes.

## 3. Checks on this runner

- [x] 3.1 Run `--shared` (unit discovery), `tests/test_alignment.py`, `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .` and `git diff --check`. Verify: the results are recorded in `docs/validation.md`, with no new failure compared with the branch head.

## 4. Validation on Windows

- [x] 4.1 Prepare the operator bundle: the snapshot of the branch tree and a README with the steps of design D2. Verify: the README lists the three steps, the shell commands of step 2, the summary copies and the data to send back, and the checksums match.
- [x] 4.2 Have the operator run design D2. Verify: `docs/validation.md` records the three steps:
  - step 1's summary with the `local` endpoint;
  - step 2's `/proc/1/comm`, `XDG_RUNTIME_DIR`, setup answers and summary;
  - step 3's endpoint proposal and `ok`.

  When a step fails, apply pauses for the decision of design D2 before this task is marked.

## Workflow follow-up

- Archive the change and sync its specs after review.
- Then, for `sandbox-ref-27`:
  - merge the branch into `main`;
  - rename the "(pending tag)" sections of `docs/validation.md` to the tag, with every runner mode;
  - update the parity cell, then create the tag.
- Propagate `sandbox-ref-25` to `sandbox-ref-27` to `claude-container` with `tools/propagate.py`. Copy `claude-container.ps1` and `.gitattributes` by hand and adapt the wrapper's Windows docs. Then run the provider check on Windows, including the account login and the API key.
