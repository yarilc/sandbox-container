# Tasks

## 1. Baseline

- [x] 1.1 Create branch `establish-sandbox-reference` from `main` (`9ff66c8`) in `sandbox-container`; verify `git status` is clean and the tree equals `sandbox-ref-18` plus the archive commit.
- [x] 1.2 Run the unchanged unit discovery in a disposable container with private executable temporary storage (host `/tmp` is `noexec`); verify it passes, and record the count as the baseline in the scratchpad.

## 2. Fixture profiles and test ownership

- [x] 2.1 Add `tests/fixtures/agent/profile.json` and `policies/default.json` (`fixture-agent`, methods `narrow`/`wide` with `.test` hosts, `login_args`, `credential_env`, `FIXTURE_AGENT_YOLO`, `protected_env` `FIXTURE_AGENT_`) as in design decision 3; verify both load with the current `agent_profile.load()` and `policy.load()`.
- [x] 2.2 Rewrite `tests/sandbox_profile.py` to build the private fixture root (copies of `network/`, `setup/` and the fixture `agent/`) and export the fixture names plus `REAL_ROOT`/`REAL_PROFILE`; verify that importing `common` from a test resolves `PROFILE.name == 'fixture-agent'`.
- [x] 2.3 Move the mechanics tests (`test_network_policy`, `test_session`, `test_qualification`, `test_setup`, `test_toolchains`, `test_guard`, `test_network_feasibility`) to fixture names and `FIXTURE_ROOT` paths; move the eight wrapper-launching setup tests to the per-agent `tests/test_setup_wrapper.py` with real names, and keep `QualificationRuntime` on the real wrapper; verify unit discovery passes with the same count as 1.2 while the checkout still has the Claude profile.
- [x] 2.4 Split `test_agent_profile` into real-profile checks (skipping method checks with a reason when there are none) and fixture-profile checks, and make `test_alignment` scan real plus fixture identifiers; add the fixture files to `SHARED_TESTS`; verify unit discovery passes.
- [x] 2.5 Add the alignment checks from the design (no neutral `SANDBOX_*` harness name starts with the wrapper prefix; no shared test reads the checkout profile directly); verify that each check fails on an injected violation.

## 3. Profiles without authentication methods (shared code)

- [x] 3.1 Add `tests/fixtures/shell-agent/` (`fixture-shell`, `auth: {}`, no `approval_bypass_env`, `profiles: {}`) and loader tests; verify they fail before the code change.
- [x] 3.2 Relax `network/agent_profile.py` (0–8 methods, optional `approval_bypass_env`, `None` handling in the distinct-name check) and `network/policy.py` (empty profiles only without methods); verify the 3.1 tests pass and an empty policy with methods still fails.
- [x] 3.3 Make `session.py`, `qualify.py`/`qualification_records.py` and `setup/toolchains.py` handle a missing bypass variable and refuse provider without methods with `profile declares no authentication method`, before any image, proxy or container operation; verify with fixture-shell tests in `test_session`, `test_qualification` and `test_toolchains`.
- [x] 3.4 Make `setup/common.py` and `setup/setup.py` follow design decision 4 (offline/unrestricted only, offline default, no auth/residual/login/bypass questions, `not applicable` authentication, no bypass or provider variables in the launch environment); verify with fixture-shell questionnaire, defaults, validation and environment tests in `test_setup`, plus the unchanged fixture-agent tests.
- [x] 3.5 Update `network/README.md` for the relaxed schema and the provider refusal; verify unit discovery and `bash tests/run-runtime.sh --setup` pass.

## 4. Reference profile and image

- [x] 4.1 Replace `agent/profile.json` and `agent/policies/default.json` with the reference values (design decision 1, empty policy profiles with a `sandbox-container-…` revision); verify `test_agent_profile` real-profile checks pass and method checks are reported as skipped.
- [x] 4.2 Rewrite `Containerfile` and `.containerignore` (design decision 7: no agent CLI, OpenSpec pinned, `HOME=/sandbox-home`, `SANDBOX_CONTAINER_CONFIG_DIR`, `HISTFILE`, `/sandbox-home` and `/workspace` in a layer, relay/mux copied, `bash` entrypoint); update `test_image_pins.py` (OpenSpec pin, base digest, no agent CLI, CLI/policy test removed); verify `test_image_pins` passes.
- [x] 4.3 Build the image with explicit maintenance authorization; verify `openspec --version` reports 1.16.0, `bash` is the entrypoint, `claude` is absent and the Debian sources use HTTPS (`tests/image-smoke.sh` updated accordingly).

