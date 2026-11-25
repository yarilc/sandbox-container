# Proposal

## Why

The runner suites assume a host with IPv6, every cgroup controller delegated,
a Debian CA bundle path, and a Podman server of the same era as the runtime
image's client. On the native Rocky 9 lab host none of these holds:
- kernel `5.14.0-687.12.1.el9_8` booted with `ipv6.disable=1`;
- Podman 5.8.0 and crun 1.27;
- `systemd` manager with `[memory pids]` delegated, no `cpu`.

Task 8.2 of `replace-podman-delegation-with-session-engine` ran there on
2026-11-25. 7 test failures were caused by the tests, not by the product, in
`--network-feasibility`, `--network`, `--guard` and `--setup-runtime`. They
hide real failures and prevent a clean record of all modes on native Linux.

## What Changes

- **IPv6-less kernels in the shared fixtures.** `tests/network_fixture.py`
  (line 121) and `tests/guard_runtime_fixture.py` (line 155) create an
  `AF_INET6` socket outside the `try` that expects the denial. On a kernel
  without IPv6 the creation itself raises `EAFNOSUPPORT`, so
  `test_isolated_agent_unix_proxy` and
  `test_production_filter_and_landlock_on_real_rootless_kernel` fail.
  - The qualification gate already treats `EAFNOSUPPORT` on `AF_INET6` as
    the IPv6 denial (`kernel_rejects_ipv6()` in
    `network/qualification_probe.py`).
  - The fixtures accept it the same way, and only when the kernel lacks
    IPv6.
- **Budgets follow the delegated controllers in the network suite.**
  `test_agent_budgets_are_effective_and_lifetime_is_enforced`
  (`tests/test_network_runtime.py`, line 574) always reads `cpu.max`. It
  fails with `FileNotFoundError` where `cpu` is not delegated. The test
  checks each budget only when its controller is delegated, as
  `tests/test_runtime.py` already does through `engine_budgets()`.
- **CA bundle copied into the native test volume.**
  `tests/test_setup_runtime.py` answers the CA bundle prompt with
  `/etc/ssl/certs/ca-certificates.crt`. Setup checks that path in the runner
  container, where it exists, but the engine mounts it from the host. On
  Rocky that path does not exist, so qualification stops with
  `statfs /etc/ssl/certs/ca-certificates.crt: no such file or directory`.
  - The test copies the runner's bundle into the disposable native volume
    (`SANDBOX_TEST_STATE_ROOT`), and answers the prompt with that path.
  - The volume has the same path in the runner and on the engine host.
    `tests/run-runtime.sh` already relies on this for the test state.
  - Setup requires only a readable regular file there, and the launcher
    resolves it with `readlink -f`.
  - In ordinary use setup and the engine share the host, so the product is
    not affected.
- **Engine tags left by the setup acceptance test.** `clean_tags`
  (`tests/test_setup_runtime.py`) removes the runtime tag recorded in
  `setup.json`, but not the `…-engine:setup-<release>` tag. Each run leaves
  one engine tag per test. `clean_tags` also removes the engine tag.
- **Terminal tests skipped where the runner's client gets a read-only
  `/dev`.** The runner's Podman 4.3.1 client talks to the host's Podman 5.8
  server. A `--read-only` container then gets a read-only `/dev`, while the
  host's 5.8 client gets `rw`. With a terminal, crun 1.27 fails with
  `unlink /dev/console: Read-only file system`, the case recorded on
  2026-11-10 (`allow-terminal-on-read-only-dev`). An explicit
  `--read-only-tmpfs=true` from the old client does not help. Three tests
  fail through the remote API as `no logs from conmon` before checking
  anything:
  - `test_terminal_interrupt_reaches_an_application_without_a_handler` and
    `test_terminal_interrupt_is_delivered_once` (`tests/test_guard.py`,
    shared). Their harness `production_command` starts the container;
  - the terminal case of
    `test_guarded_arguments_stdin_status_and_tty_both_state_modes`
    (`tests/test_network_runtime.py`). It starts the production launcher on
    a pseudo-terminal, and the launcher adds `--tty` itself.

  The tests stay, because they back the scenarios "Interrupt from the
  terminal" and "One interrupt" (`network-egress`) and "Guarded pipeline and
  terminal" (`container-launcher`). A direct probe runs a `--read-only`
  container through the runner's client and reads the `/dev` mount. When
  `/dev` is read-only, the three cases skip with that reason, and validation
  records them as unavailable, never as passed. Elsewhere they run as
  before: they pass on WSL (Podman 4.9.3), on the Podman machine (6.1.4) and
  through the session engine (6.2.0).

  The managed launcher uses the host's client and is not affected. On Podman
  5 hosts with crun 1.27, the `container-isolation` scenario "Terminal
  attaches on an engine that mounts /dev read-only" stays a manual check:
  the operator opens an interactive session with the host's client at each
  validation, and the record says so.

