# Tasks

## 1. Engine image: eligibility and startup

- [x] 1.1 Add the eligibility program `launcher/engine/cgroup.sh`, installed as `/usr/local/bin/sandbox-engine-cgroup` (design D2).
  - **Rule:** a private cgroup namespace (`0::/`), `cgroup2fs`, a read-write mount with `nsdelegate`, and the root owned by `0:0` (eligible) or `1000:1000` with the engine's processes below it (delegated); otherwise `ineligible: <reason>`.
  - **Inputs:** read-only; the `/proc` and `/sys` paths are arguments with the real paths as defaults, so tests can use fixture files.
  - **Verify:**
    - `tests/test_engine.py` cases over fixture files: eligible, delegated, and each ineligible reason (cgroup v1, shared namespace, read-only mount, no `nsdelegate`, foreign owner);
    - `bash tools/shellcheck.sh .`.
- [x] 1.2 Add the startup program `launcher/engine/start.sh`, installed as `/usr/local/bin/sandbox-engine-start` and made the image entrypoint (design D1, D3).
  - **Order:**
    1. the process rlimit, when given;
    2. eligibility through `sandbox-engine-cgroup`;
    3. the delegation writes of D3;
    4. the `capsh` hand-over to the engine user;
    5. `exec /usr/libexec/podman/catatonit -- /usr/local/bin/sandbox-engine <port>`.
  - **Failures:** a failed step on an eligible engine exits non-zero. Started as a user other than root, it skips the delegation.
  - **Entrypoint:** `launcher/engine/entrypoint.sh` keeps only the port argument. The Containerfile keeps `USER podman`. Both new files join the engine inputs (`setup/engine.py INPUTS`) and `.containerignore`.
  - **Verify:**
    - `tests/test_engine.py`: the start program's argument checks, its step order, and the moved process-limit case (formerly `test_entrypoint_sets_the_process_limit_after_the_port`);
    - `test_build_context_admits_only_engine_inputs` and `test_inputs_identity_covers_every_build_input` with the new files;
    - `python3 -m unittest discover -s tests -p test_image_pins.py -v`.
- [x] 1.3 Change the engine options in `setup/engine.py container_options` (design D1): no `--init`, `--user 0:0`, `--cap-add=SETUID,SETGID,SYS_CHROOT,CHOWN`; every other option unchanged.
  - **Verify:** `EngineOptionsTests` asserts the exact option list (`python3 -m unittest discover -s tests -p test_engine.py -v`).

## 2. Launcher

- [x] 2.1 Adapt the engine start in `launcher/core.sh` (design D4).
  - **Command:** `engine_command` starts with `/usr/local/bin/sandbox-engine-start`. On the rlimit fallback, `budgets_applied` verifies `.Path` and `2375 <limit>`, without `init_program`.
  - **Rlimit:** read from `/proc/1/limits`.
  - **User:** every `engine exec` into the engine (readiness, rlimit, eligibility) passes `--user podman`.
  - **Verify:**
    - `tests/test_launcher.py` with `tests/fake_podman.py`: `test_engine_process_rlimit_is_verified_before_the_session`, `test_engine_budgets_follow_the_agent_rules` and the engine argument cases, updated, plus a case that fails when an `exec` into the engine lacks `--user podman`;
    - `bash -n launcher/core.sh` and `bash tools/shellcheck.sh .`.
- [x] 2.2 Report the engine's eligibility after readiness (spec "Ineligible engines are announced", design D2).
  - **Behavior:**
    - `delegated` prints nothing;
    - `ineligible: <reason>` prints the notice with the reason, and the session starts;
    - any other answer stops the launch before the application, naming the engine and leaving no resources.
  - **Verify:** `tests/test_launcher.py` cases for the three answers.
- [x] 2.3 Document the behavior.
  - **README, container tests section:**
    - systemd containers: how to run a systemd image from a session, and the platforms where it works;
    - guaranteed explicit nested limits per controller, replacing "not guaranteed";
    - the delegation exception, with `CAP_CHOWN` in the bounding set;
    - the ineligible-engine notice;
    - that resource-control unit settings have no effect without controllers.
  - **AGENTS.md:** the engine's hardening exceptions now include the startup delegation step.
  - **Verify:** the README exception list matches `container_options` and the spec's "Fixed engine hardening exceptions". Its commands are run as written in task 4.1.

## 3. Qualification

