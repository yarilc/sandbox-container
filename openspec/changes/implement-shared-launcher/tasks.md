# Tasks

The behavior of each task is defined by the named rows of `docs/launcher-contract.md`. Every task group leaves the unit discovery green in the disposable test container.

## 1. Test groundwork

- [x] 1.1 Create branch `implement-shared-launcher` from `main`; verify `git status` is clean.
- [x] 1.2 Extract the reference's embedded fake engine into `tests/fake_podman.py` (unknown commands fail, design decision 5), and point `tests/test_wrapper.py` at it; verify the 80 cases pass unchanged.
- [x] 1.3 Add `tests/fixtures/agent/launcher.sh` (every data array and hook; hooks record their inputs and visible variables) and `tests/fixtures/shell-agent/launcher.sh` (data only). Make `tests/sandbox_profile.fixture_root` copy `launcher/` and write the thin entry script under the fixture wrapper name. Add `tests/fake_podman.py` and the two fixture `launcher.sh` files to `SHARED_TESTS` in `tests/test_alignment.py` (`launcher` and `tests/test_launcher.py` join the lists in 3.1 and 3.3, when they exist, because the alignment checks read every listed path). Verify the unit discovery passes.

## 2. Profile and shared Python

- [x] 2.1 `network/agent_profile.py`: accept `native.exec` (absolute path, default `/usr/local/bin/<command>`) and `native.exec_tmp` (boolean, default false), refuse `install.runtime_build`, add `ENV_VARS` and `READONLY_STATE` to the suffixes, and derive the default network mode from the authentication methods. Update the reference and fixture profiles and `tests/test_agent_profile.py`; verify they pass.
- [x] 2.2 `setup/common.py`: install `launcher/core.sh` and `agent/launcher.sh` (H1), drop host `ENV_VARS` and `READONLY_STATE` in `runtime_environment` (M3), and use the profile default mode in `protect_mounts` (H-a). `setup/setup.py` builds every runtime through the wrapper's build-only operation (U3, U8). `setup/launch.py` verifies the two launcher files as protected (H-e). Update `tests/test_setup.py`; verify it passes.
- [x] 2.3 `network/qualification_records.py` binds `launcher/core.sh` (`SHARED_CODE`) and `agent/launcher.sh` (`code_files`); `network/control.py` preflight requires both protected; `network/qualify.py` and `qualification_records.py` derive a missing mode from the profile (H1, H-a, H-e). Update `tests/test_qualification.py` and `tests/test_session.py` cases; verify they pass.

## 3. Core extraction (no behavior change)

- [x] 3.1 Move `sandbox-container.sh` into `launcher/core.sh`, replacing reference literals with `AGENT_*` values; write the reference's `agent/launcher.sh` (shell profile, `AGENT_SESSION_ENV` with `HISTFILE` and the config variable); make `sandbox-container.sh` the thin entry script with the readlink fallback (H-b). Add `launcher` to `SHARED_DIRECTORIES`. Verify the 80 wrapper cases and `bash -n` pass, and that the entry scripts of the reference and the fixture differ only by name.
- [x] 3.2 Add the alignment test comparing `agent/launcher.sh` with `agent/profile.json` and `AGENT_CREDENTIALS` with `agent/policies/default.json`, and update `tests/test_alignment.py` for the thin entry script. Verify it passes for the reference and both fixtures, and fails on a mismatched value.
- [x] 3.3 Restructure the core into the phase functions and `call_hook` of design decisions 2 and 3, still without behavior change. Create `tests/test_launcher.py`, add it to `SHARED_TESTS`, and move the reference's cases there, running through the fixture root with the shell fixture. Verify the moved cases pass and the count matches.

## 4. Phases 1-2: interface, modes, settings

- [x] 4.1 Implement the phase 1-2 rows:
  - profile default mode (U1);
  - provider-mode requirements;
  - shell profiles always in shell mode (H-c);
  - `<P>_ENV_VARS` and `<P>_READONLY_STATE` parsing (U5, U6, U18);
  - approval bypass validation;
  - image-name and configuration-override lexical checks;
  - `agent_validate`, `agent_help` and help composition with the provider disclosure from the default policy (M8).

  Add the shared cases, including the new U1 case and the fixture agent cases. Verify they pass.
- [x] 4.2 Implement the build-only path and combined flags (U3, U16, U17). Rewrite the "shared (rewrite) U16/U17" cases; verify they pass.

