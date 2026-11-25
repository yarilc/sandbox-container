# Tasks

## 1. Kernels without IPv6 in the shared fixtures

- [x] 1.1 Pass the IPv6 state to the guard fixture, and make its direct-route loop follow `no_direct_route(ipv6)` (design D1).
  - **Harness:** `test_production_filter_and_landlock_on_real_rootless_kernel` calls `ipv6_state()` from `network/qualification_records.py` in the runner. It prefixes `IPV6 = <bool>` to `tests/guard_runtime_fixture.py`, next to `AGENT`.
  - **Fixture:** each socket is created inside the `try`. A creation failure is accepted only for `AF_INET6`, only with `IPV6` false, and only with `EAFNOSUPPORT`. An `AF_INET6` socket created while `IPV6` is false fails the fixture.
  - **Verify:** on WSL, `bash tests/run-runtime.sh --guard -k test_production_filter_and_landlock_on_real_rootless_kernel` passes with IPv6 present.
- [x] 1.2 Pass the IPv6 state to the network fixture, and apply the same rule to its UDP loop (design D1).
  - **Harness:** `tests/test_network_feasibility.py` runs `ipv6_state()` once and passes it as the argument after the token of `/probe.py probe`.
  - **Fixture:** the `probe` loop of `tests/network_fixture.py` creates each socket inside the `try`, with the rule of task 1.1.
  - **Verify:** on WSL, `bash tests/run-runtime.sh --network-feasibility` passes.

## 2. Terminal tests where no terminal attaches through the runner's client

- [x] 2.1 Add the shared probe `tests/guard_terminal_probe.py` (design D2), and list it in `SHARED_TESTS` in `tests/test_alignment.py`.
  - **Probe:** it starts one `--read-only` container from the given image with `--tty`, through the runner's client on a pseudo-terminal. If that fails, it starts the same container without a terminal and reads the `/dev` line of `/proc/mounts`. The result is cached per image.
  - **Result:** no reason when the terminal container starts. A skip reason only when it fails, the container starts without a terminal, and `/dev` is read-only.
  - **Errors:** a container that also fails without a terminal, no `/dev` line, or a writable `/dev` raises; none leads to a skip.
  - **Skip reason:** it names the runner client's read-only `/dev`, carries the engine's error, and points to the manual terminal check.
  - **Verify:** `python3 -m unittest tests.test_alignment` passes, including the shared list and the agent-literal scan.
- [x] 2.2 Skip the two terminal tests of `tests/test_guard.py` where no terminal attaches.
  - **Where:** `run_in_terminal` calls the probe with the test's image before it starts the container, and skips with the probe's reason.
  - **Verify:** on WSL, `bash tests/run-runtime.sh --guard -k test_terminal_interrupt` runs both tests, without skipping, and they pass.
- [x] 2.3 Skip only the terminal case of `test_guarded_arguments_stdin_status_and_tty_both_state_modes` in `tests/test_network_runtime.py` where no terminal attaches.
  - **Where:** in each state mode, the terminal case runs in its own `subTest`, which skips with the probe's reason. The piped case still runs in both state modes.
  - **Verify:** on WSL, `bash tests/run-runtime.sh --network -k test_guarded_arguments_stdin_status_and_tty_both_state_modes` passes with both terminal cases run.
- [x] 2.4 Add the manual terminal check to the Testing Guidelines of `AGENTS.md` (design D6).
  - **Contents:** where no terminal attaches through the runner's client on a read-only `/dev`, the terminal tests skip with the engine's error, and validation records them as unavailable. The operator's interactive session on that host is the evidence for the `container-isolation` scenario "Terminal attaches on an engine that mounts /dev read-only".
  - **Verify:** the paragraph names the skip, the unavailable record and the manual session, and `git diff --check` passes.

## 3. Per-wrapper runtime tests

- [x] 3.1 Make `test_agent_budgets_are_effective_and_lifetime_is_enforced` in `tests/test_network_runtime.py` follow the shared budget rule (design D3).
  - **Rule:** from `Host.CgroupControllers`, `Host.CgroupManager` and `Host.Kernel`, the test derives the delegated controllers and the process mechanism with `agent_budgets.delegated()` and `process_mechanism()`.
  - **Check:** a delegated controller's file holds the budget, and an undelegated one reads `max` or is absent. On the `rlimit` mechanism, `/proc/self/limits` holds the process budget. The lifetime part is unchanged.
  - **Verify:** on WSL (`systemd`, `[cpu memory pids]`), `bash tests/run-runtime.sh --network -k test_agent_budgets_are_effective_and_lifetime_is_enforced` passes, and still checks all three limits.
- [x] 3.2 Copy the CA bundle into the test's native state in `tests/test_setup_runtime.py` (design D4).
  - **Where:** for the CA case, `answers()` copies `/etc/ssl/certs/ca-certificates.crt` to `self.base / 'ca-bundle.pem'` and answers the prompt with that path.
  - **Verify:** on WSL, `bash tests/run-runtime.sh --setup-runtime` passes both tests, and the fresh offline case still reports `Sandbox qualification: locally-qualified` with CA trust.
- [x] 3.3 Make `clean_tags` in `tests/test_setup_runtime.py` remove every tag named after a release the test created (design D5).
  - **Tags:** for each `releases/*/setup.json`, the recorded `image`, and `REAL_PROFILE.image(kind, 'setup-' + release)` for the engine, the guard toolchain and the proxy, when the tag exists. Removal uses `podman image rm <tag>`.
  - **Verify:** on WSL, compare `podman images --format '{{.Repository}}:{{.Tag}}'` before and after `--setup-runtime`. No `:setup-` tag of the test's releases remains, and the operator's tags, such as `…-engine:latest`, are still present.

## 4. Integration validation

- [x] 4.1 Run every runner mode on WSL, where IPv6 is present and a terminal attaches through the runner's client.
  - **Modes:**
    - the unit discovery, the default mode, `--setup` and `--setup-runtime`;
    - `--qualification` and `--wrapper`;
    - `--network-feasibility`, `--network-policy`, `--mux`, `--network` and `--guard`;
    - `bash tools/shellcheck.sh .` and `bash tools/powershell.sh .`.
  - **Expected:** the terminal tests run and pass, and no test skips because of the probe.
  - **Record:** the results in `docs/validation.md`, under a section that names `sandbox-ref-35`.
- [x] 4.2 Have the operator run the same modes on the Rocky 9 lab host.
  - **Expected:**
    - every test passes, except the three terminal cases, which skip with the probe's reason;
    - the operator's interactive session attaches its terminal.
  - **Record:** in the same section, with the terminal cases as unavailable and the session as the manual evidence. `--network-feasibility` is listed even though `tools/propagate.py` does not print it for this fixture.
- [x] 4.3 Run the repository checks.
  - **Checks:**
    - `openspec validate fix-runtime-test-portability --strict`;
    - `python3 -m unittest discover -s tests`;
    - `git diff --check`.
  - **Verify:** all pass.

## Workflow follow-up

- Merge into `main`, tag `sandbox-ref-35` on the merge commit, and set the reference cell of the parity table, following `docs/propagation.md`.
- Archive the change.
- Each wrapper adopts `sandbox-ref-35` in its own change. That change:
  - copies the fixes of tasks 2.3, 3.1, 3.2 and 3.3 into its own tests, and the sentence of task 2.4 into its `AGENTS.md`;
  - runs `--network-feasibility` in addition to the modes the tool prints.

  Claude's adoption also adds the missing `session-container-engine` scenario "Interfaces of a restricted session with an engine".
