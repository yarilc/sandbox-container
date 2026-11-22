# Tasks

## 1. Setup guidance from the Windows entry

- [x] 1.1 In `launcher/core.sh`, name `<AGENT_NAME>.ps1 --container-setup from Windows` in both "setup required" refusals when `WRAPPER_WINDOWS_ENTRY` is not empty (design D1). Verify: a `tests/test_launcher.py` case with `WRAPPER_WINDOWS_ENTRY` set gets the Windows step for the offline and provider refusals and no wrapper path, and the existing cases without it keep `run bash ... --container-setup and use the managed launcher`.
- [x] 1.2 In `tools/windows-validate.ps1`, make the unprepared restricted-mode case also expect `.ps1 --container-setup from Windows`. Verify: PSScriptAnalyzer passes, and a dry run against the fake `wsl.exe` completes.
- [x] 1.3 Update `docs/launcher-contract.md` (the setup guidance and the Windows entry) and `docs/launcher-test-map.md`. Verify: both name the Windows step and the new test.
- [x] 1.4 Document host CA trust with a Podman machine (design D3) in the Windows sections of `README.md` and `docs/setup.md`, with links from their host CA paragraphs, and record the operator's check in `docs/validation.md`. Verify: the docs name `podman machine set --import-native-ca`, the restart and the setup answers.

## 2. Checks on this runner

- [x] 2.1 Run `--shared`, `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .` and `git diff --check`. Verify: the results are recorded in `docs/validation.md`, with no new failure compared with the branch head.

## 3. Validation on Windows

- [x] 3.1 Prepare the operator bundle with the snapshot and the steps of design D2. Verify: the README lists the three steps, the copies of the summary files, and the data to send back.
- [x] 3.2 Have the operator run design D2. Verify: `docs/validation.md` records, for both editions, the `-Install` and `-StopMachine` results; the unprepared restricted-mode case with the Windows step; and the final offline setup with the proposed `default` endpoint. No case fails.

## Workflow follow-up

- Merge the branch into `main` with the other Windows changes, tag it, and propagate it to the wrappers. Then run `windows-validate -Install` and a provider setup with `--network` in an agent wrapper on Windows.
- Archive the change and sync its specs after review.