## 5. Shell launcher

- [ ] 5.1 Create `sandbox-container.sh` from `claude-container.sh` (`git mv`) and apply design decisions 5 and 6: profile names, Bash command with forwarded arguments, `--container-shell` as a no-op, YOLO/optional-traffic/API-key code removed, provider rejected, offline default with the early protected-installation check; verify `bash -n` and that help lists only `SANDBOX_CONTAINER_*` variables.
- [ ] 5.2 Rewrite `tests/test_wrapper.py` for the shell: offline default, unrestricted, provider rejection, missing-installation guidance before engine queries, argument/stdin forwarding to Bash, `--container-shell` equivalence, delegation only with unrestricted in both state modes, state layout and `HISTFILE`, CA, budgets, lifetime, worktree, toolchains, cleanup and signals; verify `bash tests/run-runtime.sh --wrapper` passes.
- [ ] 5.3 Update the README sections for usage, modes, state, delegation, CA, worktree, hardening and toolchains, and update `AGENTS.md` to the reference role and file ownership; verify every documented `SANDBOX_CONTAINER_*` variable is listed in help (alignment test) and no Claude usage remains outside history notes.

## 6. Runtime and setup acceptance

- [ ] 6.1 Adapt `tests/test_runtime.py`, `tests/test_setup_runtime.py` and `tests/run-runtime.sh` (image and variable names, guard toolchain image, shell application, no YOLO grid); verify `bash tests/run-runtime.sh` (default mode) and `--setup-runtime` pass.
- [ ] 6.2 Update `docs/setup.md` for the shell questionnaire and managed launcher; run `--container-setup` on this host with offline mode; verify setup reports locally qualified, authentication not applicable, and the managed launcher opens an offline shell with persistent history.
- [ ] 6.3 Run `bash tests/run-runtime.sh --qualification` and `--guard`; verify both pass with the reference installation and the fixture installations.

## 7. Network runtime through the session helper

- [ ] 7.1 Rework `tests/test_network_runtime.py` and `network_tls_fixture.py` to drive `network/session.py` from a protected fixture installation with the reference images by immutable ID (design decision 8), keeping SNI binding, retried ClientHello, shared-address, CA off/on and transport cases; verify `bash tests/run-runtime.sh --network` passes and leaves no fixture-named image tags.
- [ ] 7.2 Run `--network-policy` and `--network-feasibility`; verify both pass.

## 8. Reference role

- [ ] 8.1 Update `tools/propagate.py` messages, docstring and `MANIFEST_HEAD`, and `tests/test_propagate.py`; verify `test_propagate` passes and a dry run against a scratch clone of `codex-container` from `sandbox-ref-18` to a local test tag lists the shared and fixture files and names `sandbox-container`.
- [ ] 8.2 Rewrite `docs/propagation.md` for five targets including Claude, and update `docs/network-contract.md` (reference row, Claude as a target row, offline-default mode table, neutral identity wording); verify the five wrapper rows remain identical to the sibling repositories' rows.

## 9. Integration and tag

- [ ] 9.1 Run unit discovery and every runner mode (`--setup`, `--setup-runtime`, `--qualification`, `--guard`, `--network`, `--network-policy`, `--network-feasibility`, `--wrapper`, default), plus `git diff --check`; verify they all pass.
- [ ] 9.2 Add the `sandbox-ref-19` section to `docs/validation.md` with each mode's result and environment, noting that earlier entries were recorded for the Claude wrapper; verify every mode from 9.1 is listed.
- [ ] 9.3 Commit, merge into `main`, and create the annotated tag `sandbox-ref-19` on the merge commit; verify `git describe --exact-match` on `main` prints `sandbox-ref-19`.

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-19`, then runs setup on the Rocky 9 and newer WSL hosts; record the results.
- Archive this change with spec sync.
- Adopt `sandbox-ref-19` in `claude-container` first (it also removes `tools/propagate.py`, `docs/propagation.md` and the `reference-propagation` spec, and adds `tests/test_reference_copy.py`), then in Codex, OpenCode, Pi and Antigravity, each as its own OpenSpec change. Each adoption also creates its per-agent `tests/test_setup_wrapper.py` from the wrapper-launching tests of its previous shared `tests/test_setup.py`.