- [x] 3.1 Update `network/qualify.py engine_case` to the new engine (design D5).
  - **`ENGINE_STATE`:** runs as `--user podman`, and expects `CapBnd: 00000000000400c1`, PID 1 `Uid` 1000, `NoNewPrivs: 1` and `Seccomp: 2`.
  - **Report:** the eligibility answer is recorded in the engine section, bound to the engine image identity (`network/qualification_records.py`).
  - **Verify:** `tests/test_qualification.py` cases for a passing probe, the old bounding set (rejected), a root PID 1 (rejected), and a report without the eligibility field (stale).
- [ ] 3.2 Add the cgroup containment checks to `engine_case` (spec "Engine containment is qualified").
  - **Every engine:** write-back of each limit file of the engine's cgroup root, never `cgroup.kill` or `cgroup.freeze`:
    - from the engine user with all capabilities cleared;
    - from a nested root on the probe root file system with `--cgroupns=host --security-opt=unmask=ALL`.
  - **Delegated engines:** a nested probe container runs below the engine's cgroup root.
  - **Ineligible engines:** not a failure.
  - **Docs:** add the checks to the engine containment evidence in `docs/network-contract.md`.
  - **Verify:**
    - `tests/test_qualification.py` cases for a writable limit file (gate fails), a nested container at the root of a delegated engine (gate fails) and an ineligible engine (gate passes);
    - `bash tests/run-runtime.sh --qualification`.

## 4. Runtime tests

- [x] 4.1 Add the systemd fixture and the systemd cases to `SessionEngineTests` in `tests/test_runtime.py` (design D6).
  - **Fixture:** `tests/systemd-sample.Containerfile`, from Rocky Linux 9's init image (`docker.io/rockylinux/rockylinux:9-ubi-init`) pinned by digest through the maintenance procedure in `docs/validation.md`. It has no build step, so it builds without network (`--pull=never`, an empty context), under a tag derived from the recipe's digest. `SANDBOX_TEST_SYSTEMD_SAMPLE` overrides it. The tests skip with guidance when the base image is missing.
  - **Pins:** `tests/test_image_pins.py` checks that the recipe has one digest-pinned base and no build step.
  - **Cases:** on an eligible engine, `systemctl is-system-running` is `running` or `degraded` once boot completes (without `--wait`, which needs D-Bus in the image), a transient unit becomes active, and `journalctl` shows its output; the README's systemd commands run as written.
  - **Verify:**
    - `python3 -m unittest discover -s tests -p test_image_pins.py -v`;
    - `SANDBOX_RUNTIME_TESTS=1 python3 -m unittest discover -s tests -p test_runtime.py -v` on an eligible engine.
- [x] 4.2 Add the delegation cases to `SessionEngineTests`.
  - **Cases:**
    - nested `--memory=64m --pids-limit=32` applies where the engine has `memory` and `pids`, and fails otherwise;
    - no engine process runs as the root of its user namespace, or holds `CAP_CHOWN` outside the bounding set;
    - the engine's limit files are unwritable from a nested root;
    - the eligibility notice is absent on an eligible engine.
  - **Verify:** the same runtime command, with each case skipped, with its reason, where the engine lacks the condition.

## 5. Integration validation

- [ ] 5.1 Run the suites on the Rocky Linux lab host (native Linux, `systemd` manager), from the host: `bash tests/run-runtime.sh`, `--guard` and `--qualification`.
  - **Guard:** run from the host, `--guard` uses the host engine and no nested container, so it is a regression check. The nested limits that its multiplex tests request inside a session are covered by the runtime delegation case (task 4.2).
  - **Record:** the results in `docs/validation.md`, with the spike results of the proposal.
- [ ] 5.2 Run the same suites on the Windows Podman machine.
  - **Expected:** systemd cases pass; the delegation case finds no controller, so nested limits are refused; `--guard` from the host is a regression check, as in task 5.1.
  - **Record:** the results in `docs/validation.md`.
- [ ] 5.3 Run an Ansible test from a session on both platforms, against the `orbit-e2e-lab` Rocky Linux 9 and Amazon Linux 2023 targets: Molecule's Podman driver through `CONTAINER_HOST`, and the lab's own flow.
  - **Scope:** a playbook that manages units and handlers of packages already in the images. Package installation needs `add-read-only-dependency-mirror`.
  - **Record:** the commands and results in `docs/validation.md`.
- [ ] 5.4 Run the runtime and qualification suites on a host with SELinux enforcing and on one with AppArmor active, where available.
  - **Record:** the results in `docs/validation.md`, or record them as unavailable, with the reason.

## Workflow follow-up

- Tag the release and propagate the shared files to the sibling wrappers with `tools/propagate.py` (dry run, then `--apply`), following `docs/propagation.md`.
- Operators rerun setup to build the new engine image and requalify.
- Archive the change after review, and verify the archived `session-container-engine` spec.