Not in scope:
- A newer Podman client in the runtime image. It would make the three tests
  run on Podman 5 servers, but it is a product change that touches the
  `Containerfile` of every wrapper and the client agents use in sessions. It
  needs its own change, together with the design risk "Old Podman clients in
  the session".
- An explicit writable `/dev` in the tests. The production launcher's case
  would stay broken, and the launcher deliberately leaves `/dev` to the
  engine (`use-engine-dev-for-pseudo-terminals`).
- Nested explicit limits (`--memory`, `--pids-limit` on containers inside
  the session engine). They fail because the engine's cgroup belongs to
  root in its user namespace, while the engine runs as uid 1000 (design D4
  of the session engine change). That change records them as a known limit.
- CPU budgets where `cpu` is not delegated. These stay announced and
  unenforced; setup never changes host delegation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The IPv6 fixtures align the tests with the existing `network-egress`
scenario "Host kernel without IPv6". The other items change test code and
validation records only, so the change sets `skip_specs: true`.

## Impact

- **Shared tests**, which need the new tag `sandbox-ref-35`:
  - `tests/network_fixture.py` and `tests/guard_runtime_fixture.py` (IPv6);
  - `tests/test_guard.py` (the read-only `/dev` probe and the two skips).

  Before tagging, run the unit discovery, `--network-feasibility`, `--guard`
  and `--network`, on the Rocky 9 lab host and on WSL. The lab host is so far
  the only host without IPv6 and without `cpu` delegation. WSL has IPv6 and a
  matching client, and shows that nothing regresses there.
- **Per-wrapper tests** in this repository:
  - `tests/test_network_runtime.py`: the budgets, and the terminal case skip;
  - `tests/test_setup_runtime.py`: the CA copy, and the engine tag cleanup.

  `tools/propagate.py` does not copy them, so each of the five wrappers
  needs the same fixes in its own copy, in its adoption of `sandbox-ref-35`.
  Claude's adoption also adds the `session-container-engine` scenario
  "Interfaces of a restricted session with an engine", which its copy of the
  spec lacks.
- **Validation:**
  - rerun every runner mode on the Rocky 9 lab host;
  - record the terminal cases as unavailable there, with the probe's reason;
  - record the operator's interactive session on that host.

## Decisions

- **Terminal tests against Podman 5 servers.** The tests skip where the
  runner's client gets a read-only `/dev`. This is detected by a direct probe
  rather than by comparing versions, because the condition is what breaks
  the terminal, and which server versions show it is not measured: Podman
  4.9.3 and 6.2.0 passed, 5.8.0 failed. Terminal attach on Podman 5 with
  crun 1.27 keeps manual evidence. A newer client in the runtime image is
  left to a separate change.
- **CA bundle in the setup acceptance test.** The test copies the runner's
  bundle into the native volume. This was preferred over mounting the host's
  bundle into the runner, which would change `tests/run-runtime.sh` in every
  repository and need each distribution's bundle path.
- **Tag scope.** `sandbox-ref-35` carries the two IPv6 fixtures and the
  terminal skip in `tests/test_guard.py`. Everything else is per-wrapper.
