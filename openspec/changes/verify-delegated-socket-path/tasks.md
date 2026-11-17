# Tasks

## 1. Failing cases first

- [ ] 1.1 Commit this change directory on `main` and create the branch `verify-delegated-socket-path`. Add `test_reported_host_socket_must_be_a_socket_when_visible` to `tests/test_launcher.py` and extend `test_socket_validation_rejects_rootful_and_cr_responses` in `tests/test_setup.py` (design decision 3). Verify that, in the disposable test container, the refusal subtests fail against the current core and setup, and the accepted ones pass.

## 2. Fix

- [ ] 2.1 Add the two checks to `core_engine_delegation` in `launcher/core.sh` and mirror them in `verify_socket` in `setup/setup.py` (design decisions 1 and 2). Verify that `python3 -m unittest tests.test_launcher tests.test_wrapper tests.test_alignment tests.test_setup` passes in the disposable test container.
- [ ] 2.2 Update `docs/launcher-contract.md` and `docs/launcher-test-map.md` (design decision 4). Verify that the contract names the remapped-socket limit and that the test map maps Antigravity's `test_complete_socket_response_required` to the new shared case.

## 3. Validation and integration

- [ ] 3.1 Run the unit discovery in the disposable test container, `bash tests/run-runtime.sh --wrapper`, `--setup` and the default runtime run, and `git diff --check` (design decision 5). Verify that all pass.
- [ ] 3.2 Add the section "Delegated socket path (`sandbox-ref-25`)" to `docs/validation.md` with every result, the operator setup marked pending. Commit, merge into `main`, and verify that `openspec validate verify-delegated-socket-path` passes.

## Workflow follow-up

- The operator pushes `main` and runs `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host; then the merge is tagged `sandbox-ref-25` (annotated) and the tag pushed.
- Archive this change with spec sync.
- Claude, Codex and Antigravity adopt `sandbox-ref-25` in their own changes; Codex's change also corrects its `network-egress` scenario that names offline as the qualification default. Pi and OpenCode adopt `sandbox-ref-25` in their full adoptions.
