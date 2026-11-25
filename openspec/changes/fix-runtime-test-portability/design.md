# Design

## Context

See proposal.md for the failures and the decisions. The code they touch:

- The qualification gate already handles kernels without IPv6:
  - `ipv6_state()` (`network/qualification_records.py`) returns `present`, or
    `absent` only when `/proc/sys/net/ipv6` is missing and `AF_INET6`
    creation fails with `EAFNOSUPPORT`. Anything else raises.
  - `no_direct_route(ipv6)` (`network/qualification_runtime.py`) accepts that
    error only when told the host has no IPv6.
- `tests/guard_runtime_fixture.py` has the same loop without the state, and
  so does the UDP loop of `tests/network_fixture.py`.
- The fixtures run inside containers:
  - the guard fixture as a script prefixed with `AGENT = ...` and run under
    the guard (`production_container`);
  - the network fixture as `/probe.py probe <token>` in the runtime image.
- Budgets: `tests/test_runtime.py` checks each budget against the controllers
  that `agent_budgets.delegated()` and `process_mechanism()` report, the
  single rule shared with the launcher. `tests/test_network_runtime.py`
  reads every file unconditionally.
- The setup acceptance test keeps its state under `SANDBOX_TEST_STATE_ROOT`,
  a disposable native volume. `tests/run-runtime.sh` mounts that volume at
  its host path in the runner. `clean_tags` removes only `setup.json`'s
  `image`. Setup names the other images of a release
  `PROFILE.image(<kind>, 'setup-' + release)`.
- Terminal tests:
  - the two in `tests/test_guard.py` start their container with
    `production_command(..., extra=('--tty',))`;
  - the case in `tests/test_network_runtime.py` runs the wrapper on a
    pseudo-terminal.
- `tools/propagate.py` prints runner modes from path prefixes (`checklist()`).
  `tests/guard_` maps to `--guard` and `--network`. No prefix maps to
  `--network-feasibility`.

## Goals / Non-Goals

**Goals:**
- The suites pass, or skip with a stated reason, on a host without IPv6,
  without `cpu` delegation, with a CA bundle outside the Debian path, and with
  a Podman 5 server.
- No check is weakened on hosts where it runs today. Skips happen only on the
  measured condition, and contradicting evidence fails.
- The IPv6 rule and the budget rule each have one source: the qualification
  code and `agent_budgets`.

**Non-Goals:**
- Changing production code, the runtime image or the launcher.
- Making the terminal tests pass on Podman 5 servers.
- Changing `tools/propagate.py` (see Open Questions).

## Decisions

### D1. The harness detects the IPv6 state and passes it to the fixtures

Before running a fixture, the harness calls `ipv6_state()` in the runner
container, which shares the engine host's kernel. It passes the result into
the fixture:
- the guard fixture gets `IPV6 = <bool>` next to the `AGENT` prefix;
- the network fixture gets it as an argument after its token.

The fixtures then follow `no_direct_route(ipv6)`:
- create each socket inside the `try`;
- accept a creation failure only for `AF_INET6`, only when IPv6 is absent,
  and only with `EAFNOSUPPORT`;
- fail when IPv6 is absent but an `AF_INET6` socket can be created.

Alternative: detect inside the fixture. Rejected. The guard fixture runs under
Landlock and seccomp, where reading `/proc/sys` may differ from the host, so a
state detected there could be wrong. One detection outside the confined
process matches the gate, which also detects on the engine host and passes
`config['ipv6']`.

Alternative: catch any `OSError` on creation. Rejected, because it would also
accept a guard denial on a host with IPv6, which is not what the check
proves.

### D2. A shared probe for a read-only `/dev`

A new shared module `tests/guard_terminal_probe.py` runs one `--read-only`
container from the test's image through the runner's Podman client. It reads
the `/dev` line of `/proc/mounts` and reports whether `/dev` is read-only. The
result is cached per image for the test process.

- If the probe container cannot run, or no `/dev` line is found, the probe
  raises. A broken probe never turns into a skip.
- The two terminal tests in `tests/test_guard.py`, and the terminal case of
  `test_guarded_arguments_stdin_status_and_tty_both_state_modes`, call it and
  skip when `/dev` is read-only. The skip message names the cause, the
  runner client's read-only `/dev` under `--read-only`, and points to the
  manual check.
- The non-terminal part of that network test still runs.

The module is listed in `SHARED_TESTS` (`tests/test_alignment.py`). Its
`guard_` prefix makes `tools/propagate.py` print `--guard` and `--network`
when it changes, the modes of its callers.

This refines proposal.md's file list for the tag: the tag also carries the new
module and the `SHARED_TESTS` entry.

Alternative: compare client and server versions. Rejected. The failing
versions are not measured (4.9.3 and 6.2.0 pass, 5.8.0 fails), and the probe
measures the condition that breaks the terminal.

