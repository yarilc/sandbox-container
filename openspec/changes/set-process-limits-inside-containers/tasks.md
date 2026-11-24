# Tasks

## 1. Evidence

- [x] 1.1 Record the measurement that motivates the change in `docs/validation.md`.
  - **Setup:** nested rootless containers in a session's `cgroupfs` engine. Each scenario runs beside a container that holds 80 sleeping processes, plus its shell, 81 in all.
  - **Record:**
    - a container created with `--ulimit nproc=40` does not start, and one with `nproc=200` does;
    - a running container created with `--ulimit nproc=100` cannot fork while the other container holds its 81 processes;
    - with `ulimit -u 100` run inside the container instead, it creates 60 processes beside the same 81, and stops at 99 of 150;
    - the Windows validation failures this explains;
    - the kernel rule from design "Context".
  - **Verify:** the scenarios rerun as recorded.

## 2. Agent container

- [x] 2.1 Build the limit step in `launcher/core.sh` (design D1, D2).
  - **Function:** one function wraps the entry program on the `rlimit` mechanism:
    - the guard returned by `session.py agent-args`;
    - the profile's agent program in unrestricted agent mode;
    - `/bin/bash` in shell mode.
  - **Budget arguments:** `budget_args` no longer adds `--ulimit nproc` for the agent.
  - **Verify:** `tests/test_launcher.py` cases, through `tests/fake_podman.py`, for:
    - the created command in the three modes on `rlimit`;
    - no step and no `--ulimit nproc` on `cgroup` and `none`;
    - the qualification probe launch carrying the same step.
- [x] 2.2 Change `budgets_applied` for the fallback (design D3).
  - **Rule:** require the step with the selected budget in the created entry command (`.Path`, then `index .Args` one by one), and refuse a configured `RLIMIT_NPROC` at or below the budget.
  - **Verify:** `tests/test_launcher.py` cases where the fake reports:
    - a missing step;
    - another budget in the step;
    - a configured process rlimit at the budget;
    - an engine default above the budget, which passes.

    Each failure removes only the session's own container and names the fallback.
- [x] 2.3 Keep the effective checks in `setup/smoke.py` and `network/qualification_probe.py`, and change their comments to the per-container rule.
  - **Verify:** `tests/test_qualification.py` still passes its rlimit cases.
- [x] 2.4 Add a runtime independence case to `tests/test_runtime.py` (design D4).
  - **Steps:**
    - start a container holding more processes than `SANDBOX_CONTAINER_PIDS_LIMIT=128`;
    - run a session that creates 100 processes and then tries 200.
  - **Verify:**
    - with the other container running, the 100 succeed and the 200 stop near 128;
    - the case skips when the mechanism is not `rlimit`.

    Remove the old comment that the budget must leave room for container startup.

## 3. Egress proxy

- [x] 3.1 Start the proxy with the step in `network/session.py` instead of `--ulimit nproc`.
  - **Verify:** the proxy argument cases in `tests/test_session.py` show `--entrypoint /bin/sh` with the step and the proxy program, and no `--ulimit nproc`, on `rlimit` only.
- [x] 3.2 Change `network/proxy_hardening.py` for the fallback (design D3).
  - **Rule:**
    - require the step with 128 in the created entry command;
    - refuse a configured `RLIMIT_NPROC` at or below 128;
    - keep the effective `/proc/1/limits` check at 128.
  - **Verify:** `test_proxy_hardening_verification_is_exact_per_enforced_budget` in `tests/test_session.py` covers each rule, including an engine default above 128.
- [x] 3.3 Add a provider runtime case to `tests/test_network_runtime.py`: a session's proxy starts and passes its effective check beside a container holding more than 128 processes.
  - **Verify:** the case passes on the fallback and skips otherwise.

## 4. Session engine

- [x] 4.1 Make `launcher/engine/entrypoint.sh` take the process limit after the port, and set it under `set -eu` before starting its services (design D1, D2). The launcher passes the budget on `rlimit` and no `--ulimit nproc`.
  - **Verify:**
    - `tests/test_engine.py` checks the entrypoint's argument rules;
    - `tests/test_launcher.py` checks the engine's `podman run` arguments on each mechanism.
- [x] 4.2 Verify the engine's effective limit in the readiness check: the limit of PID 2, the entrypoint under `--init`, must equal the budget before the session starts (design D3).
  - **Verify:** `tests/test_launcher.py` cases where the fake reports the budget, another value and no value; the last two stop the launch and remove the engine.
- [x] 4.3 Add an engine runtime case: an engine session starts and runs a nested container beside a container holding more processes than its budget.
  - **Verify:** the case passes where an engine can start, and skips from inside a session's engine, as the other engine cases do.

## 5. Documentation

- [x] 5.1 Correct the per-container explanation in `network/agent_budgets.py`, `launcher/core.sh` (help text and comments) and `AGENTS.md`: the limit is set inside each container, because one applied at creation counts every container of the user.
  - **Verify:** `grep -rn "ulimit nproc\|--ulimit" README.md AGENTS.md docs network launcher setup` finds only the explanation of why it is not used.
- [x] 5.2 Update the README budget section and `docs/network-contract.md`:
  - where the step runs;
  - that `podman exec` processes get the engine-applied limits;
  - that the machine as a whole is bounded only by the user's own limit.

  **Verify:** `git diff --check` passes, and the README's statements match the specs of this change.

## 6. Integration

- [x] 6.1 Run the runner modes from a session through its engine: unit discovery, `--setup`, `--qualification`, the default runtime, `--network` and `--guard`. Run `--setup-runtime` where an engine can start. Record the results under the new tag in `docs/validation.md`, with the tests that had been recorded as `cgroupfs` budget failures re-examined.
  - **Verify:**
    - every mode passes, apart from the failures recorded for `cgroupfs` cgroup limits, which need a cgroup manager;
    - no case fails with `Resource temporarily unavailable`.
- [x] 6.2 Merge, tag `sandbox-ref-34`, and update the reference parity row.
  - **Verify:** `git describe --exact-match` on `main` prints the tag, and `python3 -m unittest tests.test_alignment` passes.

## Workflow follow-up

- Move the Claude adoption to `sandbox-ref-34` with `tools/propagate.py`. Have the operator rerun setup and `tools/windows-validate.ps1` on Windows, with the operator's own Claude session running; no case should fail with `crun: clone`.
- Archive the change after review, syncing `container-isolation` and `network-egress`.
