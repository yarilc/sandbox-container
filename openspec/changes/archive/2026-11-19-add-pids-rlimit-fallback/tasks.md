# Tasks

## 1. Measure the engine representation

- [x] 1.1 On the rootless Podman 4.9.3 server and on the Podman machine 6.1.4 WSL distribution, create a `--userns=keep-id` container with and without `--ulimit nproc=64:64`. Record `podman inspect --format '{{json .HostConfig.Ulimits}}' <id>` and `{{.HostConfig.PidsLimit}}` for both cases in a new `docs/validation.md` section for this change. Verify: the section shows the four outputs and states whether Podman adds its own default `RLIMIT_NPROC` entry.

## 2. Shared mechanism rule

- [x] 2.1 Add `process_mechanism(controllers, kernel)` to `network/agent_budgets.py`, returning `cgroup`, `rlimit` or `none` (design D1), and add the `process` field to `agent_hardening()`. Verify: new unit cases pass for `pids` present, WSL `6.6.87.2-microsoft-standard-WSL2`, `5.14.0`, `5.13.19`, distribution suffixes and malformed or empty kernel strings.
- [x] 2.2 Add the Bash equivalent of the rule in `launcher/core.sh`, and extend `test_budget_rules_match_shared_python_module` in `tests/test_launcher.py` with the same kernel cases. Verify: `python3 -m unittest discover -s tests -p 'test_launcher.py' -v` passes and both implementations agree on every case.
- [x] 2.3 Add `delegated(controllers, manager)` to `network/agent_budgets.py` (design D0): the reported controllers with the `systemd` manager, none otherwise, and `ControllerError` for a malformed manager. Add the Bash equivalent in `launcher/core.sh` and extend the shared Bash/Python consistency test with manager cases (`systemd`, `cgroupfs`, empty, uppercase, multi-record). Verify: unit cases and the consistency test pass.

## 3. Agent launch

- [x] 3.1 Query `.Host.Kernel` as a single-record engine response in `core_engine_session`, and teach `tests/fake_podman.py` to answer it (for example through `FAKE_KERNEL`). Verify: a multi-record or CR-containing kernel response stops before image operations, and an unparseable kernel string selects `none`.
- [x] 3.2 Build the agent budget arguments per mechanism (`--pids-limit=-1 --ulimit nproc=N:N` for `rlimit`) and print the notices of design D6. Extend `test_budgets_follow_delegated_controllers`. Verify: without `pids` on kernel 5.14 or later the arguments carry `--ulimit nproc=512:512` (and `1024` with `SANDBOX_CONTAINER_PIDS_LIMIT=1024`) and the rlimit notice; on 5.13 or an unparseable kernel there is no `--ulimit` and the notice gives the reason; with `pids` there is no `--ulimit` and no process notice.
- [x] 3.3 Extend the post-create check to read the `RLIMIT_NPROC` entry of `HostConfig.Ulimits` with the parser shape measured in 1.1 (design D4), and teach `tests/fake_podman.py` to report configurable `Ulimits`. Extend `test_ignored_budgets_stop_before_start_and_remove_owned_container`. Verify: a missing entry or a different soft or hard value under `rlimit` removes only the owned container, exits non-zero before the application starts, and names the process rlimit fallback; a Podman default `nproc` entry is accepted under `cgroup` and `none`.
- [x] 3.4 Update the wrapper help in `launcher/core.sh` and the README "Hardening, budgets and lifetime" section. Cover the fallback rule, its per-session scope, the Linux 5.14 condition, the startup-task overhead and that memory and CPU have no fallback. Add the new and changed tests to `docs/launcher-test-map.md`. Verify: the help test still passes without engine queries, `bash tools/shellcheck.sh .` and `bash -n launcher/core.sh` pass, and `git diff --check` is clean.
- [x] 3.5 Query `.Host.CgroupManager` in `core_engine_session`, derive budgets and the process mechanism from the delegated set, name the manager in the notices (design D6) and teach `tests/fake_podman.py` to answer the query. Extend the README, help and AGENTS.md budget text. Verify: with `cgroupfs` and every controller reported, the launch requests no `--memory`, `--cpus` or `--pids-limit=512`, carries `--ulimit nproc=512:512`, and prints the manager notices; a malformed manager stops before image operations.

## 4. Session proxy

