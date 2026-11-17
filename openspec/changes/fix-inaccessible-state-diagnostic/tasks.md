# Tasks

## 1. Core and shared test

- [x] 1.1 Commit this change directory on `main` and create the branch `fix-inaccessible-state-diagnostic`. Extend `test_inaccessible_state_and_ignored_permissions` in `tests/test_launcher.py` with the cases of design decision 4. Verify that it fails against the current core in the disposable test container, showing the raw `cd:` or `mkdir:` messages.
- [x] 1.2 Add `resolve_state_directory` and the creation-failure handling to `launcher/core.sh`. Use them at the four resolution points and in `core_readonly_state` (design decisions 1-3). Verify that `python3 -m unittest tests.test_launcher tests.test_wrapper tests.test_alignment` passes in the disposable test container, and that `bash -n launcher/core.sh` succeeds.

## 2. Validation and release

- [x] 2.1 Run the unit discovery in the disposable test container, then `bash tests/run-runtime.sh --wrapper`, `--setup` and the default mode, then `git diff --check`. Record the results in `docs/validation.md`. Verify that all pass.
- [x] 2.2 Mark the old Codex case in `docs/launcher-test-map.md` (`test_inaccessible_state`) as covered by the extended shared case. Merge into `main`. Verify that `openspec validate fix-inaccessible-state-diagnostic --strict` passes.

## Workflow follow-up

- The operator pushes `main` and runs `--container-setup` on the three hosts. The merge is then tagged `sandbox-ref-24` (annotated) and pushed. The change is archived with spec sync.
- `codex-container`'s `adopt-sandbox-ref-23` adopts `sandbox-ref-24` (task 2.3): it propagates from `sandbox-ref-23` and reruns the old-test classification. Its artifacts name the new tag.