Alternative: the probe in `sandbox_profile.py`. Rejected, because that module
is the profile view, and a change there maps only to `--shared`.

Alternative: a copy of the probe in `test_network_runtime.py`. Rejected, as
six per-wrapper copies would drift.

### D3. Budgets in the network suite use the shared rule

`test_agent_budgets_are_effective_and_lifetime_is_enforced` queries
`Host.CgroupControllers`, `Host.CgroupManager` and `Host.Kernel`. It derives
the delegated controllers and the process mechanism with
`agent_budgets.delegated()` and `process_mechanism()`, and passes them to
the in-container check. The check mirrors `tests/test_runtime.py`:
- a delegated controller's file holds the budget;
- an undelegated one reads `max`, or is absent;
- on the `rlimit` mechanism, `/proc/self/limits` holds the process budget.

The lifetime part is unchanged.

Alternative: import `engine_budgets()` from `tests/test_runtime.py`.
Rejected, to avoid importing one test module into another. The rule itself
stays in `agent_budgets`, and only the three `podman info` queries are
repeated.

### D4. The CA bundle is a copy in the test's native state

When the CA case runs, `answers()` copies the runner's
`/etc/ssl/certs/ca-certificates.crt` to `self.base / 'ca-bundle.pem'`. That
directory is under `SANDBOX_TEST_STATE_ROOT`, at the same path in the runner
and on the host. The copy's path answers the prompt.

The test keeps asserting that the CA is trusted: the qualification and the
session use that path, through setup's readable-file check, the launcher's
`readlink -f` and the engine's bind.

### D5. `clean_tags` removes every tag named after a test's release

For each release the test created (`releases/*/setup.json`), `clean_tags`
removes:
- the recorded `image`;
- `REAL_PROFILE.image(kind, 'setup-' + release)` for the engine, the guard
  toolchain and the proxy, when that tag exists.

It uses `podman image rm <tag>` as today, so an image with other names, such
as the operator's engine image, only loses the test's tag. Release names are
unique per run, so these tags belong to the test.

### D6. The manual terminal check is part of the testing guidance

`AGENTS.md` (Testing Guidelines) states:
- where the runner's Podman client gets a read-only `/dev`, the terminal
  tests skip;
- validation records them as unavailable;
- the operator's interactive session on that host is the evidence for the
  `container-isolation` scenario "Terminal attaches on an engine that mounts
  /dev read-only".

The wrappers carry the same sentence in their adoption of the tag.

## Risks / Trade-offs

- [The probe reports read-only on a host where a terminal would attach] →
  The terminal tests skip needlessly there. The probe measures the
  precondition of the failure, not a proxy for it, and the other runners
  keep the coverage.
- [A guard regression in signal handling ships unnoticed on Podman 5 hosts]
  → The guard binary is the same everywhere, and the tests still run on WSL,
  the Podman machine and the session engine. The manual session covers
  terminal attach on the lab host.
- [The IPv6 state is wrong in the runner] → `ipv6_state()` raises on
  unverifiable evidence, and the fixtures fail when the state contradicts
  socket creation. Neither path turns into a pass.
- [The per-wrapper fixes drift between wrappers] → Each adoption copies the
  reference's versions of the two per-wrapper tests, adapted only in names.
  The adoption proposals list them.
- [`propagate.py` does not print `--network-feasibility` for the changed
  fixture] → The tag's validation record and the wrappers' adoption
  proposals list it explicitly.

## Migration Plan

1. Implement in `sandbox-container`, on a branch.
2. Run on WSL, where IPv6 is present and the client matches:
   - the unit discovery, `--network-feasibility`, `--guard` and `--network`;
   - `--setup-runtime` and the default mode, for the per-wrapper tests.

   The terminal tests must run there, not skip.
3. The operator runs the same modes on the Rocky 9 lab host. The terminal
   tests must skip with the probe's reason, every other test must pass, and
   one interactive session is recorded.
4. Record both runs in `docs/validation.md` under `sandbox-ref-35`. Merge,
   tag `sandbox-ref-35` on the merge commit, and set the reference cell of
   the parity table, following `docs/propagation.md`.
5. Each wrapper adopts `sandbox-ref-35` in its own change. That change carries:
   - the two per-wrapper test fixes and the `AGENTS.md` sentence;
   - the Claude scenario noted in proposal.md.

**Rollback:** the change touches tests and documentation only. Reverting the
merge and not adopting the tag restores the previous behavior.

## Open Questions

- Whether `checklist()` in `tools/propagate.py` should map
  `tests/network_fixture.py` and `tests/test_network_feasibility.py` to
  `--network-feasibility`. It does not change this design: the mode is
  listed by hand until then.
- Which Podman server versions give the old client a read-only `/dev`. The
  probe does not depend on the answer.