- [x] 4.1 In `network/session.py`, read the engine kernel together with the controllers, select the proxy mechanism with `process_mechanism`, add `--pids-limit=-1 --ulimit nproc=128:128` for `rlimit`, print the proxy notices of design D6 and pass the mechanism to the host-side verification. Verify: new `tests/test_session.py` cases cover the arguments and notices for `cgroup`, `rlimit` and `none`.
- [x] 4.2 Extend `network/proxy_hardening.py`: `probe` reports the `Max processes` row of `/proc/1/limits`, and `verify` requires `RLIMIT_NPROC` soft and hard of 128, a `PidsLimit` of 0 or -1 and an absent or unlimited `pids.max` under `rlimit`. Update its failure message. Verify: proxy hardening unit cases accept the exact record and reject a missing, different or soft-only limit.
- [x] 4.3 Update `network/README.md` where proxy budgets are described. Verify: it states the proxy fallback and its condition.
- [x] 4.4 In `network/session.py`, read the cgroup manager and derive the proxy budgets from the delegated set, with the manager named in the notices. Verify: a `tests/test_session.py` case with `cgroupfs` and every controller reported creates the proxy without `--memory` or `--pids-limit=128` and with `--ulimit nproc=128:128`.

## 5. Setup and qualification

- [x] 5.1 In `setup/setup.py`, read the engine kernel, list the process budget mechanism in the setup plan for the agent and for the provider proxy, and pass the mechanism to the smoke. In `setup/smoke.py`, compare the effective `Max processes` soft and hard values with the saved budget under `rlimit`. Verify: new `tests/test_setup.py` cases cover the plan lines for all three mechanisms and the smoke check accepting the exact limit and rejecting a missing or different one.
- [x] 5.2 In `network/qualification_records.py`, bind the agent and proxy `process` mechanism into the identity (design D5). In `network/qualification_probe.py`, measure the effective process rlimit under `rlimit`. Verify: new `tests/test_qualification.py` cases show that a mechanism change between qualification and launch reports mismatched evidence, and that the probe accepts the exact limit and rejects a missing one.
- [x] 5.3 Update `docs/setup.md` where the setup plan's budget lines are described. Verify: the documented plan output matches the new lines.
- [x] 5.4 In `setup/setup.py`, derive the plan and smoke budgets from the delegated set, and in `network/qualification_records.py`, derive the agent and proxy hardening from it. Update `docs/setup.md` and `network/README.md`. Verify: `tests/test_setup.py`, `tests/test_setup_wrapper.py` and `tests/test_qualification.py` cases with `cgroupfs` show no enforced cgroup budget, the manager in the plan lines and the rlimit mechanism in the identity.

## 6. Integration and release checks

- [x] 6.1 Run `test_launcher.py`, `test_wrapper.py`, `test_session.py`, `test_setup.py`, `test_qualification.py`, `test_agent_profile.py` and `test_alignment.py`, then `bash tools/shellcheck.sh .` and `git diff --check`. Verify: no new failures compared with `main` on the same runner, with environment failures listed as such.
- [x] 6.2 On the rootless WSL host with `pids` delegated, run `bash tests/run-runtime.sh` in unrestricted mode. Verify: no `--ulimit` in the created configuration, no process notice, results recorded in `docs/validation.md`.
- [x] 6.3 On an engine that does not delegate `pids`, on a kernel of 5.14 or later (the Podman machine WSL distribution with the `cgroupfs` manager, with a checkout copy on its ext4 file system, in unrestricted mode), run a session. Verify, and record in `docs/validation.md`: the memory and CPU notices naming `cgroupfs`, the rlimit notice, `ulimit -u` reporting the budget inside, fork failing near the budget, `ulimit -u` being impossible to raise, and two concurrent sessions reaching their limits independently.
- [x] 6.4 Run the runner modes that `docs/propagation.md` requires for the changed shared files: `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--guard` and `--network`. Verify: every mode is recorded as passed or unavailable in `docs/validation.md`, under the section that names the new tag, and none fails.

## Workflow follow-up

- Merge into `main`, create the annotated `sandbox-ref-N` tag on the merge commit and update the `Reference (...)` cell of the parity table in `docs/network-contract.md`.
- Propagate the tag to the Claude, Codex, OpenCode, Pi and Antigravity wrappers with `tools/propagate.py` (dry run, then `--apply`).
- Archive the change and sync its specs after review.