## 5. Phases 3-4: workspace, state, engine

- [x] 5.1 Implement the phase 3-4 rows:
  - one host-tool check, with readlink reported in the reference's order;
  - one capture function with CR and record checks and a 10 s timeout on every read-only query (M8);
  - field-parse engine check;
  - parent-aware `STATE_DIR` overlap;
  - private directories that are never repaired;
  - contained and private isolated children (M4);
  - read-only state layout (M9).

  Port the family B engine-response cases from the map. Verify they pass.

## 6. Phase 5: mounts, environment, image

- [x] 6.1 Implement the temporary-storage layout and the tmpfs home (U7, L7), the bind builder and the `agent_mounts` validation (M7), and the delegation tmpfs mounts (U12). Rewrite the U7 cases; verify they pass.
- [x] 6.2 Implement session environment ordering (M6), locale and unrestricted proxy forwarding (U11), credentials (U10), reserved names (U13), fixed settings by scope (M2), `agent_environment`, `agent_approval_bypass` and `agent_command_args`. Port the credential and forwarding cases (U10, U11, U13 rewrites); verify they pass.
- [x] 6.3 Implement the image rules: base pull, `--pull=never --format docker` with `</dev/null`, no timeout, `build-inputs-hash` over the defined inputs with `agent_build_args` and `agent_build_inputs` (H6, M12, U8, U12), and the stale-image refusal. Port Pi's freshness cases; verify they pass.

## 7. Phases 6-7: creation, start, shutdown

- [x] 7.1 Implement:
  - `AGENT_EXEC` for restricted agent sessions and the image entrypoint for unrestricted ones (H2);
  - `session.py agent-args` output after the core arguments (M9);
  - per-attempt `CONTAINER_NAME`, `--init` in unrestricted sessions, `</dev/null` for create;
  - the owned-container-behind-a-failed-create rule;
  - X's CID validation and O's cross-check;
  - the probe path (M1).

  Port the family B and OpenCode creation and collision cases. Verify they pass.
- [x] 7.2 Align shutdown slicing with the contract (U9) and port the family B signal and stall cases as rewrites. Verify they pass and every shared case finishes within the shutdown bound.

## 8. Test completion and documentation

- [x] 8.1 Check `tests/test_launcher.py` against `docs/launcher-test-map.md`: add a "Shared case" column naming, for every "shared" and "shared (rewrite)" case, the shared case that covers it; a case from another wrapper whose coverage is not verified here is marked "to verify at adoption" (user decision: each adoption runs its old `tests/test_wrapper.py` against the new core and turns every lost behavior into a shared case through the reference). Reduce the reference's `tests/test_wrapper.py` to shell-profile and history cases. Verify the counts and the unit discovery.
- [x] 8.2 Update the README (new variables, temporary storage, build-only, forwarding), `docs/network-contract.md` (parity: reference on the new tag), `network/README.md`, `AGENTS.md` (shared directories), and mark `docs/launcher-contract.md` as implemented. Verify `git diff --check` and that `grep` finds no description of the old layout.

## 9. Validation and tag

- [ ] 9.1 Run the unit discovery and every runner mode (`--setup`, `--setup-runtime`, `--qualification`, `--guard`, `--network`, `--network-policy`, `--network-feasibility`, `--wrapper`, default) with a reference image rebuilt through the new build-only path. Run `tools/propagate.py` as a dry run against a scratch clone of `claude-container` (old tag to a local test tag) and verify that it adds `launcher/`, `tests/test_launcher.py` and `tests/fake_podman.py`. Record everything in `docs/validation.md`. Verify all pass.
- [ ] 9.2 Commit and merge into `main`; verify `openspec validate implement-shared-launcher --strict` and `git diff --check`.

## Workflow follow-up

- The operator pushes `main` and runs `--container-setup` on the three hosts; the results go to `docs/validation.md`.
- Create the annotated tag `sandbox-ref-22` on the merge, update the parity table's reference cell, and archive this change with spec sync.
- Adopt `sandbox-ref-22` in Claude; then in Codex, Antigravity and Pi; then in OpenCode, each in its own change. Before deleting its old launcher, each adoption runs its current `tests/test_wrapper.py` against the new core and resolves the map's "to verify at adoption" rows: a failure from a lost behavior becomes a shared case through a reference fix.
