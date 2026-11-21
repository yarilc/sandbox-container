# Tasks

## 1. Setup started by the Windows entry

- [x] 1.1 In `launcher/windows/core.ps1`, run both setup calls (`--container-setup` and the setup after `--container-install`) with `WRAPPER_WINDOWS_SETUP=1` forwarded through `WSLENV` (design D1). Verify: shim cases show `WRAPPER_WINDOWS_SETUP/u` in `WSLENV` and the value `1` for both setup calls, and in no launch call.
- [x] 1.2 In `setup/setup.py`, when `WRAPPER_WINDOWS_SETUP` is exactly `1`, skip both `path_guidance()` calls and the "Launch from a workspace" and "Review/change setup" lines, and print the Windows next-step sentence instead. Verify: `tests/test_setup.py` cases show the guidance with the variable unset or set to another value, and its absence with `1`. `tests/test_setup.py` and `tests/test_setup_wrapper.py` pass.

## 2. Owned tag cleanup

- [x] 2.1 Record the tags that `prepare_artifacts()` creates for the candidate. When the candidate is not activated, untag each one in `main()`'s `finally`, and report any image left without a name, and any untag failure, as persistent effects (design D2). Verify: `tests/test_setup.py` cases with the fake engine show, for a smoke failure after a reused-image tag and after a build, one `untag` of each candidate tag and no other `untag` or `rm`, and no untag after a successful activation.

## 3. Documentation

- [x] 3.1 Update `docs/setup.md`: the Windows output; the removal of an abandoned candidate's tags; the manual steps for tags of earlier runs (design D3). Update the README's Windows section where it mentions setup output, and `docs/launcher-test-map.md`. Verify: the documented commands match the code, and the guide still states that retained releases are not pruned.

## 4. Validation

- [x] 4.1 Have the operator run `.\sandbox-container.ps1 --container-setup` and an install on Windows. Verify: `docs/validation.md` records that the setup output has no `export PATH=` line or distribution command, and that the entry prints its next step.
- [x] 4.2 Run `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .`, `git diff --check`, the unit discovery and the runner modes `--setup` and `--setup-runtime`. Verify: the results are recorded in the validation section, with no new failure compared with the branch head.

## Workflow follow-up

- Merge the branch into `main` with the other Windows changes, tag it, and propagate it to the wrappers.
- Archive the change and sync its specs after review.
