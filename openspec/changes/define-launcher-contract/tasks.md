# Tasks

## 1. Inventory skeleton

- [ ] 1.1 Create `docs/launcher-contract.md` with:
  - the seven phases of design decision 1;
  - for each phase, a table with one column per launcher (sandbox, Claude, Codex, Antigravity, OpenCode, Pi), a "core decision" column and a "hook" column;
  - a "visible changes" list.

  Verify the file renders the empty tables and `git diff --check` passes.
- [ ] 1.2 Record the interface baseline: the eight common options, the common `<PREFIX>_*` variables with their default and meaning in each wrapper, and the agent-specific variables. Verify each entry against each launcher's `--container-help` (run with a fake `HOME`, no engine call) and its source.

## 2. Phase-by-phase reconciliation

Each task below fills one or two phases of the document from the six launchers and their `tests/test_wrapper.py`, cites the covering tests, applies design decision 2, and ends with a review of that phase's open choices with the user. Verify each task by a complete table (no empty cell) and by the user's decisions being recorded in the document.

- [ ] 2.1 Phases 1–2: arguments, help, modes, budgets, lifetime.
- [ ] 2.2 Phases 3–4: workspace, isolated state, engine and cgroup checks.
- [ ] 2.3 Phase 5: mounts, toolchains, CA, image build and selection (OpenCode `add_bind`, `opt_in_integration`, `shared_state`, `build_current_image`; Pi `select_ca_bundle`, `build_runtime_image`, `select_setting`).
- [ ] 2.4 Phase 6: creation and name reservation, budget verification, start and attach (family A `creation_lookup`/`capture_response`, family B `wait_for_create`/`recover_container_id`).
- [ ] 2.5 Phase 7: signals, shutdown deadline, cleanup and recovery by label (family A `shutdown`/`recover_container`, family B `cleanup`/`record_signal`/`recover_container_by_label`/`wait_for_client_until`).
- [ ] 2.6 Wrapper tests: map every `tests/test_wrapper.py` case of the six repositories to a phase row. Mark each one as "shared launcher test", "agent hook test" or "obsolete (duplicate)". Compare the embedded fake engines with `tests/fake_podman.py` and list the cases the shared fake must support. Verify that no test case is left unmapped (count per repository).

## 3. Contract and spec deltas

- [ ] 3.1 Write the contract section of `docs/launcher-contract.md`:
  - file layout (`launcher/`, `agent/launcher.sh`, entry script);
  - the variables `agent/launcher.sh` must declare;
  - the hook list, with call point, inputs, outputs, default and refusal rules;
  - the core-owned state hooks may read.

  Verify every "hook" cell of the phase tables names a hook defined there, and every agent-specific helper listed in task 2.3 maps to a hook or to a core behavior.
- [ ] 3.2 Update `specs/shared-launcher/spec.md` if the reconciliation refined the contract (for example the hook refusal rules). Write `specs/container-launcher/spec.md` with a MODIFIED or ADDED delta for each behavior in the "visible changes" list. Verify `openspec validate define-launcher-contract --strict` passes.
- [ ] 3.3 Record a short entry in `docs/validation.md`: launchers and test files read (with their commit), counts of differences by decision type, and validation. Commit this change; verify `git diff --check` and `git status` are clean.

## Workflow follow-up

- The user reviews `docs/launcher-contract.md`; archive this change with spec sync.
- Next change in `sandbox-container`: implement `launcher/`, the reference's `agent/launcher.sh`, the shared fake engine and the shared launcher tests, then tag. After that, one adoption change per wrapper: Claude first, then Codex, Antigravity and Pi, then OpenCode.
