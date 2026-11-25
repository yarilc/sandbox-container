# Proposal

> Status: roadmap. Only this proposal exists. Design, specs and tasks will
> follow when the open questions below are answered. The findings come from
> task 8.2 of `replace-podman-delegation-with-session-engine`, run on
> 2026-11-25.

## Why

The runner suites assume a host with IPv6, every cgroup controller delegated,
a Debian CA bundle path, and a Podman server of the same era as the runtime
image's client. On the native Rocky 9 lab host none of these holds:
- kernel `5.14.0-687.12.1.el9_8` booted with `ipv6.disable=1`;
- Podman 5.8.0 and crun 1.27;
- `systemd` manager with `[memory pids]` delegated, no `cpu`.

On that host, 7 test failures were caused by the tests, not by the product,
in `--network-feasibility`, `--network`, `--guard` and `--setup-runtime`.
They hide real failures and prevent a clean record of all modes on native
Linux.

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
  - Both files are shared, so this needs a new `sandbox-ref-N` tag.
- **Budgets follow the delegated controllers in the network suite.**
  `test_agent_budgets_are_effective_and_lifetime_is_enforced`
  (`tests/test_network_runtime.py`, line 574) always reads `cpu.max`. It
  fails with `FileNotFoundError` where `cpu` is not delegated. The test
  checks each budget only when its controller is delegated, as
  `tests/test_runtime.py` already does through `engine_budgets()`.
- **CA bundle path in the setup acceptance test.**
  `tests/test_setup_runtime.py` answers the CA bundle prompt with
  `/etc/ssl/certs/ca-certificates.crt`. Setup checks that path in the runner
  container, where it exists, but the engine mounts it from the host. On
  Rocky that path does not exist, so qualification stops with
  `statfs /etc/ssl/certs/ca-certificates.crt: no such file or directory`.
  The test must use a path that exists on the engine host. In ordinary use
  setup and the engine share the host, so the product is not affected.
- **Engine tags left by the setup acceptance test.** `clean_tags`
  (`tests/test_setup_runtime.py`) removes the runtime tag recorded in
  `setup.json`, but not the `…-engine:setup-<release>` tag. Each run leaves
  one engine tag per test.
- **Terminal tests with the runtime image's Podman client.** The runner's
  Podman 4.3.1 client talks to the host's Podman 5.8 server. A
  `--read-only` container then gets a read-only `/dev`; the host's 5.8
  client gets `rw`. With a terminal, crun 1.27 fails with
  `unlink /dev/console: Read-only file system`, the case recorded on
  2026-11-10 (`allow-terminal-on-read-only-dev`). An explicit
  `--read-only-tmpfs=true` from the old client does not help. Three tests
  fail through the remote API as `no logs from conmon`:
  - `test_guarded_arguments_stdin_status_and_tty_both_state_modes`;
  - `test_terminal_interrupt_is_delivered_once`;
  - `test_terminal_interrupt_reaches_an_application_without_a_handler`.

  The managed launcher uses the host's client and is not affected. In a
  session, the same 4.3.1 client against the session engine (Podman 6.2.0,
  crun 1.31) passed the terminal tests on Windows.

Not in scope:
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

None expected. The IPv6 fixtures align the tests with the existing
`network-egress` scenario "Host kernel without IPv6", and the other items
change test code only. If the terminal fix changes the runtime image's
Podman client, `runtime-image` may gain a requirement; otherwise the change
sets `skip_specs: true`.

## Impact

- Shared tests: `tests/network_fixture.py` and
  `tests/guard_runtime_fixture.py`. They need a new reference tag. Before
  tagging, run the unit discovery, `--network-feasibility`, `--guard` and
  `--network`.
- Per-wrapper tests: `tests/test_network_runtime.py` and
  `tests/test_setup_runtime.py` in this repository. `tools/propagate.py`
  does not copy them, so each of the five wrappers needs the same fix in its
  own copy, for example in its adoption of the new tag.
- Terminal fix: depends on the open question below. It may touch the
  runtime image inputs (`Containerfile`), the guard test harness
  (`production_command` in `tests/test_guard.py`, shared) or only the
  validation records.
- Validation: rerun every runner mode on the Rocky 9 lab host, which is so
  far the only host without IPv6 and without `cpu` delegation.

## Open Questions

- **Terminal tests against Podman 5 servers.** Three options:
  - a newer pinned Podman client in the runtime image; Debian bookworm ships
    4.3.1, so this needs another pinned source;
  - an explicit writable `/dev` for the terminal containers the tests start.
    The launcher deliberately leaves `/dev` to the engine
    (`use-engine-dev-for-pseudo-terminals`), so this would apply to the test
    harness only;
  - recording it as a known limit of the runner on Podman 5 servers with
    crun 1.27.

  Which server versions show it is not yet measured: Podman 4.9.3 and 6.2.0
  passed, 5.8.0 failed.
- **How the setup acceptance test finds a host CA bundle.** The runner could
  pass the host's path into the test container, or the CA case could run
  only when a path exists both in the runner and on the engine host.
- **Tag scope.** Whether the new tag carries only the IPv6 fixtures, or also
  a terminal fix in the shared guard harness.
