# Tasks

## 1. Shared test independent of wrapper variable names

- [x] 1.1 Create branch `fix-adoption-blockers` from `main` in `sandbox-container`; verify `git status` is clean.
- [x] 1.2 Change `tests/test_guard.py` (`guarded_multiplex`) to take the proxy image from the single harness entry ending in `_EGRESS_IMAGE`, failing with a clear message for none or several (design decision 1); verify `bash tests/run-runtime.sh --guard` passes here.
- [x] 1.3 Verify the change in an agent wrapper context without touching that wrapper: copy `codex-container` to the scratchpad, place the changed `tests/test_guard.py` and the `sandbox-ref-19` shared files there, and run its `--guard` mode against its own harness; verify the guarded-multiplex tests pass (they fail with `KeyError` on the unchanged ref-19 test).

## 2. Manifest names the reference repository

- [x] 2.1 Extend `tools/propagate.py` (design decision 2): read the `SIBLING` name, rewrite it, the docstring and the skip message to the reference checkout's directory name on `--apply`, report `manifest: names <reference>` in the dry run, and refuse a manifest without a `SIBLING` line; add the cases to `tests/test_propagate.py` and verify they pass.
- [x] 2.2 Update `docs/propagation.md` (what `--apply` rewrites in the manifest); verify a dry run and an `--apply` on a scratch clone of `codex-container` (`sandbox-ref-18` to a local test tag) rewrite `SIBLING` to `sandbox-container` and that clone's `tests/test_reference_copy.py` sibling check runs instead of skipping.

## 3. Integration and tag

- [x] 3.1 Run the unit discovery, `--guard` and `--network`, and `git diff --check`; verify they pass.
- [ ] 3.2 Add a `sandbox-ref-20` section to `docs/validation.md` with each check and its result; commit, merge into `main` and create the annotated tag `sandbox-ref-20`; verify `git describe --exact-match main` prints `sandbox-ref-20` and the parity table's reference cell names it.

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-20`. No setup rerun is needed: no installed code or image changes.
- Archive this change with spec sync.
- Adopt `sandbox-ref-20` in `claude-container` (first manifest at `sandbox-ref-18`, then the tool), then in Codex, OpenCode, Pi and Antigravity, each in its own change.
