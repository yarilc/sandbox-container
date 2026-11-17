# Tasks

## 1. Fix and guard

- [ ] 1.1 Replace the seven identifier lines in `tests/test_launcher.py` (design decision 1). Verify that `python3 -m unittest tests.test_launcher` passes in the disposable test container.
- [ ] 1.2 Add the sibling-identifier check to `tests/test_alignment.py` (design decision 2). Verify that:
  - it fails against the `sandbox-ref-22` `tests/test_launcher.py`;
  - it passes after task 1.1;
  - it reports a skip when run in a copy without siblings.

## 2. Release

- [ ] 2.1 Run the unit discovery in the disposable test container and `bash tests/run-runtime.sh --wrapper`, plus `git diff --check`. Record the results in `docs/validation.md`, archive this change with spec sync, merge into `main`, and tag the merge `sandbox-ref-23`. Verify that `git describe --exact-match` names the tag.

## Workflow follow-up

- Claude's `adopt-sandbox-ref-22` change moves to `sandbox-ref-23`.
- The operator pushes `main` and the tag. No `--container-setup` is needed for this tag alone, because only shared tests changed.
