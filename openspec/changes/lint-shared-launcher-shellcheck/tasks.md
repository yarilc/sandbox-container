# Tasks

## 1. Lint the shared launcher files

- [x] 1.1 Add `tools/shellcheck.sh` (design decision 3). Verify that `bash -n tools/shellcheck.sh` succeeds and that running it on this checkout reports the findings listed in design "Context" and exits nonzero.
- [x] 1.2 Edit `launcher/core.sh` (design decision 1): the `shell=bash` directive, commented SC2154 directives for the nine `capture_response` targets and `wrapper_dir`, and quoting for `noexec`, `exec` and the `--mount` and `--tmpfs` option lists. Verify that `git diff launcher/core.sh` changes only comments and quoting, and that `bash tools/shellcheck.sh .` reports nothing for `launcher/core.sh`.
- [x] 1.3 Add the agent-part directive (design decision 2) to `tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh` and `agent/launcher.sh`. Verify that `bash tools/shellcheck.sh .` exits 0.

## 2. Verification and documentation

- [x] 2.1 Run `python3 -m unittest tests.test_launcher tests.test_alignment tests.test_agent_profile` in the disposable test container and `bash tests/run-runtime.sh --wrapper`. Verify that they pass with the tests unchanged.
- [x] 2.2 Run `bash tools/shellcheck.sh` on the five wrapper checkouts without changing them. Record, per wrapper, which findings come from the shared files (fixed by the next tag) and which from its own `agent/launcher.sh` (fixed in its next adoption).
- [x] 2.3 Document the lint command in `AGENTS.md` and the agent-part directive in `docs/launcher-contract.md` ("Profile data in `agent/launcher.sh`"). Add a `docs/validation.md` section with the results of tasks 1.1 to 2.2 and the note that no tag is taken (design decision 4).
- [x] 2.4 Commit on `main` without a tag. Verify with `git tag --points-at HEAD` that no tag was added.

## Workflow follow-up

- Archive this change with spec sync.
- The next reference change that changes `launcher/core.sh` and takes a tag names this change in its validation record. In that adoption, Claude, Codex and Antigravity add the directive to their own `agent/launcher.sh`, and every wrapper reruns `--container-setup` once.
