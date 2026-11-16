# Tasks

## 1. Inventory skeleton

- [x] 1.1 Create `docs/launcher-contract.md` with:
  - the seven phases of design decision 1;
  - for each phase, a table with one column per launcher (sandbox, Claude, Codex, Antigravity, OpenCode, Pi), a "core decision" column and a "hook" column;
  - a "visible changes" list.

  Verify the file renders the empty tables and `git diff --check` passes.
- [x] 1.2 Record the interface baseline: the eight common options, the common `<PREFIX>_*` variables with their default and meaning in each wrapper, and the agent-specific variables. Verify each entry against each launcher's `--container-help` (run with a fake `HOME`, no engine call) and its source.

## 2. Phase-by-phase reconciliation

Each task below fills one or two phases of the document from the six launchers and their `tests/test_wrapper.py`, cites the covering tests, applies design decision 2, and ends with a review of that phase's open choices with the user. Verify each task by a complete table (no empty cell) and by the user's decisions being recorded in the document.

- [x] 2.1 Phases 1–2: arguments, help, modes, budgets, lifetime.
- [x] 2.2 Phases 3–4: workspace, isolated state, engine and cgroup checks.
- [x] 2.3 Phase 5: mounts, toolchains, CA, image build and selection (OpenCode `add_bind`, `opt_in_integration`, `shared_state`, `build_current_image`; Pi `select_ca_bundle`, `build_runtime_image`, `select_setting`).
- [x] 2.4 Phase 6: creation and name reservation, budget verification, start and attach (family A `creation_lookup`/`capture_response`, family B `wait_for_create`/`recover_container_id`).
- [x] 2.5 Phase 7: signals, shutdown deadline, cleanup and recovery by label (family A `shutdown`/`recover_container`, family B `cleanup`/`record_signal`/`recover_container_by_label`/`wait_for_client_until`).
- [x] 2.6 Wrapper tests: map every `tests/test_wrapper.py` case of the six repositories to a phase row. Mark each one as "shared launcher test", "agent hook test" or "obsolete (duplicate)". Compare the embedded fake engines with `tests/fake_podman.py` and list the cases the shared fake must support. Verify that no test case is left unmapped (count per repository).

## 3. Contract and delta list

- [x] 3.1 Write the contract section of `docs/launcher-contract.md`:
  - file layout (`launcher/`, `agent/launcher.sh`, entry script);
  - the variables `agent/launcher.sh` must declare;
  - the hook list, with call point, inputs, outputs, default and refusal rules;
  - the core-owned state hooks may read.

  Verify every "hook" cell of the phase tables names a hook defined there, and every agent-specific helper listed in task 2.3 maps to a hook or to a core behavior.
- [x] 3.2 Add a "Spec deltas for the implementation change" section to `docs/launcher-contract.md`: for each entry of the "visible changes" list and for the new `shared-launcher` capability, the capability, the requirement to add or modify and the behavior it states. Verify every visible change maps to a delta and `openspec validate define-launcher-contract --strict` passes.
- [x] 3.3 Record a short entry in `docs/validation.md`: launchers and test files read (with their commit), counts of differences by decision type, and validation. Commit this change; verify `git diff --check` and `git status` are clean.

## 4. Independent review fixes

The review findings (H1-H6, M1-M13, L1-L9) are recorded in a "Review findings"
section of `docs/launcher-contract.md`, each with its resolution.

- [x] 4.1 Resolve the high findings in the contract:
  - H1: installation manifest and qualification code list include the core files;
  - H2: in-container application path and the unrestricted entrypoint rule;
  - H3: credential model keyed by policy profile, including unrestricted forwarding;
  - H4: proxy and locale forwarding in unrestricted mode;
  - H5: Pi's `--init`, `CONTAINER_NAME`, delegation tmpfs mounts, build format and timeout;
  - H6: the base `build-inputs-hash` input set.

  Choices with no existing decision go to the user as U10 and following. Verify each finding has a recorded resolution and a delta row where behavior changes.
- [x] 4.2 Resolve the medium findings M1-M13 the same way: shutdown slicing, environment scopes and ordering, bind and tmpfs rules, query timeouts, read-only layout, build-only path, entry-script contract, and test-map notes. Verify as in 4.1.
- [x] 4.3 Correct the low findings L1-L9 and regenerate `docs/launcher-test-map.md`, adding a "shared (rewrite)" destination for tests a decision changes. Verify that the totals still match the `def test_` counts.
- [x] 4.4 Update the `docs/validation.md` entry (review performed, finding counts and resolutions), run `openspec validate define-launcher-contract --strict` and `git diff --check`, and commit.

## 5. Second independent review fixes

- [x] 5.1 Record decisions U15-U18 and resolve the second review's high findings (H-a to H-g) in the contract: resolved mode exported to the Python helpers, entry-script fallback without readlink, shell profiles always in shell mode, build-only validation, preflight and managed-launch trust lists, editor default, OpenCode's native-variable allowlist. Verify each finding has a recorded resolution and a delta row where behavior changes.
- [x] 5.2 Resolve the medium and low findings: probe path, combined build flags, setup awareness of the new variables, variable syntax, help composition, `session.py agent-args` ordering, build-hash construction, profile field types, hook state, cell corrections and missing visible changes. Verify as in 5.1.
- [x] 5.3 Regenerate `docs/launcher-test-map.md` (credential and decision-dependent rewrites) and add the affected non-wrapper test files; verify the totals still match the `def test_` counts.
- [x] 5.4 Update the `docs/validation.md` entry, run `openspec validate define-launcher-contract --strict` and `git diff --check`, and commit.

## Workflow follow-up

- The user reviews `docs/launcher-contract.md`; archive this change with `--skip-specs`.
- Next change in `sandbox-container`: implement `launcher/`, the reference's `agent/launcher.sh`, the shared fake engine and the shared launcher tests, then tag. After that, one adoption change per wrapper: Claude first, then Codex, Antigravity and Pi, then OpenCode.
