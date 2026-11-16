# Tasks

## 1. Shared guard test uses the real image's home

- [x] 1.1 Create branch `fix-guard-agent-home` from `main` in `sandbox-container`; verify `git status` is clean.
- [x] 1.2 Change `tests/test_guard.py` (`production_container`) to mount `AGENT_HOME`, added to `tests/sandbox_profile.py` (design decision 1); verify `bash tests/run-runtime.sh --guard` passes here.
- [x] 1.3 Verify in an agent wrapper context without touching that wrapper: in `opencode-container` temporarily replace `tests/test_guard.py` and `tests/sandbox_profile.py` with the changed files (runtime bind mounts need host-visible paths, so a scratchpad copy cannot run), then restore them, and run `--guard -k test_production_filter_and_landlock_on_real_rootless_kernel` with the OpenCode setup image; verify it passes (it fails with the `sandbox-ref-20` file).

## 2. Integration and tag

- [x] 2.1 Run the unit discovery and `--guard`, and `git diff --check`; verify they pass.
- [x] 2.2 Add a `sandbox-ref-21` section to `docs/validation.md` with each check and its result; commit, merge into `main` and create the annotated tag `sandbox-ref-21`; update the parity table's reference cell; verify `git describe --exact-match main` prints `sandbox-ref-21`.

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-21`. No setup rerun is needed for this tag alone.
- Archive this change with spec sync.
- Adopt `sandbox-ref-21` in Claude, Codex, Antigravity, OpenCode and Pi, each in its own change; then the operator runs the host setups for all wrappers.
