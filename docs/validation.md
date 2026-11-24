# Validation record

## Reference tag `sandbox-ref-34`: 2026-11-24

Change `set-process-limits-inside-containers` (task 6.1). On the process
rlimit fallback, the agent, the egress proxy and the session engine now set
their process limit inside the container, instead of receiving
`--ulimit nproc`. The measurement that motivated it is the next section.

Found during implementation:
- **dash.** dash, the `/bin/sh` of the agent and proxy images, rejects
  `ulimit -u` (`Illegal option -u`) and names the limit `-p`. The step
  therefore tries `-u`, then `-p`. Measured in dash 0.5.12, Bash and BusyBox:
  both limits are set, and a value above the hard limit fails.
- **Created commands.** A container created with `--init` reports
  `/run/podman-init` and `--` before its command in `.Path` and `.Args`.
  `[{{json .Path}},{{json .Args}}]` and an image's `.Config.Entrypoint` print
  identically through Podman 4.3.1 and 6.2.0 clients.
- **The proxy program.** The network suite's provider fixture derives its proxy
  image with an entrypoint of its own. With the proxy program fixed in the step,
  the two provider tests that reach the fixture's upstream failed with
  `dns-failure`, so the step executes the proxy image's own entrypoint and
  default command, read from the image.

Runner modes from a Claude session on the Windows Podman machine, through its
engine: Podman server 6.2.0, `cgroupfs` manager, kernel
`6.18.58.1-microsoft-standard-WSL2`. The session ran on the Claude adoption of
`sandbox-ref-33`. Same runner as `sandbox-ref-31`.

| Mode | Result |
| --- | --- |
| unit discovery | Passed: 567 tests, 81 skipped |
| runtime (default mode) | Passed: 19 tests, 1 skipped (`SessionEngineTests`: an engine cannot start inside a session's engine) |
| `--setup` | Passed: 93 tests |
| `--qualification` | Passed: 34 tests, 1 skipped |
| `--wrapper` | Passed: 117 tests, 1 skipped |
| `--network-feasibility`, `--network-policy`, `--mux` | Passed: 1, 15 and 26 tests |
| `--network` | 19 tests, 3 skipped. Only the 5 subtests below fail, all needing cgroup limits |
| `--guard` | 25 tests, 1 skipped. The AF_VSOCK control and the 3 multiplex tests with explicit `--memory` limits failed, as before |
| `--setup-runtime` | Unavailable from a session: the offline case stops at the engine qualification (nested engine) |
| `tools/shellcheck.sh .`, `tools/powershell.sh .` | Passed: no finding, 62 shim cases |

Independence cases (design D4), run with this tag and with `main` before the
change (`7e7c5d6`), in the same engine:

| Case | Before the change | This tag |
| --- | --- | --- |
| A session with a budget of 128 beside a container holding 151 processes | Does not start: `crun: clone: Resource temporarily unavailable` | Starts 100 processes, then stops at 125 of 200 |
| A provider session beside the same container | The proxy does not start: the same error | The proxy starts, passes its effective check and serves the session |
| An engine session beside a container holding 521 processes | Unavailable from a session (nested engine) | Unavailable from a session (nested engine) |

No case in any mode failed with `Resource temporarily unavailable`. The
`crun: fork` failure recorded in "Suites from a session with its engine" below
is consistent with the shared ceiling. The remaining `--network` failures need
a cgroup manager:
- `test_agent_budgets_are_effective_and_lifetime_is_enforced`, both subtests:
  no `memory.max`;
- `test_proxy_budgets_at_maximum_streams_and_slow_inspection`: no
  `memory.current`;
- `test_proxy_resource_exhaustion_is_bounded_and_fails_closed`, memory: no
  memory limit, so the allocation runs until the 15-second timeout;
- the same test, processes: the test forks in a `podman exec` process, which
  now gets the engine's default limits (the documented exception). Before the
  change that process got the proxy's `--ulimit`, and the test then required
  `pids.events`, which exists only with the `pids` controller.

Shared files changed since `sandbox-ref-33`: `launcher/core.sh`,
`launcher/engine/entrypoint.sh` (the engine image changes), `network/session.py`,
`network/proxy_hardening.py`, `network/agent_budgets.py`, and comments in
`network/qualification_probe.py` and `setup/smoke.py`. All but `setup/smoke.py`
are in `SHARED_CODE`, so installations requalify. Shared
tests: `tests/fake_podman.py`, `tests/test_launcher.py`, `tests/test_session.py`
and `tests/test_engine.py`. Per-wrapper tests: `tests/test_runtime.py` and
`tests/test_network_runtime.py`.

## Process rlimit counted across containers (`set-process-limits-inside-containers`, task 1.1): 2026-11-24

Measured from a Claude session on the Windows Podman machine, through the
session's engine: Podman server 6.2.0, `cgroupfs` manager, kernel
`6.18.58.1-microsoft-standard-WSL2`. The test containers ran nested and rootless
in that engine, with `--userns=keep-id`, `--network=none` and the pinned alpine
image. Each scenario ran beside a crowd container holding 80 sleeping processes
plus its shell, 81 in all.

| Scenario | Result |
| --- | --- |
| New container with `--ulimit nproc=40:40`, beside the crowd | Does not start: `crun: clone: Resource temporarily unavailable` |
| New container with `--ulimit nproc=200:200`, beside the crowd | Starts |
| `--ulimit nproc=40:40` after the crowd is removed | Starts |
| Running container with `--ulimit nproc=100:100` that starts 60 background processes once the crowd runs | The first fork fails with `can't fork` |
| The same container alone | 60 started, 61 processes |
| `ulimit -u 100` run inside the container beside the crowd, 60 requested | 60 started, 61 processes; limit 100/100; raising the hard limit to 200 fails |
| The same, 150 requested | Stops at 99 processes |

The kernel rule behind this (design "Context"): a new user namespace records
its creator's `RLIMIT_NPROC`. A fork inside it is checked against the
process's own limit at the namespace's level, and against the recorded limit
one level up, where every container of the user counts. crun applies
`--ulimit` before it creates the container's namespace, so that limit becomes
a ceiling shared by every container of the user. A limit set later by a
process in the namespace only bounds the container and its descendants.

This explains the four failures of the Claude adoption's Windows validation of
`sandbox-ref-33` on the same machine. The operator's Claude session, its
engine and the validation's own sessions were running:
- "Drive path with spaces" and "Redirected input": the session did not start,
  with `crun: clone: Resource temporarily unavailable`;
- "Qualification": the proxy did not start, with the same error;
- "Sibling without worktree scope": `cannot verify effective proxy hardening`.
  The check runs `podman exec` in the proxy, and the exec process gets the
  proxy's `--ulimit nproc=128`.

The `sandbox-ref-26` record below measured independent limits with `--ulimit`
on kernel `6.6.87.2-microsoft-standard-WSL2`: two sessions reached 489 and 497
processes under 512, and two containers 49 each under 64. The machine's WSL
kernel has since moved to 6.18.58.1, where the limit is shared. Which kernel
change caused this was not determined. A limit set inside the container does
not depend on the value recorded when its namespace is created.

## Suites from a session with its engine (tasks 7.1 and 8.1): 2026-11-24

The suites ran from a restricted Claude session on the Windows Podman machine,
through that session's own engine. That session was started by `claude-container`
on its adoption branch of `sandbox-ref-31`. The library held two image
toolchains:
- the pinned registry images of the tests: alpine, node, python, ShellCheck and
  the engine base;
- the local runtime, guard toolchain and PowerShell tool images of both
  wrappers, copied by image ID.

The engine images were left out on purpose; see the nested engines below.
`tests/run-runtime.sh` ran unchanged: it found
`CONTAINER_HOST=tcp://127.0.0.1:2375` and copied the checkout, which is mode
777 on `C:`, into a native volume. The unit discovery ran in the runtime image
in the same engine, on a native copy.

| Mode | Result |
| --- | --- |
| unit discovery | Passed: 559 tests, 78 skipped |
| runtime (default mode) | Passed: 18 tests; `SessionEngineTests` skipped, no engine image in the library |
| `--setup` | Passed: 93 tests |
| `--wrapper` | Passed: 114 tests, 1 skipped |
| `--qualification` | Passed: 34 tests, 1 skipped |
| `--network-feasibility`, `--network-policy`, `--mux` | Passed: 1, 15 and 26 tests |
| `--network` | 18 tests, 3 skipped (the two engine cases and the opt-in examples). Only the 5 budget subtests that fail under `cgroupfs` on this machine |
| `--guard` | 25 tests, 1 skipped. The AF_VSOCK control and the 3 multiplex tests with explicit `--memory` limits failed, as in the spike |
| `--setup-runtime` | 2 tests; the offline setup failed at qualification: `the qualification container engine did not answer as a rootless engine` |
| `tools/shellcheck.sh .`, `tools/powershell.sh .` | Passed: no finding, 62 shim cases |

**Nested engines.** An engine started inside a session's engine exits with
`newuidmap: write to uid_map failed: Operation not permitted` for
`0 1000 1 1 1 999 1000 1001 64535`. The engine user's subordinate ranges reach
ID 65535, but a container of the session's engine has 65535 IDs, 0 to 65534.
The qualification probe of a setup run inside a session starts such an engine,
and so does every engine test. These ran against a host engine for
`sandbox-ref-31` (record above). Sizing the engine user's ranges to the IDs the
engine receives would lift this; it is left to a separate change.

**Process budget.** Under `cgroupfs`, the engine's process budget falls back to
the process rlimit (512 tasks), which counts every process in the engine and
its containers. In the Claude network suite one test failed with
`crun: fork: Resource temporarily unavailable` and passed alone. A session
started for heavy suites can raise `<P>_PIDS_LIMIT`.

## Reference tag `sandbox-ref-33`: 2026-11-24

Fix to the interface checks of restricted sessions, found by the Claude
adoption of `sandbox-ref-32`. The operator's library now held image toolchains,
so the setup smoke session had an engine. On the Windows Podman machine, setup
stopped at `assert os.listdir('/sys/class/net') == ['lo']`, after the
qualification had passed.

Measured in a Claude provider session with its engine, on the same machine:
- `/sys` is the host's sysfs (superblock `0:24`), bind-mounted read-only with
  its submounts (`tracefs`, `debugfs`, `configfs`, `fusectl`);
- `/sys/class/net` lists the host's `eth0` to `eth8`, `loopback0` and `lo`,
  with their MAC addresses, link state and counters;
- `/proc/net/dev` lists only `lo`;
- `debugfs` and `tracefs` give `Permission denied`, `configfs` is empty, and
  Podman's masks of `/sys/firmware` and `/sys/fs/selinux` apply.

Rootless Podman bind-mounts its own `/sys` into a container that joins another
container's network namespace. Through this session's engine, a container
joining another's namespace got the engine's sysfs (`0:184`), with only its own
user namespace or with the other container's as well. The owner of the
namespace got a sysfs of its own (`0:205`). The spike's nested engines therefore
showed only loopback, and design D1 could not see the difference before a
setup on a real host.

The operator accepted the read-only host view, now documented in the README's
engine section and in design D1. The setup smoke check, the qualification probe
and the offline default test read `/proc/net/dev`, and the offline engine test
checks that it lists only loopback (task 4.7). `tests/network_fixture.py` is
unchanged: its probes run in containers that own their network namespace.

Shared files changed since `sandbox-ref-32`: `network/qualification_probe.py`
and `setup/smoke.py`, both in `SHARED_CODE`. Per-wrapper file:
`tests/test_network_runtime.py`. Same runner as `sandbox-ref-32`.

| Mode | Result |
| --- | --- |
| `--shared` (unit discovery) | Passed: 560 tests, 78 skipped |
| `--setup` | Passed: 93 tests |
| `--qualification` | Passed: 34 tests, 1 skipped (no authentication method in the profile) |
| runtime (default mode) | Passed: 18 tests. `SessionEngineTests` skipped: an engine cannot start inside a session's engine |
| `--network -k test_offline_defaults_and_leftover_delegation_refusal -k test_offline_session_engine_has_no_external_path` | Passed: 2 tests. The engine test skipped for the same reason |
| `--setup-runtime` | Unavailable from a session: the offline case stops at the engine qualification (nested engine), before the smoke check |
| ShellCheck | Passed |

The new smoke check runs for real in the adoption's setup on the Windows
machine.

## Reference tag `sandbox-ref-32`: 2026-11-24

Fix to how shared code reads engine labels, found by the Claude adoption's
Windows validation of `sandbox-ref-31`. The machine's Podman client is 6.x,
and a session engine was running during the validation. "Image toolchain
removed" failed with `Cannot list the running container engines: … executing
"ps" at <index .Labels "sandbox-engine.store">: error calling index: cannot
index slice/array with type string`. The launcher's reconciliation of engines
left by interrupted launches used the same template and failed silently, so it
removed nothing.

Measured through this session's engine (server 6.2.0), with a labelled running
container:

| Template | 4.3.1 client | 6.2.0 client |
| --- | --- | --- |
| `ps --format '{{index .Labels "…"}}'` | works | fails: `.Labels` is a string |
| `ps --format '{{.Label "…"}}'` | fails: no field `Label` | works |
| `ps --format json` | works: `Labels` is an object | works: `Labels` is an object |
| `container inspect --format '{{index .Config.Labels "…"}}'` | works | works |
| `image inspect --format '{{index .Labels "…"}}'` | works | works |

`setup/toolchains.py` now reads the engine listing as JSON, and
`launcher/core.sh` lists engine IDs and reads each owner with `container
inspect`. The fakes in `tests/test_toolchains.py` and `tests/fake_podman.py`
refuse `.Labels` in `ps` templates, as Podman 6.2 does. A new case covers the
JSON listing, including unreadable output (design D8, task 3.9). No other
template in shared code indexes `ps` labels.

Shared files changed since `sandbox-ref-31`: `launcher/core.sh`,
`setup/toolchains.py`, `tests/fake_podman.py` and `tests/test_toolchains.py`.
Both code files are in `SHARED_CODE`. The suites ran from a Claude session
through its engine, as in the section on suites from a session.

| Mode | Result |
| --- | --- |
| `--shared` (unit discovery) | Passed: 560 tests, 78 skipped |
| `--setup` | Passed: 93 tests |
| `--qualification` | Passed: 34 tests, 1 skipped (no authentication method in the profile) |
| runtime (default mode) | Passed: 18 tests. `SessionEngineTests` skipped: an engine cannot start inside a session's engine |
| `--setup-runtime` | Unavailable from a session: the offline case stops at the engine qualification (nested engine), as before this change |
| ShellCheck | Passed |

The adoption's Windows validation reruns setup and the toolchain cases on the
machine, with its Podman 6 client.

## Reference tag `sandbox-ref-31`: 2026-11-24

Fix to the engine image's base pin, found while the operator added an image
toolchain for the Claude adoption. A clean pull of the pinned
`quay.io/podman/stable@sha256:3e54de04…` failed with `manifest unknown`.
quay.io rebuilds the `podman/stable` tags daily: the copy the pin came from was
built on 2026-11-23 at 03:33, and `v6.2` pointed to a build of 2026-11-24 at
03:39. The earlier manifest was deleted. Installations that already had the
base built the engine; a new installation could not.

The project publishes `-immutable` tags that are never rebuilt. The engine now
builds `FROM quay.io/podman/stable:v6.2.0-immutable@sha256:e0da0a3a…`, the
multi-architecture index; its amd64 manifest is `sha256:39a21e78…`, built on
2026-11-18. It has Podman 6.2.0, crun 1.31, fuse-overlayfs 1.17 and the same
subordinate ranges as the measured base. It also has the files the recipe
removes or empties, and the `/var/lib/shared` additional image store in
`storage.rootless.conf.d/20-image_build.conf`. `tests/test_engine.py` refuses
a base without an `-immutable` tag (design D3, task 2.6).

Shared files changed since `sandbox-ref-30`: `launcher/engine/Containerfile`
and `tests/test_engine.py`. The engine files are in `SHARED_CODE`, so
`--qualification` ran. The operator pulled the base by its index digest into
the spike engine's storage, with the spike's subordinate ranges, and the engine
image was rebuilt from the new recipe. A first attempt pulled it into the spike's
shared store with the image's own ranges: files owned by `podman` appeared as
UID 1 in the engine, and every engine test failed on `stat /home/podman/.config`.
That was the test setup, not the base. Same runner as the `sandbox-ref-29`
record below.

| Mode | Result |
| --- | --- |
| `--shared` (unit discovery) | Passed: 559 tests, 78 skipped |
| `--qualification` | Passed: 34 tests, 1 skipped (no authentication method in the profile) |
| `--setup-runtime` | Passed: 2 tests in 210 s; setup built the engine image from the pinned base |
| runtime (default mode) | Passed: 21 tests, including the three `SessionEngineTests` |
| `--network -k test_offline_session_engine_has_no_external_path -k test_image_recipe_check_runs_without_network` | Passed: 2 tests |

## Reference tag `sandbox-ref-30`: 2026-11-24

Fix to the session container engine, found while preparing the Claude adoption
of `sandbox-ref-29`. In an engine started with the documented options, image
operations that extract layers failed:
- a build with a `RUN` step failed with `error in copier subprocess: chrooting
  to directory "…/merged": operation not permitted`;
- a load of layers the engine did not have failed with `unpacking failed …
  chroot ".": operation not permitted`.

Running containers from library images worked, which is all the spike had
measured. Podman re-executes itself in its rootless user namespace, where the
container's bounding set (`SETUID`, `SETGID`) caps its capabilities, so
`chroot` was denied. With `SYS_CHROOT` added, both operations succeeded in the
same engine; `--isolation=oci` builds failed the same way without it. The
engine options now add `SYS_CHROOT` (design D4, task 2.5 of
`replace-podman-delegation-with-session-engine`). The qualification probe
expects the bounding set `0x400c0`. `SessionEngineTests` builds an image with a
`RUN` step in a session, removes it and loads it back.

Shared files changed since `sandbox-ref-29`: `setup/engine.py`,
`network/qualify.py`, and the shared tests `test_engine.py`,
`test_launcher.py` and `test_qualification.py`. The engine files are in
`SHARED_CODE`, so `--qualification` ran. Same runner as the `sandbox-ref-29`
record below.

| Mode | Result |
| --- | --- |
| `--shared` (unit discovery) | Passed: 559 tests, 78 skipped |
| `--setup` | Passed: 93 tests |
| `--setup-runtime` | Passed: 2 tests in 124 s |
| `--qualification` | Passed: 34 tests, 1 skipped (no authentication method in the profile) |
| `--wrapper` | Passed: 114 tests, 1 skipped |
| runtime (default mode) | Passed: 21 tests, including the three `SessionEngineTests` |
| `--network -k test_offline_session_engine_has_no_external_path -k test_image_recipe_check_runs_without_network` | Passed: 2 tests |

**Engines nested in a session's engine.** An engine container started inside an
engine, as the engine tests would do when run from a session, did not start:
`crun: mkdir /home/podman/.local: Permission denied`. The engine user's
subordinate ranges (1-999 and 1001-65535) also give a nested engine only 65535
IDs, one fewer than its own ranges need. The engine tests
(`SessionEngineTests`, the `session-engine` qualification case and the two
network engine cases) therefore run against a host engine; from a session they
skip when the library holds no engine image. Not changed by this tag.

## Reference tag `sandbox-ref-29`: 2026-11-24

Container tests through a private session engine instead of host Podman
delegation. The tag holds these changes, recorded in the two sections below:
- `simplify-toolchain-provisioning` (archived);
- `replace-podman-delegation-with-session-engine` (active until its native
  Linux check, task 8.2, and its archive).

Shared files changed since `sandbox-ref-28`:
- `launcher/core.sh`, `launcher/windows/bootstrap.sh`,
  `launcher/windows/core.ps1` and the new `launcher/engine/` files;
- `network/agent_profile.py`, `network/qualification_records.py` and
  `network/qualify.py`;
- `setup/common.py`, `setup/launch.py`, `setup/setup.py`,
  `setup/toolchains.py`, the new `setup/engine.py` and
  `setup/toolchain-catalog/`;
- the shared tests `fake_podman.py`, `test_alignment.py`, `test_engine.py`
  (new), `test_launcher.py`, `test_qualification.py`, `test_setup.py`,
  `test_toolchains.py`, `test_windows_bootstrap.py` and
  `tests/windows/shim_tests.ps1`.

**Runner modes on the final tree.** Every mode that `docs/propagation.md`
requires for these files ran, `--wrapper` because `network/agent_profile.py`
changed, `--qualification` because `launcher/core.sh`, `setup/engine.py` and
the engine files are in `SHARED_CODE`. The runner was the spike engine of the
session container engine change: Podman 6.2.0 (`quay.io/podman/stable`),
rootless with the `cgroupfs` manager, nested in a restricted session on the
Windows Podman machine (Podman 6.1.4, WSL kernel 6.18.58.1). Tests ran from a
native copy of the checkout, with the runtime image
`localhost/sandbox-container:setup-fc9eba86d7d7406ea869cc7f2e60fe7c` through
`SANDBOX_CONTAINER_IMAGE`.

| Mode | Result |
| --- | --- |
| `--shared` (unit discovery, with `test_agent_profile.py` and `test_alignment.py`) | Passed: 559 tests, 78 skipped |
| `--setup` | Passed: 93 tests |
| `--setup-runtime` | Passed: 2 tests in 179 s |
| `--qualification` | Passed: 34 tests, 1 skipped (no authentication method in the profile) |
| `--wrapper` | Passed: 114 tests, 1 skipped |
| runtime (default mode) | Passed: 21 tests |
| `--network-feasibility`, `--network-policy`, `--mux` | Passed: 1, 15 and 26 tests |
| `--network` | 18 tests, 1 skipped. Only the 5 budget subtests that fail under `cgroupfs` on this machine, as for `simplify-toolchain-provisioning`. Two more failed under load in the full run and passed alone |
| `--guard` | 25 tests, 1 skipped. The AF_VSOCK control failed, as on this machine. The 3 multiplex tests that request explicit `--memory` limits failed because the nested engine has no writable cgroup (session engine, design Open Questions) |
| `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .`, `git diff --check`, `openspec validate --strict` | Passed: no finding, 62 shim cases |
| `tools/windows-validate.ps1 -SavedDelegation`, Windows PowerShell 5.1, offline setup of this tree | 53 passed, 0 failed, 4 skipped |

The `--network` and `--guard` failures come from the runner, not from the
change: a `cgroupfs` engine applies no cgroup limits, and these tests passed
with the `systemd` manager for `sandbox-ref-27`. A native Linux host with
`systemd` (task 8.2) has not run them on this tree.

## Session container engine (`sandbox-ref-29`): 2026-11-23 to 2026-11-24

Change: `openspec/changes/replace-podman-delegation-with-session-engine/`.
Sessions get a private nested Podman engine instead of host Podman delegation.

**Spike.** A nested engine was measured beside the restricted session
`yarilc-github-0` on the Windows Podman machine. That machine runs Podman
6.1.4, the WSL kernel `6.18.58.1-microsoft-standard-WSL2` and the `cgroupfs`
manager. The engine was `quay.io/podman/stable` (Podman 6.2.0, crun 1.31,
fuse-overlayfs 1.17), joined to the session's network namespace. Each
configuration problem found, and its fix:

| Finding | Fix (design D3/D4) |
| --- | --- |
| Zombie `fuse-overlayfs` and `conmon` children of the API service exhausted `RLIMIT_NPROC`; the proxy failed with `crun: clone: Resource temporarily unavailable` | `--init` |
| `containers.rootless.conf.d/20-image_build.conf` adds `volumes = ["/proc:/proc"]`: nested containers saw the engine's procfs (same superblock, 493 processes) | file deleted; nested PID 1 is the container's own |
| `containers.conf.d/00-vendor.conf` selects journald: `podman logs` was empty | file deleted; `k8s-file` |
| `mounts.conf` passes `/run/secrets/rhsm` through, which the guard's mount check refused | empty `mounts.conf` |
| The default seccomp profile allows `sethostname` only with `CAP_SYS_ADMIN`: private UTS failed (`crun: sethostname: Operation not permitted`) | profile derived from the default with both hostname calls allowed; nested host name is the container ID |
| `cgroups="disabled"` in the base configuration: `cannot set limits without cgroups` | the engine's own `containers.conf` |

A read-only additional image store, written by a helper container of the same
image, served images offline. Both the index and the platform digest resolved,
and an image added while the API service was running was listed and ran
without a restart. The engine refused to remove store images
(`cannot remove read-only image`). A tag copied the record into session storage
with its original names.

All suites ran from the session through the engine, with `tests/run-runtime.sh`
unchanged on a native copy of the checkout:

| Suite | Result |
| --- | --- |
| unit discovery (531 tests) | passed, except the `test_term_forwarding` race (2 of 8 isolated runs), since fixed (task 7.2) |
| runtime (19), `--setup` (92), `--setup-runtime` (2), `--wrapper` (117), `--qualification` (31), `--network-feasibility` (1), `--network-policy` (15), `--mux` (26), `tools/shellcheck.sh`, `tools/powershell.sh` (62 cases) | passed |
| `--network` (16) | 5 budget subtests failed, as on the machine itself under `cgroupfs` |
| `--guard` (25) | the AF_VSOCK control failed, as on the machine; 3 multiplex tests that request explicit `--memory` limits failed: the nested engine has no writable cgroup |

**Session topology (task 1.1).** The network runtime suite ran with every
restricted session joined to the network namespace of a separate
`--network=none` container (`--network=container:<owner>`), including the
qualification probe and the provider harness. Only the 5 cgroupfs budget
subtests failed, as in the baseline. Readiness, hardening identity, the guard,
TLS binding, proxy death, the tampered bootstrap and qualification all passed.
`/etc/resolv.conf` and the interfaces (`lo` only) were identical.

`/etc/hosts` differed in one line: a joined container gets no
`127.0.0.1 <short ID> <name>` entry, and Podman refuses `--add-host` in that
mode. A read-only `/etc/hosts` written by the launcher (localhost entries and
that line) restored resolution of the session's host name. Design D1 therefore
keeps the engine as the network namespace owner, and adds that hosts file.

**Engine capabilities (task 2.3).** The engine image ran inside the spike
engine, with the options of design D4. The spike engine's subordinate range had
to grow from 64535 to 200000 IDs, because nested containers of a nested engine
need a full 65536-ID range; on a host, the caller's own subordinate range
provides it. Each case ran one nested container from the probe root file system:

| Engine capabilities | Nested container |
| --- | --- |
| engine defaults | ran; private procfs (4 processes), own host name |
| `--cap-drop=all --cap-add=SETUID,SETGID` | ran; nested `uid_map` `0 1000 1; 1 1 999; 1000 1001 64535` |
| `--cap-drop=all` | `newuidmap: write to uid_map failed: Operation not permitted` |
| `--cap-drop=all --cap-add=SETUID` or `SETGID` alone | refused the same way |
| `--cap-drop=all --cap-add=SETUID,SETGID --security-opt=no-new-privileges` | ran with the same full map |

With no-new-privileges, the engine's API service processes had
`CapEff`, `CapAmb` and `CapBnd` equal to `0xc0` (`cap_setgid,cap_setuid`) and
`NoNewPrivs: 1`: Podman passes added capabilities to the non-root `podman` user
as ambient capabilities, so `newuidmap` and `newgidmap` need no file
capabilities. The engine therefore keeps no-new-privileges on.

**Engine user namespace (task 2.3).** With the default user namespace, the
engine's `podman` user is a subordinate ID: a nested container's root could not
write a directory owned by the caller (`touch: cannot touch '/work/...':
Permission denied`). A mapping that makes the engine's `podman` user the caller,
`--uidmap 0:100000:1 --uidmap 1:1:999 --uidmap 1000:0:1 --uidmap 1001:1001:65535`
and the same for groups, let the nested root write there, and the file belonged
to the caller (`1000:1000` in the caller's view), with no-new-privileges and with
or without file capabilities on `newuidmap`. That mapping is what
`--userns=keep-id:uid=1000,gid=1000` produces from a contiguous subordinate
range. In the spike engine, whose range was split at its own UID, keep-id split
the engine's IDs 0-999 across two parent extents, and `newuidmap` failed for
`1 1 999` only: each mapped range must lie in one parent extent.
After the spike engine was recreated with one contiguous subordinate range
(`podman:1001:300000`, uid map `[{0 1000 1} {1 1001 300000}]`), the engine image
with `--userns=keep-id:uid=1000,gid=1000`, `--cap-drop=all --cap-add=SETUID,SETGID`
and no-new-privileges ran a nested container whose root wrote into a
caller-owned `0755` directory; the file belonged to the caller (`1000:1000`).

**Rollback compatibility (task 3.7).** The previous release (`e371296`, exported
with `git archive`) read a library written by this change: an image-only
toolchain `db` whose manifest and index entry carry the new `images` field, and
an `.images` store directory. Its `--container-toolchain list` exited 0 and
listed `db 16 default=no` with the catalog recipes; its `launch-env` exited 0 and
printed only the `library` line. The index schema stayed 1, so a rollback keeps
the library readable; the previous release ignores the images.

**Image removal while in use (task 3.6).** An engine ran a nested container
(`sleep 300`) from an image of its read-only store; a store helper then removed
that image (`rmi -f`, `Deleted: bf8527eb54c3…`). The engine no longer listed it,
and the running container broke: `sh` and `/bin/busybox` were not found by a
new `exec`, and the engine could neither inspect nor remove the container
(`image not known`) until the engine itself was removed. A new container from
that image failed with a registry lookup. Deleting a store image while any
session engine runs is therefore refused (design D8); nothing relaxes that rule.

**Implementation suites (tasks 6.4, 8.4): 2026-11-24.** The implementation ran
in the spike engine, from a native copy of the checkout, with the same
`tests/run-runtime.sh` modes. It has not yet run in a session engine started by
the launcher (task 8.1).

| Suite | Result |
| --- | --- |
| unit discovery (559 tests, 78 skipped without an engine), `openspec validate --strict`, ShellCheck (13 files), PSScriptAnalyzer and shim tests (62 cases), `git diff --check` | passed |
| runtime (21, including the 3 session engine cases), `--setup` (93), `--setup-runtime` (2), `--wrapper` (114), `--qualification` (34, including `session-engine`), `--network-feasibility` (1), `--network-policy` (15), `--mux` (26) | passed |
| `--network` (18, including the offline engine and the image recipe check without network) | the 5 cgroupfs budget subtests failed, as in the baseline. Two further tests failed under load; they passed when rerun alone |
| `--guard` (25) | the AF_VSOCK control and the 3 multiplex tests with explicit `--memory` limits failed, as in the spike |

**Windows (task 8.3): 2026-11-24.** After an offline setup of this change from
Windows, `tools/windows-validate.ps1 -SavedDelegation` ran on Windows
PowerShell 5.1.26100.9711. The machine was `podman-machine-default` (WSL
3.0.5.0, kernel 6.18.58.1), with Ubuntu also running. Result: 53 passed,
0 failed, 4 skipped. The skipped cases were the unrestricted-only refusal, the
worktree scope, `-Install` and `-StopMachine`. The cases of this change:

| Case | Result |
| --- | --- |
| Delegation requested (`SANDBOX_CONTAINER_PODMAN=1`) | status 1 with the removal message and image toolchain guidance |
| Image toolchain: a digest-pinned alpine recipe added to a validation library | pulled into the image store |
| Session with library images: an offline session with that library | `CONTAINER_HOST=tcp://127.0.0.1:2375`; the image ran without a pull, and its container reached no external address |
| Image toolchain removed after the session | `Removed toolchain validate-image` |
| Saved delegation: the release's preferences rewritten as schema 2 with `podman` set | the launch stopped with the bootstrap's refusal before any Podman command |
| Setup rerun over saved delegation, from Windows | status 0; the new release saved schema 3 preferences without the setting, and a launch then succeeded |

The other cases passed as in earlier rounds; under `cgroupfs` the launches
announced the agent memory budget as not enforced.

## Toolchain provisioning (`sandbox-ref-29`): 2026-11-23

Change: `openspec/changes/simplify-toolchain-provisioning/`, on the branch of
the same name.
- `--container-toolchain add` pulls pinned images and downloads pinned
  archives without maintenance consent.
- Recipes gain schema 2 with several sources, and a catalog in
  `setup/toolchain-catalog/` adds them by name.
- An operator recipe inside a writable mount is refused.
- Windows drive paths are translated from `/proc/self/mountinfo`.
- The managed launcher keeps host commands first with a saved worktree scope.
- Setup re-verifies the toolchains after it selects a new release.

Shared files changed since `sandbox-ref-28`:
- `setup/toolchains.py`, `setup/launch.py`, `setup/setup.py`, `setup/common.py`
  and the new `setup/toolchain-catalog/`;
- `launcher/core.sh`;
- `tests/test_toolchains.py`, `tests/test_setup.py` and
  `tests/test_launcher.py`.

`setup/toolchains.py` and `launcher/core.sh` are in `SHARED_CODE`, so
`--qualification` ran too.

Runner:
- **Host:** Windows host, WSL 3.0.5.0, kernel 6.18.58.1. Podman machine
  `podman-machine-default`: Fedora Linux 44, Podman server 6.1.4, rootless,
  `cgroupfs` manager. Python 3.14.8 in the machine.
- **Images:** runtime `localhost/sandbox-container:setup-2ab24eec57c9464383114a90d9ecafc7`
  through `SANDBOX_CONTAINER_IMAGE`. Guard toolchain `dde2fe627a7b…`, tagged
  `localhost/sandbox-container-guard-toolchain:development` for the runner,
  because `tests/run-runtime.sh` forwards `SANDBOX_GUARD_TOOLCHAIN` only in
  `--guard` mode.
- **Network:** the network inspects TLS. Its CA is imported into the machine
  (`podman machine set --import-native-ca`), and setup saved host CA trust.
- **Unit tests:** they ran on a copy of the checkout on the machine's ext4
  (`~/sbx-check`, `SANDBOX_TEST_TMPDIR=~/sbx-tmp`). The checkout on `C:` is
  drvfs with mode 777, and the development session (an agent sandbox) has no
  executable native storage with protected ancestors.

| Check | Result |
| --- | --- |
| `tests/test_setup.py` and `tests/test_launcher.py` after the worktree fix | Passed: 200 tests, including `test_saved_worktree_scope_leaves_host_commands_first` |
| `tests/test_toolchains.py` (final) | Passed: 55 tests, 4 skipped. The skipped download tests need the `openssl` CLI, which the machine lacks. They passed in the development session with a local HTTPS server and a private CA; only the library ancestor check was relaxed there |
| `--shared` (unit discovery) | 531 tests, 77 skipped, 3 failures not caused by the change (see below) |
| `--setup` | Passed: 92 tests |
| `--setup-runtime` | Passed: 2 tests in 83 s |
| `--qualification` | Passed: 31 tests, 1 skipped (no authentication method in the profile) |
| `--network` | 16 tests, 1 skipped (the opt-in examples). Only the budget failures recorded for this machine under `cgroupfs` (Windows restricted networking, 2026-11-21): agent budgets (2 subtests), proxy budgets at maximum streams, proxy exhaustion (`pids` failure, `memory` error). `test_toolchain_added_during_offline_session_without_network` passed |
| `SANDBOX_TOOLCHAIN_EXAMPLES=1 bash tests/run-runtime.sh --network -k documented_toolchain` | Unavailable on this network. `java21`, `maven3.9` and `go` were added by name; the `node24` download failed with `CERTIFICATE_VERIFY_FAILED`, because the test container trusts only the image's bundle and the runner passes no host CA. An earlier run stalled 900 s in `add go` while the image was missing. The cause was not isolated: the same pull through the image's Podman 4.3.1 client against the machine's Podman 6.1.4 service took 34 s alone, and `add go` with the remote client in the machine took 40 s |
| The same steps by hand in the machine, in a scratch library | `node24` downloaded with the machine's system trust. With host CA trust and the saved bundle, `node24`, `python3.13` and `rust` were installed; `rust` has 5 sources from 4 archives, each downloaded once. An offline session started by the installed release (the previous code) on that library compiled a new crate with `cargo build --offline` for `x86_64-unknown-linux-musl` and printed `Hello, world!`. `node --version` gave the image's v22, and `env.sh` gave v24.22.3 |
| README "Managing the library" commands, as written | Passed: `add java21`, `add ~/recipes/x.json`, `list` (installed, then catalog), `remove java21`, `verify`, `verify rust`. A recipe copied into the current directory was refused |
| `tools/windows-validate.ps1`, Windows PowerShell 5.1, setup with the worktree scope | First run: 42 passed, 4 failed. "Recipe path from PowerShell" failed: `wslpath` failed for every drive path once the command ran through the entry, after `enter.sh`, while it worked from a shell in the machine. Translation now reads `mountinfo` (design D7). The three other failures were cases that assume no saved scope. After the fix, with the script skipping those three cases when setup saved the scope: 43 passed, 0 failed, 6 skipped |
| Sessions through the Windows entry, worktree scope saved | `java21` and `go` added by name to the real library; an offline session printed `openjdk version "21.0.13"` and `go version go1.27.4` |
| Sessions through the managed command in the machine shell, same setup | `--container-toolchain list` worked with the saved worktree scope; an offline session printed the same versions |
| `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .`, `git diff --check` | Passed: no finding, 62 shim cases |

The three unit-discovery failures:
- **`test_repository_text_files_have_no_carriage_return`** found the PowerShell
  summary of `windows-validate.ps1` (CRLF), copied into the checkout for this
  record. It moved to `.test-state/`, and `tests/test_alignment.py` then
  passed (21 tests).
- **`test_managed_rerun_reviews_saved_defaults_without_inheriting_launch_values`**
  also fails on `main`. It finds setup's probe of the machine's real Podman
  socket in `/run/user/1000`; the change does not touch that part of setup.
- **`test_interrupted_start_group_is_terminated_and_stop_recovers_ownership`**
  races between `exists()` and `read_text()` on `/proc/<pid>/stat`. It failed
  5 of 5 times on the branch and 1 of 3 on `main`. Neither `network/` nor the
  test is changed.

Not run: `tools/windows-validate.ps1` on PowerShell 7, `-Install` and
`-StopMachine`, and a native Linux host (the Linux steps ran in the machine
shell). Not changed: the pull in `add` has no timeout, and the Windows entry
forwards no explicit HTTP proxy (README, Toolchains on Windows).

## `windows-validate.ps1` with an agent wrapper (no tag): 2026-11-22

The Claude adoption of `sandbox-ref-28` ran `tools/windows-validate.ps1
-Checkout C:\Work\claude-container` on Windows (`claude-container`,
`docs/validation.md`). Two cases failed in both editions because of the
script, not of the sandbox:

- **Redirected input** runs the entry through `cmd.exe`, not through `& $E`,
  so it lacked `--container-shell`. Its `-c` reached Claude, which answered the
  input as a prompt.
- **Offline session** assumed that an offline launch works after setup.
  Qualification reports are stored per identity, which includes the network
  mode. A setup that saved provider networking qualifies provider only, so the
  launcher asked to rerun `--container-qualify`, as it does on Linux.

The script now passes `--container-shell` in the `cmd.exe` case for an agent
profile. When setup saved provider networking, it runs an "Offline
qualification" case (`<P>_NETWORK=offline --container-qualify`) before the
offline session. `tools/` is never copied, so no tag is needed.

| Check | Result |
| --- | --- |
| Dry run with the fixture agent profile and a fake `wsl.exe` that reports provider networking | "Offline qualification" ran `--container-qualify` with `FIXTURE_AGENT_NETWORK=offline` before the offline session, which started with `--container-shell`. A fake `cmd.exe` recorded `... fixture-agent.ps1 --container-shell -c od -An -tx1 < ...` |
| `bash tools/powershell.sh .` | Passed: no finding, 62 shim cases |
| Operator rerun on Windows with `C:\Work\claude-container` (Claude saved provider networking) | 43 passed, 0 failed, 3 skipped on Windows PowerShell 5.1 and on PowerShell 7. "Offline qualification", "Offline session" and "Redirected input" passed |

## Windows guidance for agent wrappers (`sandbox-ref-28`): 2026-11-22

Change: `openspec/changes/archive/2026-11-22-fix-windows-agent-guidance/`. Planning the Claude
adoption found three gaps that only an agent wrapper shows:

- **Setup authentication steps.** Started by the Windows entry, setup now
  names the steps for PowerShell. A postponed login is `<name>.ps1` with the
  login arguments, quoted for PowerShell. The API method names
  `$env:<KEY> = '...'` before `<name>.ps1`. Linux output is unchanged.
- **`tools/windows-validate.ps1`.** For a profile whose command is not
  `bash`, the command cases run with `--container-shell`. Before, `-c` would
  have reached the agent.
- **`tools/propagate.py`.** It recognizes a runner mode tested as
  `== --mode ||`. Claude's `--guard` was missing from the dry run.

Shared files changed since `sandbox-ref-27`: `setup/setup.py` and
`tests/test_setup.py`. Neither is in `SHARED_CODE`, so `--qualification` is
not required. Same runner as the `sandbox-ref-27` record below.

| Check | Result |
| --- | --- |
| `--shared` (unit discovery) | 498 tests, 74 skipped. The 14 `AF_UNIX path too long` environment failures as before. `test_ignored_signals_force_owned_removal` (`INT`) failed again on timing, as recorded for `sandbox-ref-27`. `test_shared_components_contain_no_sibling_identifiers` found `--claudeai` in the new PowerShell quoting case; the case now uses a neutral value, and the alignment, setup and propagation suites pass (119 tests) |
| `--setup` | Passed: 88 tests, including `test_windows_entry_names_the_powershell_authentication_steps` and `test_powershell_words_are_quoted_only_when_needed`, which fail without the change |
| `--setup-runtime` | Passed: 2 tests in 155 s |
| `tests/test_propagate.py` | Passed: 10 tests, including `test_runner_modes_in_if_conditions`, which fails without the change. With Claude's runner, the checklist for `network/guard.c`, `setup/setup.py` and `network/qualification_records.py` lists `--setup`, `--setup-runtime`, `--qualification`, `--guard` and `--network`. The full dry run to `claude-container` ran in that adoption's first task, after its change directory was committed |
| `tools/windows-validate.ps1` dry run (fake `wsl.exe` that decodes the first argument) | With the fixture agent profile, all 12 launches start with `--container-shell`, and the by-hand line names `fixture-agent.ps1 --container-shell -c 'stty size'`. With the reference profile, none does. Same 13 passed, 17 failed, 9 skipped as before, the failures expected from the fake |
| `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .`, `git diff --check` | Passed: no finding, 62 shim cases |

The runtime image was `localhost/sandbox-container:setup-c496ace9b5e94548b7f86f4a0bcbd8bc`,
through `SANDBOX_CONTAINER_IMAGE`, as for `sandbox-ref-27`. The reference
profile has no authentication method, so its Windows run cannot show the new
steps. The Claude adoption checks them on Windows.

## Reference tag `sandbox-ref-27`: 2026-11-22

Windows support on a Podman machine (WSL provider). The tag holds these
changes, recorded in the sections below:
- `support-windows-podman-machine`;
- `add-windows-installer`;
- `clean-up-setup-output-and-tags`;
- `support-machine-restricted-networking`;
- `validate-windows-remaining-cases`;
- `close-windows-pre-tag-gaps`.

Shared files changed since `sandbox-ref-26`:
- `launcher/core.sh` and the new `launcher/windows/` files;
- `network/guard.c` and `network/README.md`;
- `setup/common.py`, `setup/launch.py` and `setup/setup.py`;
- the shared tests `test_alignment.py`, `test_guard.py`, `test_launcher.py`,
  `test_setup.py`, `test_windows_bootstrap.py` and `test_windows_enter.py`,
  and `tests/windows/shim_tests.ps1`.

**Runner modes on the final tree.** Every mode that `docs/propagation.md`
requires for these files ran on 2026-11-21 and 2026-11-22. `--qualification`
is required because `launcher/core.sh` is in `SHARED_CODE`. The runner was
WSL2 x86_64 `6.18.58.1-microsoft-standard-WSL2`, with Podman client 4.3.1,
server 4.9.3, the `systemd` cgroup manager and controllers `[cpu memory pids]`.
The runtime image was `localhost/sandbox-container:setup-c496ace9b5e94548b7f86f4a0bcbd8bc`,
passed as `SANDBOX_CONTAINER_IMAGE`: its `build-inputs-hash` `b50c3422...`
matches the current inputs, and the engine had no `latest` tag left.

| Mode | Result |
| --- | --- |
| `--shared` (unit discovery, with `test_agent_profile.py` and `test_alignment.py`) | 495 tests, 74 skipped; only the 14 `AF_UNIX path too long` environment failures (13 in `test_session.py`, 1 in `test_launcher.py`) |
| `--setup` | Passed: 86 tests |
| `--setup-runtime` | Passed: 2 tests in 151 s |
| `--qualification` | Passed: 31 tests in 164 s, 1 skipped (no authentication method in the checkout profile) |
| `--guard` | Passed: 25 tests in 123 s, 1 skipped (`--guard-idle`) |
| `--network` | Passed: 16 tests in 312 s, 1 skipped (toolchain examples) |
| `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .`, `git diff --check` | Passed: no finding, 62 shim cases |

**On Windows** (Podman machine `podman-machine-default`, WSL 3.0.5.0, kernel
6.18.58.1-1, Landlock ABI 7), `tools/windows-validate.ps1` passed in Windows
PowerShell 5.1 and PowerShell 7, including `-Install` and `-StopMachine`. It
passed in offline and unrestricted modes, with the `default` and `local`
endpoints. The sections below record each run and the restricted runner modes
in the machine.

## Windows pre-tag gaps (`sandbox-ref-27`): 2026-11-21

Change: `openspec/changes/archive/2026-11-21-close-windows-pre-tag-gaps/`.

**Antivirus (operator report, 2026-11-21).** The problem appears only with
Bitdefender (Advanced Threat Control, `Atc4.Detection`). It affects only the
validation scripts (`tools/windows-validate.ps1` and the throwaway operator
scripts) and the extraction of validation bundles with `tar`. Setup and the
installer do not trigger it. On another Windows system with other antivirus
products the operator saw no problem. It is documented in the README's
Windows limits and in the header of `tools/windows-validate.ps1`; nothing in
the code works around it.

**Checks on this runner (task 3.1), 2026-11-21.** Same runner as below:

| Check | Result |
| --- | --- |
| `git diff --check`, `bash tools/shellcheck.sh .` | Passed |
| `bash tools/powershell.sh .` | Passed: no finding, 62 shim cases, including the new credential-variable case (forwarded when set, not when unset or empty, none for a profile without methods, named in the help) |
| `--shared` (unit discovery), with `tests/test_alignment.py` | 495 tests, 74 skipped; only the 14 `AF_UNIX path too long` environment failures (13 in `test_session.py`, 1 in `test_launcher.py`) |

**Operator run on Windows (task 4.2), 2026-11-21.** Snapshot of the branch
tree with this change. Windows WSL 3.0.5.0, kernel 6.18.58.1-1, Windows
PowerShell 5.1.26100.9711; the machine `podman-machine-default` with Ubuntu
running. The steps of design D2:

| Step | Result |
| --- | --- |
| 1. Setup from Windows, unrestricted, endpoint answered `local`; then `windows-validate.ps1` | 41 passed, 0 failed, 3 skipped. "One engine for sessions and the machine" passed: the service ran a command in the session's container and removed it. The unprepared restricted mode named `sandbox-container.ps1 --container-setup from Windows` |
| 2. Setup in a shell opened with `wsl -d podman-machine-default`; then `windows-validate.ps1` | The shell entered the machine's systemd namespaces (the machine's notice "You will be automatically entered into a nested process namespace", `/proc/1/comm` `systemd`, `XDG_RUNTIME_DIR=/run/user/1000`). Run from the home directory, setup stopped with `Managed installation/command overlaps a writable workspace or state mount`, because the home contains `~/.local/lib/sandbox-container`; Linux behaves the same. Run again from `/mnt/c/Work/sandbox-container`, with the proposed answers (unrestricted, endpoint `local`, host CA trust with `/etc/ssl/certs/ca-certificates.crt`), it ended with `Sandbox: ready`. The validation then gave 41 passed, 0 failed, 3 skipped, with "One engine" passing |
| 3. Setup from Windows, offline | The endpoint question proposed `[default]` over the saved `local`. `sandbox-container.ps1 -c 'echo ok'` from a project folder printed `ok`, with `network mode=offline`, `status=locally-qualified`, Landlock ABI 7 and `sandbox-egress-guard: enforced revision=abi3-seccomp-mux-v1 abi=7` |

Every step passed, so nothing changes (design D2). The `local` endpoint works
from Windows, and a shell of the machine runs setup inside its systemd
namespaces. The "One engine" failure of the earlier run stays tied to the
release that run started from, whose settings are not known.


## Windows remaining cases (`sandbox-ref-27`): 2026-11-21

Change: `openspec/changes/archive/2026-11-21-validate-windows-remaining-cases/`. From the Windows
entry, the launcher's "setup required" refusals now name
`<name>.ps1 --container-setup from Windows`.

**Host CA trust with the Podman machine (operator report, 2026-11-21).** On a
network with TLS inspection, the operator verified setup with host CA trust on
`podman-machine-default`, keeping the default bundle that setup proposed. The
machine trusts the Windows CAs only after `podman machine set
--import-native-ca`, which fails while the machine runs; without it, the
sandbox's configuration does not get the interception CA. `README.md` and
`docs/setup.md` now give the steps (task 1.4).

**Checks on this runner (task 2.1), 2026-11-21.** Same runner as the guard
init checks below:

| Check | Result |
| --- | --- |
| `git diff --check`, `bash tools/shellcheck.sh .` | Passed |
| `bash tools/powershell.sh .` | Passed: no finding, 61 shim cases |
| `tools/windows-validate.ps1` dry run with a fake `wsl.exe` (PowerShell 7) | Completed; the unprepared restricted-mode case now expects the Windows step |
| `--shared` (unit discovery) | 495 tests, 74 skipped. The 14 `AF_UNIX path too long` environment failures as before (13 in `test_session.py`, 1 in `test_launcher.py`). `test_fixture_identifiers_stay_in_the_fixtures` found the fixture name in the new provider case, which now reads it from the profile; the alignment suite and the case pass. `test_ignored_signals_force_owned_removal` (`INT`) ended in 2.9 s instead of more than 3.5 s; on the branch head it failed in 2 of 4 runs, so it is a timing flake of this runner, not a new failure |
| New cases | `test_setup_guidance_from_the_windows_entry_names_the_windows_step` and `test_provider_setup_guidance_from_the_windows_entry` pass, with the 5 existing setup-guidance cases |

**Operator run on Windows (task 3.2), 2026-11-21.** Snapshot of the branch
tree with this change. Windows WSL 3.0.5.0, kernel 6.18.58.1-1 (WSL and the
kernel were updated since the previous runs); the Podman Desktop machine
`podman-machine-default`, user `user`, with Ubuntu running. The summary files
were copied after each run.

| Run | Release in the machine | Summary |
| --- | --- | --- |
| `windows-validate.ps1 -Install -StopMachine`, Windows PowerShell 5.1.26100.9711 | The release of a setup run earlier from a Linux shell in the machine, saved with unrestricted networking (its endpoint is not known); the installer's setup replaced it with offline networking | 51 passed, 2 failed, 1 skipped |
| `windows-validate.ps1 -Install -StopMachine`, PowerShell 7.7.0 | This change, offline | 54 passed, 0 failed, 1 skipped |
| Setup with unrestricted networking and the `default` endpoint, then `windows-validate.ps1`, 5.1 | This change, unrestricted | 41 passed, 0 failed, 3 skipped |
| Setup with offline networking, then `windows-validate.ps1` as a control run, 5.1 | This change, offline | 42 passed, 0 failed, 3 skipped |

- Installer, both editions: install from the checkout and setup from the
  installed copy through the namespace helper, the user `PATH` in the registry
  and in a new window, the refusal of an install from the installed copy, and
  the uninstall of the `PATH` entry and of the folder passed.
- Stopped machine, both editions: the launch refusal, the help, the machine
  staying stopped, the launch and setup refusals of a distribution that
  `wsl.exe` alone started, and the restart with `podman machine start` passed.
- Unprepared restricted mode, with this change's release: `setup required:
  offline sessions need a protected installation; run sandbox-container.ps1
  --container-setup from Windows, or set SANDBOX_CONTAINER_NETWORK=unrestricted
  for a direct session`.
- The two failures of the first 5.1 run came from the earlier release, because
  the matrix runs before the installer's setup:
  - the unprepared restricted mode printed the Linux step of the earlier
    launcher (`run bash /home/user/.local/lib/sandbox-container/releases/<id>/sandbox-container.sh
    --container-setup and use the managed launcher`);
  - "One engine for sessions and the machine": the service listed the
    session's container, but `exec` failed with `crun: container ... does
    not exist: open /run/user/1000/crun/<id>/status`, and the session did not
    end within 60 s. The helper was the same in both releases. That release
    came from a setup in a Linux shell of the machine, whose way into the
    machine and endpoint are not known. With this change's release the case
    passed in offline mode on both editions and in unrestricted mode on 5.1.
- The final offline setup proposed the `default` endpoint, which the
  unrestricted setup had saved. The replacement of a saved `local` endpoint
  did not run on Windows; `test_restricted_mode_proposes_a_service_endpoint_over_a_saved_local_engine`
  covers it.
- After the final offline setup, `sandbox-container.ps1 -c 'echo ok'` from a
  project folder printed `ok`.

## Windows restricted networking (`sandbox-ref-27`): 2026-11-21

Change: `openspec/changes/archive/2026-11-21-support-machine-restricted-networking/`. The operator
ran four rounds of throwaway spike scripts, not committed, on 2026-11-21:

- Windows with WSL kernel `6.6.87.2-microsoft-standard-WSL2`;
- the Podman Desktop machine `podman-machine-default`: Podman 6.1.4, Fedora
  Linux 44, user `user` (uid 1000), the `cgroupfs` manager;
- `podman machine inspect`: `Rootful: false`, `UserModeNetworking: false`.

The scripts ran from a `C:\Work` folder, and the suites ran from a snapshot
of the branch tree copied to the distribution's ext4 file system.

**Machine structure (rounds 2 and 3).**

- PID 1 of a `wsl.exe --exec` session is WSL's `/init`. Podman started
  `unshare --kill-child --fork --pid --mount --mount-proc --propagation shared
  /lib/systemd/systemd`, so systemd is PID 1 of child PID and mount
  namespaces (`NSpid: 21 1`).
- The user's `systemd --user`, `dbus-broker`, `podman.socket` and the
  service's `catatonit` run there.
- `/etc/profile.d/enterns.sh` and `/usr/local/bin/enterns` take login shells
  in with `sudo nsenter -m -p -t <systemd>` and `sudo -u $USER`. `user` has
  passwordless `sudo` (`(ALL) NOPASSWD: ALL`).
- `/usr/share/containers/containers.conf.d/999-podman-machine-wsl-cgroupfs.conf`
  sets `cgroup_manager="cgroupfs"`.

**Inventory from a `wsl.exe --exec` session (rounds 1 and 2).** Round 1 mixed
Podman's warnings into the values it parsed, and its restart check compared
the kernel boot id, which WSL distributions share. Round 2 is the reference.

| Check | Result |
| --- | --- |
| A1 `/run/user/1000` | `drwx------ user:user`; `bus` socket present; linger `yes` |
| A1 `systemctl --user show-environment` | Failed: `Transport endpoint is not connected` |
| A1 `/run/user/1000/podman/podman.sock` | Socket, `srw-rw---- user:user`; API answers: `true linux true`, server 6.1.4, Netavark, `cgroupfs v2 [cpu io memory pids]`, crun |
| A1 setup probe (`launch_service`) with `XDG_RUNTIME_DIR=/run/user/1000` | `True`: the default endpoint answers; user manager `False` |
| A1 setup probe with `XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir` | `False`: no socket there, no user manager |
| A1 after `wsl --terminate` and `podman machine start` | Socket and API present again; the init's start time changed |
| A2 binds through the service | Passed for `/mnt/c/Work/...`, `/home/user` and `/run/user/1000`: the container read the host's file and the host read the container's |
| A2 container started by the service, used by the session's podman | Inspect and removal worked. Exec failed (`crun: the container ... is not running`), after `Failed to join existing conmon namespace, creating a new rootless podman user namespace` |
| A2 `pause.pid` | Each side replaced the other's on every command: `pause.pid file refers to PID 272 which is not a pause process`. The service's `catatonit` runs in another PID, mount and user namespace |
| A3 `platform_check` | Eligible: `{"arch": "x86_64", "backend": "netavark", "kernel": "6.6.87.2-microsoft-standard-WSL2", "seccomp": true, "selinux": false, "apparmor": false, "server": "6.1.4"}` |
| A3 Landlock | ABI 3 (`landlock_create_ruleset` version query) |
| A6 | Service rootless; no `/run/podman/podman.sock` |

**Way into systemd's namespaces (round 3).** A prototype helper ran a command
as the user in systemd's PID and mount namespaces, in two variants:

- `nsenter`: `sudo -n nsenter --target <pid> --mount --pid --wd=<cwd>
  --setuid 1000 --setgid 1000`;
- `sudo`: the same `nsenter`, then `sudo -n -u user`, as `enterns`.

The environment went through a mode-0600 file under `/run/user/1000`, which
the inner part read and removed.

| Check | `nsenter` | `sudo` |
| --- | --- | --- |
| PID 1 inside; identity | `systemd`; uid and gid 1000, groups `user` only | `systemd`; uid and gid 1000, groups `user wheel` |
| `HOME`, `USER`, `LOGNAME`, `PATH`, `TERM`, `LANG`; directory | Kept | Kept |
| A 40000-character `WSLENV` variable with quotes, `\`, `è` and `€` | Same bytes | Same bytes |
| `XDG_RUNTIME_DIR` | `/run/user/1000` | `/run/user/1000` |
| Exit status 37, piped stdin, separate stderr | Passed | Passed |
| Terminal | A new pseudo-terminal (`use_pty`) | A new pseudo-terminal |
| Time per command | 223 ms | 327 ms |
| One rootless user namespace: `pause.pid` stable (`catatonit`), no warning | Passed | Passed |
| `systemctl --user show-environment` | Works | Works |
| Session's podman runs a command in, and removes, the service's container | Passed | Passed |
| Environment files left | None | None |
| Ctrl+C during `sandbox-container -c 'sleep 60'` (installed, unrestricted) | Status 2; container `test-prk-0` left in `Created` | Status 130; nothing left |
| Window closed during the same session | A `conmon` process left, without a container | Nothing left |

Inside the namespaces through the `nsenter` way, the round 2 inventory passed
completely, before and after a restart:

- user manager `running`;
- setup probe `True` with the user manager `True`;
- one `pause.pid`;
- the session's podman ran a command in the service's container and removed
  it.

The `sudo` way became the design (D2).

**Runner modes inside the namespaces (rounds 3 and 4).** These used the
`sudo` way in round 4, the toolchain built in the machine (`7ea67bad7f58`),
the runtime image `a5048f924d32` and the pinned Python base of the proxy
image, which round 3 lacked.

| Mode | Result |
| --- | --- |
| `--setup-runtime` | Passed: 2 tests in 78 s (fresh offline setup, unrestricted setup and shell) |
| `--qualification` | Passed: 31 tests in 65 s, 1 skipped (no authentication method in the profile) |
| `--guard` | 20 tests in 126 s, 1 skipped (`--guard-idle`). 1 failure, `test_existing_late_sockets_and_aliases_across_bind_roots`, in its unguarded control: `socket(AF_VSOCK)` gives `Operation not permitted` |
| `--network` | 16 tests in 216 s, 1 skipped (toolchain examples). Offline and provider sessions, TLS binding, readiness, tampered bootstrap, proxy death, the Windows workspace and toolchain cases passed. The failures are listed below |

The `--network` failures:

- `test_agent_budgets_are_effective_and_lifetime_is_enforced`, both subtests:
  - the launch notices stated that the memory and CPU budgets are not
    enforced under `cgroupfs`, and the process budget uses the process
    rlimit;
  - the test then read `memory.max`, which is `max` there.
- `test_proxy_budgets_at_maximum_streams_and_slow_inspection` read
  `memory.max` too.
- `test_proxy_resource_exhaustion_is_bounded_and_fails_closed`:
  - the `pids` case reached the rlimit (`pids-budget-enforced`), then read
    `pids.events`, which counts 0 without the controller;
  - the `memory` case grew until the 15 s timeout, because the memory budget
    is not enforced.

The AF_VSOCK control (round 4) points at the machine's seccomp profile, not at
the kernel:

| Probe | Result |
| --- | --- |
| Rootless container, default profile | `PermissionError: [Errno 1] Operation not permitted` |
| The same, `--security-opt seccomp=unconfined` | Created |
| The distribution itself | Created |
| `/usr/share/containers/seccomp.json` | One rule on socket family 40 |

These failures are the engine limits recorded since `sandbox-ref-26` and in
the phase 1 section below. The tests assume delegated cgroup controllers and an
unguarded AF_VSOCK. The launcher's notices and qualification identity state
the `cgroupfs` mechanisms; nothing was weakened, and the tests are unchanged.

**Integration checks (task 5.3).** On the runner of the sections below
(Podman client 4.3.1, server 4.9.3, `systemd` manager), on top of commit
`fa520b7`, with the runtime image `localhost/sandbox-container:setup-c496ace9…`:

| Check | Result |
| --- | --- |
| `git diff --check`, `bash tools/shellcheck.sh .` | Passed |
| ShellCheck 0.11.0 on the new `launcher/windows/enter.sh` (not tracked yet) and `launcher/windows/bootstrap.sh` | Passed |
| `bash tools/powershell.sh .` | Passed: no finding, 61 shim cases |
| `--shared` (unit discovery) | 487 tests, 69 skipped; only the 14 `AF_UNIX path too long` environment failures (13 in `test_session.py`, 1 in `test_launcher.py`) |
| `--setup` | Passed: 85 tests |
| `--setup-runtime` | Passed: 2 tests in 140 s |

The unit discovery includes `tests/test_windows_enter.py` (9 tests) and
`tests/test_windows_bootstrap.py` (9 tests). A dry run of
`tools/windows-validate.ps1` in the PowerShell 7 image, against a fake
`wsl.exe` that answers every probe with success and prints nothing, completed
and wrote its summary.

**Operator run with the namespace helper (task 7.1, first round).** Windows
PowerShell 5.1.26100.9818 and PowerShell 7.7.0, WSL 2.5.10.0, the machine
started by Podman, no other distribution running.

- An offline setup from Windows ended with `Sandbox qualification:
  locally-qualified` and `Sandbox: ready`. Setup proposed the saved endpoint
  `local` after the choice of offline networking and refused it once; task 6.2
  changes that default.
- `tools/windows-validate.ps1` passed in both editions: 41 passed, 0 failed,
  4 skipped (no other distribution, the unrestricted-only refusal case,
  `-Install`, `-StopMachine`). The new cases passed: an offline session without
  network access (`blocked`), qualification (`locally-qualified`), the
  delegation refusal, and the machine's service running a command in, then
  removing, a session's container.
- By hand, in both editions: `-c 'stty size'` printed `28 110`, as
  `$Host.UI.RawUI.WindowSize`; in an interactive offline shell
  `curl https://example.com` failed to resolve; closing the window left no
  container (`podman ps -a` on Windows). Ctrl+C during `-c 'sleep 60'` did not
  end the command: it ended after 60 s with status 0. The bundle needed the
  antivirus disabled for the validation script.

The runner modes then ran in the machine through the snapshot's own
`launcher/windows/enter.sh`, with the previous guard. The results matched the
spike's round 4:

- `--setup-runtime` passed (2 tests in 74 s), and so did `--qualification`
  (31 tests in 66 s, 1 skipped);
- `--guard` had only the AF_VSOCK control failure, with the same probe
  results;
- `--network` had only the `cgroupfs` budget failures listed in the section
  above.

The interrupt was not lost on the way: on this runner, with plain Podman,
`bash -c 'echo started; sleep 20'` without `--init` ignored Ctrl+C on a
terminal (status 0 after 20 s), and with `--init` ended in 0.3 s with status
130. Restricted containers had no init in front of the application, which ran
as PID 1; task 6.1 makes the confined guard that init.

**Guard init and setup endpoint (task 6.4).** Same runner and image, with the
guard of task 6.1 and the setup change of task 6.2:

| Check | Result |
| --- | --- |
| `git diff --check`, `bash tools/shellcheck.sh .`, ShellCheck on `launcher/windows/enter.sh` | Passed |
| `bash tools/powershell.sh .` | Passed: no finding, 61 shim cases |
| `--shared` (unit discovery) | 493 tests, 74 skipped; only the 14 `AF_UNIX path too long` environment failures |
| `--setup` | Passed: 86 tests, including `test_restricted_mode_proposes_a_service_endpoint_over_a_saved_local_engine`, which fails at once without the change |
| `--setup-runtime` | Passed: 2 tests in 146 s |
| `--guard` | Passed: 25 tests in 116 s, 1 skipped (`--guard-idle`) |
| `--qualification` | Passed: 31 tests in 114 s, 1 skipped (no authentication method in the profile) |
| `--network` | Passed: 16 tests in 300 s, 1 skipped (toolchain examples) |

The new guard cases, through the production guard in a rootless container:

- Ctrl+C on a terminal ends `sh -c 'echo ready; exec sleep 30'` with status
  130 within 10 s;
- an application with a SIGINT handler counts exactly one interrupt;
- `podman kill --signal TERM` ends `sleep` with status 143 within 10 s;
- `sh -c 'sleep 30 & exit 37'` returns 37 without waiting for `sleep`;
- the waiting guard (PID 1) holds only fd 2 and has the application's
  `NoNewPrivs` and seccomp filter count;
- in provider mode it holds no FD 3.

Compiled from the previous `guard.c`, the interrupt case failed (`0 != 130`),
the TERM case timed out, and the waiting-guard case found fds 0 to 3. The
interrupt-count and background cases also pass with the previous guard; they
guard against double delivery and waiting.

**Operator run with the final code (task 7.1).** Same Windows host, the
machine started by Podman, Ubuntu running:

- Setup from Windows proposed `offline` and the endpoint `default` from the
  saved preferences. It recompiled the guard with the toolchain
  `7ea67bad7f58`, and ended with `Sandbox qualification: locally-qualified`
  and `Sandbox: ready`.
- `tools/windows-validate.ps1` passed in both editions: 42 passed, 0 failed,
  3 skipped (the unrestricted-only refusal case, `-Install`, `-StopMachine`).
  This includes another distribution being active, the offline session
  without network access, qualification, and the one-engine check.
- By hand, in both editions, the operator reported every step as passed:
  - Ctrl+C during `-c 'sleep 60'` ended at once with status 130;
  - in an interactive offline shell, `sleep 60` with Ctrl+C returned at once to
    the prompt, and `curl https://example.com` failed;
  - `-c 'stty size'` matched the window;
  - closing the window left no container (`podman ps -a` on Windows).
- The runner modes ran in the machine through the snapshot's
  `launcher/windows/enter.sh`, with the new guard:

  | Mode | Result |
  | --- | --- |
  | `--setup-runtime` | Passed: 2 tests in 89 s |
  | `--qualification` | Passed: 31 tests in 64 s, 1 skipped |
  | `--guard` | 25 tests in 127 s, 1 skipped. The 5 new init cases and the provider descriptor case passed. The only failure is the AF_VSOCK control, with the same probe results as before |
  | `--network` | 16 tests in 237 s, 1 skipped. The only failures are the `cgroupfs` budget cases of the spike: `memory.max` and `pids.events` reads, and the unbounded memory case |

## Setup output and candidate tags (`sandbox-ref-27`): 2026-11-21

Change: `openspec/changes/archive/2026-11-21-clean-up-setup-output-and-tags/`.

**Integration checks (task 4.2).** Same runner and images as the sections
below, on top of commit `1b2d932`:

| Check | Result |
| --- | --- |
| `git diff --check`, `bash tools/shellcheck.sh .` | Passed |
| `bash tools/powershell.sh .` | Passed: no finding, 59 shim cases |
| `--shared` (unit discovery) | 477 tests, 69 skipped; only the 14 `AF_UNIX path too long` environment failures |
| `--setup` | Passed: 85 tests |
| `--setup-runtime` | Passed: 2 tests in 149 s |

**Windows (task 4.1, round 10).** Windows PowerShell 5.1, the machine started
by Podman:

- `.\sandbox-container.ps1 --container-setup` and the setup that
  `--container-install` runs from the installed copy printed no
  `export PATH=` line, no shell startup file and no managed-command line. Both
  printed `Start sessions with the Windows entry from a project directory on a
  Windows drive.`, followed by the entry's own next step. The only
  distribution path left is the default value of the "Managed launch command
  path" question.
- `sandbox-container --container-uninstall` behaved as before.
- A setup interrupted with Ctrl+C during the smoke check reported `Removed the
  tag of the abandoned candidate: localhost/sandbox-container:setup-e7c7e224...`.
  The 18 local `sandbox-container` tags listed before the run were listed
  unchanged after it, and the candidate tag was gone.

## Windows installer (`sandbox-ref-27`): 2026-11-21

Change: `openspec/changes/archive/2026-11-21-add-windows-installer/`.

**Integration checks (task 7.1).** On the runner of task 9.2 in the section below
(Podman client 4.3.1, server 4.9.3, `systemd` manager), on top of commit
`bbbddbb`, with the same runtime image:

| Check | Result |
| --- | --- |
| `git diff --check` | Passed |
| `bash tools/shellcheck.sh .` | Passed |
| `bash tools/powershell.sh .` | Passed: no finding, 54 shim cases (17 for the installer and the user `PATH`) |
| `--shared` (unit discovery) | 473 tests, 69 skipped; only the 14 `AF_UNIX path too long` environment failures, as before this change |
| `--setup` | Passed: 81 tests, including `--manifest` |
| `--setup-runtime` | Passed: 2 tests in 116 s |
| `--qualification` | Passed: 31 tests in 98 s, 1 skipped |

**Windows, round 8 (task 6.2, in progress).** `tools/windows-validate.ps1
-Install` on Windows PowerShell 5.1.26100.9818 and PowerShell 7.7.0, with the
antivirus disabled after it had quarantined, during extraction with `tar`,
`sandbox-container.sh` (as in round 4) and the test helper
`mark-downloaded.ps1`, which writes `Zone.Identifier`: 46 passed, 0 failed,
1 skipped in each edition. The install from the checkout completed. The user
`PATH` kept its existing `String` kind with the other entries unchanged. A
child that read the new `PATH` from the registry ran `sandbox-container`. The
installed copy refused to install itself, and the uninstall restored the
`PATH` exactly.

The uninstall then left the folder, because it still held files that the
installer had not created. Setup runs `python3 -I setup/setup.py` from the
installed copy, and Python caches bytecode in `__pycache__` there. The script
had counted that refusal as a folder in use. The uninstall now also removes
`__pycache__` folders that hold only `.pyc` files, and the script reports a
remaining foreign file as a failure.

With that fix, the operator reran `tools/windows-validate.ps1 -Install` in
both editions: 47 passed, 0 failed, 1 skipped (stopped machine) in each. The new
check "Machine running" passed. The uninstall removed the install folder
(status 0) and restored the user `PATH` exactly.

By hand, in Windows PowerShell 5.1:

- `.\sandbox-container.ps1 --container-install` copied 45 files, announced the
  `PATH` change, ran setup from the installed copy (`Sandbox: ready`) and
  printed the next step.
- From `C:\Work\test-project`, `sandbox-container --container-uninstall`
  removed the `PATH` entry and the folder, and named the machine installation
  that stays.
- Every file of a copy was marked with the Mark of the Web (`ZoneId=3`, 450
  files). `powershell -ExecutionPolicy Bypass -File .\sandbox-container.ps1
  --container-install` installed it. Afterwards `sandbox-container -c 'printf
  ok'` printed `ok` from `C:\Work\test-project` without a policy override, so
  the installed files carry no mark. The uninstall then removed it again.

The antivirus was active during these installs and launches and did not
intervene. New Windows Terminal tabs found the command without a Terminal
restart; the tab that had run the install did not find it at first. The
installer's message and the README now say to open a new window or tab. With
this PC's execution policy, the operator saw no block when starting the marked
copy without `-ExecutionPolicy Bypass`; the effective policy was not
recorded, so the `RemoteSigned` refusal is not reproduced here.

**After the second code review (task 8.4, round 9).** With the antivirus
active during the installs, `tools/windows-validate.ps1 -Install` gave
46 passed, 1 failed, 1 skipped on Windows PowerShell 5.1.26100.9818, then
47 passed, 0 failed, 1 skipped on PowerShell 7.7.0. The failure: the user
`PATH` ended with `;`, so the install appended the folder after it, and the
uninstall removed the entry but not the restored trailing `;`. The other
entries were unchanged. The 7.7 run, made afterwards on a `PATH` without the
trailing `;`, restored it exactly. The install now keeps a trailing `;`
trailing, and a shim case checks that removing the entry restores every tested
value byte for byte. The string rule does not depend on Windows.

Setup run from the installed copy still prints its Linux guidance
(`export PATH=...`, `~/.bashrc`) before the entry's own next step, and every
setup adds a `setup-*` tag to the runtime image (twelve in this round, all on
the same image). Both are left for a later change.

## Windows Podman machine support (`sandbox-ref-27`): 2026-11-20

Change: `openspec/changes/archive/2026-11-20-support-windows-podman-machine/`. Operator runs on
2026-11-19: Windows 10.0.26300.9974, WSL 2.5.10.0 (kernel 6.6.87.2-1,
WSLg 1.0.66), the Podman Desktop machine `podman-machine-default` (Podman
6.1.4, `cgroupfs`, user `user`), with an Ubuntu distribution running. The spike
and repro scripts were throwaway operator scripts built from the branch working
tree; they are not committed.

**PowerShell and `wsl.exe` spike (task 1.2).** Windows PowerShell
5.1.26100.9818 (Desktop) and PowerShell 7.7.0 (Core).

| Check | Windows PowerShell 5.1 | PowerShell 7.7 |
| --- | --- | --- |
| `wsl.exe -l -q` | UTF-16 with NUL characters | the same |
| `wsl.exe -l -q` with `WSL_UTF8=1` | no NUL; distribution found | the same |
| `--cd ~ --exec /bin/bash <home-relative path>` | starts in `/home/user` | fails with 127: PowerShell replaces `~`, also in a splatted array |
| `--exec /bin/sh -c 'cd && exec /bin/bash <home-relative path>'` | starts in `/home/user` | the same |
| `--cd` with a drive path containing spaces | starts in the matching `/mnt/c/...` directory | the same |
| Script `$args` binding | `''`, `"`, `a "b" c\`, `\`, `è` and an emoji kept; bare `--` consumed; `-x:y` split into `-x:` and `y`; `a,b` an `Object[]`; `5` an `Int32` | the same |
| `$MyInvocation.ExpectingInput` | `True` with pipeline input, `False` otherwise | the same |
| Arguments as base64 of NUL-terminated UTF-8 in one variable through `WSLENV` (`/u`) | 9 arguments, bytes unchanged | the same |
| Variable size through `WSLENV` | 30000 and 32766 characters delivered | the same |
| .NET `SetEnvironmentVariable` with 32767 and 32768 characters | both refused | both accepted |
| `wslpath -a -u` in the distribution | `C:\` gives `/mnt/c/`; `Z:\...`, `\\server\share\x` and `\\wsl$\Ubuntu\home` fail with 1; `\\wsl.localhost\podman-machine-default\home` gives `/home` | the same |
| Redirected native stderr under `$ErrorActionPreference = 'Stop'` | terminating `NativeCommandError` | no error |
| `exit 7` in the distribution | `$LASTEXITCODE` 7 | the same |
| Missing user; missing distribution | -1 with `Wsl/WSL_E_USER_NOT_FOUND`; -1 with `Wsl/Service/WSL_E_DISTRO_NOT_FOUND` | the same |
| Missing script | 127 | the same |
| Terminal | no TTY with captured stdout; TTY with inherited handles, `TERM=xterm-256color` | the same |
| Stdin redirected by `cmd /c "... < file"` | bytes unchanged, NUL and CR included | the same |
| Stdin piped by PowerShell (`a`, LF, `è`) | `EF BB BF 61 0A 3F 0D 0A`: byte order mark, `?`, CRLF | `61 0A C3 A8 0D 0A`: CRLF appended |
| Ctrl+C | one SIGINT; `wsl.exe` returns 130; the script continues and `finally` runs | the same |
| Absent variable restored by passing `$null` to `SetEnvironmentVariable` | removed | left defined and empty |
| Window closed | `finally` does not run; the Linux process receives one SIGHUP and keeps running for the 12 s it was given | the same |

**`podman rm` timeout (task 1.3).** Ten unrestricted sessions
(`-c 'sleep 300'`) ran in the machine distribution from a checkout copy on
ext4. Each was interrupted with SIGINT to its process group once its container
ran, under shell job control so that the wrapper's INT trap ran as with Ctrl+C.
Every session ended with status 130 about 2 s after the signal. One interval
was negative because the distribution's clock was adjusted. No container
remained and no log mentioned a timeout, so the timeout does not reproduce and
no follow-up task was added. Each session announced that the memory and CPU
budgets are not enforced under `cgroupfs` and that the process budget uses the
process rlimit (512). An earlier attempt without job control left SIGINT
ignored in the wrapper (status 1); it is not counted.

**Consequences (task 1.4).** The specs and design were updated: the bootstrap
starts through `sh -c 'cd && exec ...'` instead of `--cd ~`; the encoded
arguments are limited to 32766 characters; empty variables count as unset on
both versions; an absent variable is restored with `Remove-Item`; the probes
capture stderr outside `Stop`; closing the window ends the session with the
bounded shutdown; and pipeline input is refused on both versions.

**Setup on the machine (task 8.2, first attempts).** Two failures came before
a completed setup:

- The distribution had been started by `wsl.exe` while Podman Desktop showed
  the machine as stopped. `/run/user/1000` was missing, and every `podman` call
  as `user` failed with status 125 (`creating events dirs: mkdir
  /run/user/1000: permission denied`). The database keeps the run root
  `/run/user/1000/containers`. After `wsl --terminate` and `podman machine
  start`, `podman info` answered `true linux false` in about 2 s.
- The engine checks then passed and the runtime image was built, but the smoke
  check failed with status 125. It ran Podman with an empty `CONTAINER_HOST`,
  which Podman 6.1.4 treats as a remote context. Task 4.5 leaves the variable
  unset for the local endpoint.

With task 4.5, setup completed in rounds 4 and 5 (`Sandbox: ready`, the smoke
check passed, unrestricted, local endpoint), and the entry then printed
`start sessions with .\sandbox-container.ps1 from a project directory`.

**Antivirus.** While the round 4 snapshot was extracted with `tar` on Windows,
the antivirus on the operator's PC quarantined
`tests/fixtures/shell-agent/launcher.sh` as `Atc4.Detection`, a name used by
Bitdefender's Advanced Threat Control. The file holds only variable
assignments and only the Linux tests use it; setup and the Windows entry do
not read it.

**Runtime suite in the machine (task 8.3).** `bash tests/run-runtime.sh` ran
twice, unrestricted, from a checkout copy on the distribution's ext4 file
system, against a foreground API service that the operator script started at
the socket path Podman reports (`/mnt/wslg/runtime-dir/podman/podman.sock`).
Both runs gave the same result: 19 tests in about 140 s, 18 passed.
`test_effective_hardening_and_budgets_in_every_unrestricted_variant` failed:

- Its eight subtests read `/sys/fs/cgroup/memory.max`, which does not exist
  under the `cgroupfs` manager. The launch notices stated, as expected since
  `sandbox-ref-26`, that the memory and CPU budgets are not enforced and that
  the process budget uses the process rlimit.
- Its process-budget check with `PIDS_LIMIT=32` could not start the container
  (`crun: clone: Resource temporarily unavailable`, status 125). Under the
  rlimit fallback, 32 tasks of the session user leave no room for container
  startup.

The test assumes delegated cgroup controllers and does not yet cover an engine
without them.

**Validation script (task 8.2, round 4).** After setup completed, the operator
ran `tools/windows-validate.ps1` from `C:\Work\sandbox-container`, with Ubuntu
running and without `-StopMachine`:

| Edition | Result |
| --- | --- |
| PowerShell 7.7.0 | 38 passed, 0 failed, 1 skipped (stopped machine) |
| Windows PowerShell 5.1.26100.9818 | 37 passed, 1 failed, 1 skipped (stopped machine) |

On Windows PowerShell 5.1, "Redirected input" failed. Started as
`cmd /c "powershell -File <entry> -c od < input.bin"`, the entry saw
`$MyInvocation.ExpectingInput` set and refused the input as pipeline input.
PowerShell 7.7 passes the same case. The spike had checked `ExpectingInput`
only for pipeline input. In the 5.1 summary every refusal showed
`#< CLIXML` instead of its message: children started with `-EncodedCommand`
write CLIXML progress records to stderr. The checks search the whole output,
so the results stand, and the script now leaves that block out of the summary.

By hand, from `C:\Users\yari\test`, in both editions, with
`sandbox-container.ps1 -c 'sleep 60'`:

- Ctrl+C: status 130;
- closing the window: afterwards `podman ps -a` in the distribution listed no
  container.

**Redirected input on Windows PowerShell 5.1 (round 5).** `stdin-check.ps1`
redirected `61 0a c3 a8 0d 0a 00 7a` through `cmd.exe` to a script that ran
`wsl.exe ... od -An -tx1`:

| Started as | `ExpectingInput` | `IsInputRedirected` | Bytes in the distribution |
| --- | --- | --- | --- |
| `powershell.exe -File` | True | True | unchanged |
| `powershell.exe -Command "& <script>"` | False | True | unchanged |
| `pwsh.exe -File` | False | True | unchanged |
| `pwsh.exe -Command "& <script>"` | False | True | unchanged |

Windows PowerShell 5.1 therefore reports the redirected input of a `-File`
script as pipeline input but does not read it. The shim now accepts that case
(design D3), and `tests/windows/shim_tests.ps1` covers it.

**Validation script (task 8.2, round 5).** After a new setup:

| Edition | Result |
| --- | --- |
| PowerShell 7.7.0, `-StopMachine` | 43 passed, 2 failed |
| Windows PowerShell 5.1.26100.9818 | 37 passed, 1 failed (redirected input, fixed since), 1 skipped |

With `-StopMachine`, every refusal passed: a stopped machine (status 1, the
distribution stayed stopped), help with a stopped machine (status 0), and a
distribution started by `wsl.exe` alone, for launch and for setup. The
restart failed: `podman machine start`, run right after `wsl --terminate`,
stopped with `the WSL bootstrap script failed ... exit status 0xffffffff`
(status 125), and the launch after it found the machine stopped. The next
`wsl.exe` call failed with `Wsl/Service/CreateInstance/HCS_E_CONNECTION_TIMEOUT`
until `wsl --shutdown` and `podman machine start`. The script now waits until
WSL no longer lists the distribution as running, plus 5 s, and retries the
start once.

**Validation script (task 8.2, round 6).** Windows PowerShell 5.1.26100.9818
with `-StopMachine`, Ubuntu running: 44 passed, 0 failed, 0 skipped, read from
the console. Redirected input passed (`610ac3a80d0a007a`), and so did every
stopped-machine case and the restart with `podman machine start`. The final
cleanup then failed, because a process kept a folder of the work directory as
its current directory after the restart, so the summary file was not written.
The script now reports such a folder and still writes the summary, and runs
`podman machine start` from the profile directory.

With that script, the operator reran both editions:

| Edition | Result |
| --- | --- |
| Windows PowerShell 5.1.26100.9818, `-StopMachine` | 44 passed, 0 failed, 0 skipped |
| PowerShell 7.7.0 | 38 passed, 0 failed, 1 skipped (stopped machine; its refusals passed on PowerShell 7.7 in round 5) |

Both runs noted that the work directory could not be removed: its
`project with spaces` folder, from which the first session after the restart
ran, stayed in use while WSL ran. A WSL process probably keeps it as its
current directory; `wsl --shutdown` releases it. The README states this limit.

**Shared suites (task 9.1).** The branch working tree and a `git archive main`
copy ran on the same runner (Python 3.11.2, `SANDBOX_TEST_TMPDIR` on native
executable storage, whose long path makes `AF_UNIX` socket paths too long):

| Suite | Branch | `main` |
| --- | --- | --- |
| `test_launcher.py` | 109 tests; 1 environment failure (`AF_UNIX path too long`, provider session) | 107 tests; the same failure |
| `test_wrapper.py` | 6 passed | 6 passed |
| `test_session.py` | 20 tests; 13 environment failures (`AF_UNIX path too long`) | the same 13 |
| `test_setup.py` | 78 passed | 68 passed |
| `test_setup_wrapper.py` | 9 passed | 8 passed |
| `test_qualification.py` | 31 passed, 7 skipped | 1 error (`ProcessLookupError` in `test_bounded_subprocess_group_cleanup`, a cleanup race that passed on the branch) |
| `test_agent_profile.py` | 21 passed, 3 skipped | 21 passed, 3 skipped |
| `test_alignment.py` | 21 passed | 17 passed, 1 skipped |
| `test_windows_bootstrap.py` | 7 passed | absent |

`bash tools/shellcheck.sh` passed on both trees. `bash tools/powershell.sh .`
reported no PSScriptAnalyzer finding and 35 shim cases passed, and
`git diff --check` was clean. The branch adds no failure; the environment
failures are the ones recorded for earlier tags.

**Runner modes (task 9.2).** On the same runner and engine (Podman client
4.3.1, server 4.9.3, `systemd` manager, controllers `[cpu memory pids]`),
with the runtime image whose build-inputs hash `b50c3422…` matches this tree.
The guard toolchain image `localhost/sandbox-container-guard-toolchain:development`
came from the build cache (`101d7cad…`, the image the other wrappers' setups had
built from the same recipe), so nothing was downloaded.

| Mode | Result |
| --- | --- |
| `--shared` (unit discovery) | 469 tests, 69 skipped; the 14 `AF_UNIX path too long` environment failures of task 9.1 (13 in `test_session.py`, 1 in `test_launcher.py`), and the `test_bounded_subprocess_group_cleanup` cleanup race (`/proc/<pid>/stat` gone), which also failed once on `main` in task 9.1 and passed in the branch's own run |
| `--setup` | Passed: 78 tests |
| `--setup-runtime` | Passed: 2 tests in 125 s |
| `--qualification` | Passed: 31 tests in 147 s, 1 skipped (no authentication method in the profile) |
| `--guard` | Passed: 20 tests in 109 s, 1 skipped (`--guard-idle`) |
| `--network` | Passed: 16 tests in 344 s, 1 skipped (toolchain examples) |

**After the code review (task 10.5, local part).** Same runner, engine and
images, after the fixes of tasks 10.1 to 10.4:

| Check | Result |
| --- | --- |
| `bash tools/shellcheck.sh .` | Passed |
| `bash tools/powershell.sh .` | Passed: no finding, 37 shim cases |
| `--shared` (unit discovery) | 472 tests, 69 skipped; only the 14 `AF_UNIX path too long` environment failures |
| `--setup` | Passed: 80 tests |
| `--setup-runtime` | Passed: 2 tests in 132 s |
| `--qualification` | Passed: 31 tests in 108 s, 1 skipped |
| `--guard` | Passed: 20 tests in 112 s, 1 skipped |
| `--network` | Passed: 16 tests in 304 s, 1 skipped |
| `bash tests/run-runtime.sh` | Passed: 19 tests in 254 s |

**After the code review (task 10.5, Windows round 7).** After a new setup, with
Ubuntu running and the work folder next to the checkout
(`C:\Work\sandbox-container-windows-validate`):

| Edition | Result |
| --- | --- |
| Windows PowerShell 5.1.26100.9818, `-StopMachine` | 46 passed, 0 failed, 0 skipped |
| PowerShell 7.7.0 | 40 passed, 0 failed, 1 skipped (stopped machine) |

The new cases refused `Documents` (`/mnt/c/Users/yari/Documents`) and a
folder inside `AppData` (`/mnt/c/Users/yari/AppData/Local`) in both editions.
Redirected input passed in both, and so did every stopped-machine case and the
restart with Podman on 5.1. As in round 6, the project folder of the first
session after the restart stayed in use until WSL stopped, so both runs noted
that the work folder was not removed.

**Runtime budget test that follows the engine (task 8.4).** On this runner
(Podman client 4.3.1, server 4.9.3, `systemd` manager, controllers
`[cpu memory pids]`, kernel `6.18.58.1-microsoft-standard-WSL2`), with the
installed runtime image whose build-inputs hash `b50c3422…` matches this tree,
`bash tests/run-runtime.sh` passed: 19 tests in 229 s. The changed test
takes the delegated branch there. In the machine distribution (round 5,
`cgroupfs`, after a fresh setup), `run-runtime.ps1` ran the suite from an ext4
checkout copy, once started from each PowerShell edition: 19 tests passed in
149 s and in 145 s, so the `cgroupfs` branch with the process rlimit holds too.

## Terminal attach with an engine-forced read-only `/dev`: 2026-11-10

Change: `openspec/changes/allow-terminal-on-read-only-dev/`.

- **Trigger:** on the lab host, the first interactive launch (account login)
  failed with `crun: unlink /dev/console: Read-only file system`. With
  `--read-only --read-only-tmpfs=false`, Podman 5.8 mounts `/dev` read-only,
  and crun 1.27 replaces `/dev/console` to attach a terminal.
  Non-interactive launches and the qualification gate were unaffected.
- **Operator probes on the lab host** (Podman 5.8.0, crun 1.27; TTY start
  with `create -t` then `start --attach`):

| Arguments | TTY start | `/dev` | `/dev/shm` |
| --- | --- | --- | --- |
| `--read-only --read-only-tmpfs=false` (previous) | Failed: unlink `/dev/console` | ro | ro |
| `--read-only` | Started | rw, executable | rw, noexec |
| `=false` plus a user `/dev` tmpfs | Failed: create, no `/dev/pts` | forced ro | ro |
| `--read-only`, user `/dev` tmpfs, no `devpts` | Failed: open `/dev/ptmx` | rw, noexec | ro mask |
| `--read-only`, user `/dev` tmpfs, `devpts`, ro `/dev/shm` (adopted) | Started; `/dev/console` links to `/dev/pts/0` | rw, noexec | ro mask |

- **Change:** agent containers keep automatic provisioning and override each
  of its targets: explicit `/tmp`, `/run` and `/var/tmp`, a
  `rw,nosuid,noexec` `/dev` tmpfs (64 MiB), an explicit `devpts`, and an
  empty read-only `/dev/shm`. The proxy and the qualification gate keep
  `--read-only-tmpfs=false`. On Podman 5, `/dev` is agent-writable but not
  executable.

Measured on WSL2 x86_64, with Podman client 4.3.1, server 4.9.3 and
crun 1.14.1. No credentials or model requests were used.

| Check | Result |
| --- | --- |
| Wrapper `--container-shell` with a TTY (unrestricted, isolated state) | Passed: stdin is `/dev/pts/0`; `/dev` stays `ro,nosuid,noexec` on Podman 4.9; `/dev/shm` is read-only; `/tmp` and `/var/tmp` refuse direct execution |
| `test_wrapper.py`, `test_session.py`, `test_alignment.py` (changed tree versus `HEAD`, same runner) | No new failures; the same environment failures on both. The new test checks the `/dev` layout in offline, provider and unrestricted modes, in shell, worktree and delegated launches and with a TTY, and that the proxy keeps `--read-only-tmpfs=false` |
| `bash tests/run-runtime.sh --qualification` | Passed: 26 tests in 193 s; the gate and proxy containers are unchanged |
| Lab host interactive login after `--container-setup` | Passed (operator, 2026-11-10; Podman 5.8.0, crun 1.27): the login attached a terminal and reported `Login successful`, and setup recorded `Authentication: verified`. The operator then confirmed that Claude Code works in provider mode (operator-reported; no model request was made by the test suites). The only egress diagnostic was one `transport-closed` record with no host, from the session closing |

## Engine default `/run/secrets` mask: 2026-11-10

Change: `openspec/changes/mask-engine-default-run-secrets/`.

- **Trigger:** on the Rocky 9 lab host, `/usr/share/containers/mounts.conf`
  maps `/usr/share/rhel/secrets:/run/secrets`. Every container received a
  writable tmpfs there, and the guard stopped restricted startup with
  "nested private IPC mount validation failed (errno=1)".
- **Operator probe on the lab host:** with
  `--mount type=tmpfs,destination=/run/secrets,ro=true`, Podman skipped its
  default mount. `mountinfo` showed one `/run/secrets ro,... tmpfs`, and the
  directory was empty.
- **Change:**
  - every agent container and provider proxy gets that mask;
  - `guard.c` parses the per-mount options and filesystem type, and admits
    `/run/secrets` only as a read-only tmpfs.

Measured on WSL2 x86_64 (no default secrets mount), with Podman client 4.3.1
and server 4.9.3. No credentials or model requests were used.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --guard` (guard compiled from the changed source) | Passed: 20 tests (1 skipped). The read-only tmpfs mask is accepted, with an empty `/run/secrets`. A writable tmpfs at `/run/secrets`, a read-only host bind at `/run/secrets`, and read-only tmpfs mounts at `/run/other-secrets` and `/tmp/secrets` are rejected before exec. The existing `/tmp/untrusted-nested` rejection still holds |
| `test_wrapper.py`, `test_session.py`, `test_alignment.py` (branch versus `main`, same runner) | No new failures. The new tests check the mask in default, shell, worktree and delegated launches, and in the proxy create |
| `bash tests/run-runtime.sh --qualification` | Passed: 25 tests in 147 s, with the mask present |
| Lab host `--container-setup` (provider, refresh) | Passed (operator, 2026-11-10; Rocky 9, `ipv6.disable=1`, Podman 5.8.0, crun 1.27, Landlock ABI 6): images built, guard compiled, qualification `locally-qualified`, `Sandbox: ready`; the gate containers needed the same mask (`qualify.py`). The first interactive launch then failed on `/dev/console` (see the read-only `/dev` entry) |

## Budgets follow delegated cgroup controllers: 2026-11-09

Change: `openspec/changes/adapt-budgets-to-delegated-controllers/`.

- **Trigger:** on the Rocky 9 lab host, systemd does not delegate the `cpu`
  controller to the user. The qualification agent failed with "crun:
  controller `cpu` is not available under .../user@31600276.service/...".
  The operator decided that the host must not be modified and that the
  sandbox continues automatically.
- **Policy (relaxes the earlier "never remove a budget" rule):**
  - A budget is enforced only when the verified engine's
    `Host.CgroupControllers` lists its controller: `memory`, `cpu` or `pids`
    for the agent, `memory` or `pids` for the provider proxy.
  - Unenforced budgets are not requested (`--pids-limit=-1` overrides a
    `containers.conf` default) and are announced on every launch, in the
    setup plan and in the smoke.
  - Enforced budgets must be exact, and unenforced ones must be absent (no
    configured value, and the cgroup interface missing or `max`).
  - The agent and proxy enforced sets are part of the qualification
    identity.

Measured on WSL2 x86_64 (all three controllers delegated), with Podman client
4.3.1 and server 4.9.3, from an unrestricted session with the host socket
delegated. No credentials or model requests were used.

| Check | Result |
| --- | --- |
| `test_wrapper.py` (branch versus `main`, same runner) | 73 versus 70 tests; identical environment failure set. The new controller-subset test passed: flags, notices, `--pids-limit=-1`, ignored delegated limits, unexpected unenforced limits, malformed lists and query failure |
| `test_session.py` | Passed: 17 tests, including proxy flags and notices per controller subset and exact per-budget hardening verification |
| `test_qualification.py` | Passed: 25 tests, including enforced-set parsing, identity staleness on enforced-set change, fixed-input validation and probe checks for each subset |
| `test_setup.py` | 66 tests; the same 2 environment errors as `main`; new smoke-budget and setup-plan notice tests passed |
| `test_network_policy.py`, `test_alignment.py`, `test_image_pins.py`, `test_tls_proxy.py` | Passed |
| `bash tests/run-runtime.sh --qualification` (all controllers delegated) | Passed: 25 tests in 166 s, including 7 real qualification gates; no budget notice printed |
| Lab host without `cpu` delegation: `--container-setup` (provider, refresh) | Passed (operator, 2026-11-10; Rocky 9, `ipv6.disable=1`, Podman 5.8.0, crun 1.27, Landlock ABI 6): images built, guard compiled, qualification `locally-qualified`, `Sandbox: ready`; the CPU-budget notice was printed |

Existing qualification reports become stale (new identity fields).
Restricted installations rerun `--container-setup`.

## Qualification on kernels without IPv6: 2026-11-09

Change: `openspec/changes/qualify-ipv6-disabled-kernels/`.

- **Trigger:** the Rocky 9 lab host (kernel 5.14.0-687.12.1.el9_8 booted with
  `ipv6.disable=1`, Landlock ABI 6, Podman 5.8) built every image and the
  guard. Qualification then failed at `network create --internal --ipv6`:
  "netavark: set sysctl net/ipv6/conf/podman1/forwarding: No such file or
  directory". The kernel setting cannot be changed on that host.
- **Behavior:**
  - The identity probe on the engine host records `security.ipv6` as
    `present` or `absent`. **absent** means no `/proc/sys/net/ipv6` and
    `EAFNOSUPPORT` on `AF_INET6`; anything else is unverifiable. The state is
    bound into the report.
  - When IPv6 is absent, the fixture network and peer are IPv4-only, the
    fixed input carries `ipv6: false` with one IPv4 address, and the control
    and guarded probes require `EAFNOSUPPORT` for `AF_INET6`.
  - Contradictory fixture evidence fails the gate.
  - The provider proxy skips upstream addresses whose family the kernel
    lacks.

Measured on WSL2 x86_64 (IPv6 present, TLS-intercepted network), with Podman
client 4.3.1 and server 4.9.3 (rootless, Netavark), from an unrestricted
session with the host socket delegated. No credentials or model requests were
used.

| Check | Result |
| --- | --- |
| `test_qualification.py` (contracts) | Passed: 24 tests (6 new: IPv6 state detection, identity binding and staleness, fixtures for both states including contradictions, fixed input shapes, probe and runtime kernel-rejection evidence) |
| `test_network_policy.py` | Passed: 15 tests; the new family fall-through test fails on the unpatched proxy with `EAFNOSUPPORT` |
| `test_tls_proxy.py`, `test_alignment.py`, `test_image_pins.py` | Passed: 12, 9 and 5 tests |
| `test_session.py`, `test_setup.py`, `test_wrapper.py` (branch versus `main`, same runner) | No new failures; the same environment failures on both (7, 2 and 22) |
| `bash tests/run-runtime.sh --qualification` (IPv6 present) | Passed: 24 tests in 150 s, including 7 real qualification gates through the dual-stack path, with toolchain `localhost/claude-guard-toolchain:development` (`b00a8c07fd15`, built with the `build-ca` secret) |
| Lab host without IPv6: `--container-setup` (provider, refresh) | Passed (operator, 2026-11-10; Rocky 9, `ipv6.disable=1`, Podman 5.8.0, crun 1.27, Landlock ABI 6): images built, guard compiled, qualification `locally-qualified`, `Sandbox: ready` through the IPv4-only gate |

Existing qualification reports become stale (new identity field and code
digests), and the proxy image changes. Rerun `--container-setup` with
refresh on restricted installations.

## HTTPS package sources and host-CA build trust: 2026-11-09

Change: `openspec/changes/https-image-package-sources/`.

- **Recipe:** the runtime `Containerfile` rewrites the Debian deb822 sources
  to `https://deb.debian.org` before `apt-get update`. Fetches are verified
  against a temporary bundle built from the pinned base's Node.js roots, plus
  the optional `build-ca` build secret. The bundle is removed in the same
  step. Pins are unchanged: Claude Code 2.1.316, OpenSpec 1.16.0, and base
  `node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da`.
- **Host CA trust:** when it is enabled, setup (runtime and guard toolchain
  builds, never the proxy build) and the wrapper's `--container-build` and
  missing-image builds pass the selected bundle as
  `--secret id=build-ca,src=<bundle>`. The toolchain's `apk` verifies against
  Alpine's roots plus the secret. Both `.containerignore` files admit
  `podman-build-secret*`, because remote Podman clients ship secrets inside
  the build context under that name.
- **Motivation:** an operator Linux host (Podman 5.8) blocked outbound port
  80, so the build timed out on `http://deb.debian.org`, while HTTPS to
  Debian and npm returned 200. The maintainer's WSL host intercepts HTTPS to
  `deb.debian.org` (`CN = Cato Networks Root CA`), so Node's roots alone fail
  there.

Measured on WSL2 x86_64 with Podman client 4.3.1 and server 4.9.3 (rootless),
from an unrestricted session with the host socket delegated. No credentials or
model requests were used.

| Check | Result |
| --- | --- |
| `test_image_pins.py` | Passed: 4 tests, including 11 mutated transport and secret recipes rejected |
| Build without secret, initial recipe (TLS-intercepted host) | Failed closed, as expected: `Certificate verification failed … issuer is unknown`; no image tagged |
| Build with `build-ca` secret through the remote client, before the `.containerignore` exception | Failed: `rename … podman-build-secret… no such file or directory`; fixed by admitting `podman-build-secret*` |
| Build with `build-ca` secret (test tag `localhost/claude-code:https-sources-test`, not `:latest`) | Passed: all fetches from `https://deb.debian.org`; image `6310a9ad30b3` reports Claude Code 2.1.316 and OpenSpec 1.16.0 |
| Image contents | Both `URIs:` are `https://`; `/tmp/apt-bootstrap-ca.pem` absent; `/run/secrets` empty; Debian `ca-certificates.crt` present (148 roots); no file containing "Cato Networks" in the filesystem; no CA material in image history |
| `tests/image-smoke.sh` (read-only root, `noexec` tmpfs, all capabilities dropped, uid 1000) | Passed |
| Build without secret, final recipe (`--no-cache`, TLS-intercepted host) | Failed closed, as expected: exit 100 with certificate verification errors; no image tagged |
| `test_setup.py` (branch versus `main`, same runner) | 64 versus 63 tests; the same 2 environment errors on both (smoke tests needing a real engine); new host-CA build test passed |
| `test_wrapper.py` (branch versus `main`, same runner) | 72 versus 70 tests; the same 22 environment failures on both (proxy hardening and effective budgets need a real engine); `main` also had a timing failure in `test_lifetime_notice_preserves_status` that passed on the branch |
| Guard toolchain with `build-ca` secret (TLS-intercepted host) | Passed: `apk` verified through Cato; image `b00a8c07fd15` has gcc 13.2.1, no `/tmp/apk-bootstrap-ca.pem`, empty `/run/secrets`, and no file containing "Cato Networks" |
| Guard toolchain without secret, `--no-cache` (TLS-intercepted host) | Failed closed, as expected: `certificate verify failed`; no image tagged |
| `test_image_pins.py` toolchain recipe check | Passed, with 6 mutated recipes rejected |
| Operator setup on the port-80-blocked Linux host (2026-11-09) | Partial: runtime, toolchain and proxy images built over HTTPS and the guard compiled; qualification then failed on that kernel's missing IPv6 (see the IPv6 entry above). Rerun on 2026-11-10: setup and qualification passed (`Sandbox: ready`). After the read-only `/dev` change, the managed provider launch reached the agent, account login succeeded and Claude Code worked (operator-reported) |

Restricted installations must rerun `--container-setup` (or qualification),
because the runtime image identity changes. On TLS-intercepting networks,
answer yes to host CA trust with a bundle that contains the interception CA.

## Session hardening baseline (B01–B05): 2026-11-08

Change: `openspec/changes/harden-session-baseline/`.

- **B01, privileges:** every agent container, in all modes including shell
  and Podman delegation, uses `--cap-drop=all` and
  `--security-opt=no-new-privileges`.
- **B02, budgets:** every agent container gets `--memory`, `--cpus` and
  `--pids-limit` (defaults 4 GiB, 2 CPUs, 512 processes). Each launch checks the
  created configuration; setup smoke and restricted qualification measure the
  effective cgroup v2 values.
- **B03, workspace roots:** sensitive physical workspace roots are refused
  before engine operations unless exact
  `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` is set.
- **B04, lifetime:** optional `CLAUDE_CONTAINER_RUN_TIMEOUT` sets the engine
  container lifetime; the exit status is preserved and a notice is printed.
- **B05, pins:** Claude Code 2.1.316, OpenSpec 1.16.0 and the base image digest
  are pinned in the `Containerfile`; `DISABLE_AUTOUPDATER=1` is set in the image.
- **Setup:** budgets and lifetime are setup questions saved in schema 2
  preferences; smoke, qualification and login use a private temporary workspace.
- **Qualification:** the identity's `hardening.agent` entry binds the
  capability settings, budgets and lifetime.

Measured on 2026-11-08/09 on WSL2 6.6.87.2 x86_64, Podman client 4.3.1 and
server 4.9.3 (rootless, Netavark, cgroup v2), from an unrestricted session with
the host socket delegated (`tests/run-runtime.sh` runner). No credentials or
model requests were used.

| Check | Result |
| --- | --- |
| Baseline `hardening-probe.sh main` (unrestricted) | `CapBnd=00000000800405fb`, `NoNewPrivs=0`, `memory.max=max`, `pids.max=2048`, `cpu.max=max`; Claude, Git, OpenSpec, `bwrap` and delegated Podman (info, child container) work |
| `hardening-probe.sh WORKTREE` (unrestricted) | All capability sets 0, `NoNewPrivs=1`, `memory.max=4294967296`, `pids.max=512`, `cpu.max=200000 100000`; the same tools, `bwrap` and delegated Podman still work. No incompatibility found |
| Pinned image rebuild (`--container-build`, maintenance) | Base `node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da` from local storage, no pull; image `7cd81e8ccd06` reports Claude Code 2.1.316, OpenSpec 1.16.0, `DISABLE_AUTOUPDATER=1` |
| `podman create --timeout` | `podman run` and `podman start --attach` both return 255 after the limit; container `ExitCode=-1` |
| `test_image_pins.py` | Passed: 2 tests |
| `bash tests/run-runtime.sh --wrapper` | Initial run: 67/70; a CA test forbade every `--security-opt`, and the home guard used `readlink` before the tool prerequisite check. After fixes: passed, 70 tests |
| `bash tests/run-runtime.sh --setup` | Passed: 63 tests |
| `bash tests/run-runtime.sh` | Passed: 16 tests, including effective budgets in both state modes with and without delegation, enforced process budget, lifetime limit and refused home workspace |
| `bash tests/run-runtime.sh --network-policy` | Passed: 14 tests |
| `bash tests/run-runtime.sh --qualification` | Initial run: 4 failures, because the fixed input validator rejected the new `budgets` field; then 1 failure on the missing-report message. After fixes: passed, 18 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Initial run: 2 failures; the scratch workspace was under the runner's private `/tmp`, which the engine cannot bind. Moved under `~/.cache`: passed, 2 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 19 tests (1 skipped) |
| `bash tests/run-runtime.sh --network` | Passed: 20 tests in 838 s, including offline/provider effective budgets and lifetime expiry with owned proxy cleanup |
| Operator `--container-setup` on the real installation (2026-11-09) | Passed: provider installation rebuilt the runtime, toolchain and proxy images and reported `Sandbox qualification: locally-qualified` and `Sandbox: ready`; no login or model request. The next session launched from it measured `CapEff`/`CapBnd` 0, `NoNewPrivs` 1, `memory.max` 4294967296, `pids.max` 512 and `cpu.max` `200000 100000` |

## Updating pinned image inputs

The runtime image inputs change only through explicit maintenance:

1. Edit `CLAUDE_CODE_VERSION`, `OPENSPEC_VERSION` or the base image digest in
   the `Containerfile`. Capture a base digest with
   `podman pull docker.io/library/node:22-bookworm-slim` followed by
   `podman image inspect --format '{{index .RepoDigests 0}}' docker.io/library/node:22-bookworm-slim`.
2. For a new Claude Code version, revalidate the provider endpoint inventory
   and update `tested.cli` (and the policy revision when hosts change) in
   `agent/policies/default.json` in the same change.
3. Run `python3 -m unittest discover -s tests -p test_image_pins.py`.
4. Rebuild with exact `CLAUDE_CONTAINER_MAINTENANCE=1`, for example
   `CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_MAINTENANCE=1 ./claude-container.sh --container-build`,
   and confirm `claude --version` and `openspec --version` in the image.
   On a TLS-intercepting network, also set `CLAUDE_CONTAINER_TRUST_HOST_CA=1`
   (with `CLAUDE_CONTAINER_CA_BUNDLE` when needed), so that the bundle reaches
   the build as the `build-ca` secret.
5. Rerun `--container-setup` (or `--container-qualify` for a manual protected
   installation), because the runtime image identity changes.
6. Add a dated entry to this record with the versions, digest and results.

Sessions never update these inputs: the root filesystem is read-only and the
image disables the Claude Code auto-updater.

## Residual exfiltration disclosure and account profile reduction (N21): 2026-11-08

Change: `openspec/changes/disclose-residual-exfiltration/`.

- **Setup:** selecting provider mode in `--container-setup` prints a
  residual-exfiltration notice and requires an acknowledgement. Declining
  returns to the network-mode question.
- **Documentation:** help, README, `docs/setup.md` and
  `docs/network-contract.md` disclose the foreign-credential channel.
- **Interception:** credential-injecting TLS interception is documented as
  evaluated and not implemented.
- **Account profile:** narrowed to `api.anthropic.com` and
  `platform.claude.com`, under policy revision `anthropic-2026-11-08-v2`.

### Static endpoint inventory

Method: a `grep` of the installed CLI 2.1.316 binary for `https://` URLs on
Anthropic hosts. No credentials were used and no requests were made.

| Host | Endpoints found | Where it is used |
| --- | --- | --- |
| `platform.claude.com` | `/v1/oauth/token` | OAuth code exchange and refresh, from the container |
| `platform.claude.com`, `claude.com` | `/oauth/authorize`, `/cai/oauth/authorize` | Authorization pages, opened in the host browser |
| `api.anthropic.com` | `/api/oauth/...` (profile, usage, roles, API key creation) | Account calls |
| `claude.ai`, `claude.com` | Settings, upgrade, download and docs links; remote-code and connector features | User-facing links, or features disabled by `disable_optional_traffic` |

A credential-free `GET /api/oauth/usage` through the proxy returned 401 on both
allowed hosts. The path exists there and the proxy permits it.

### Credential-free suites

**Sandbox:**
- 101 tests passed, 9 skipped: policy, TLS ClientHello, TLS proxy, mux, session,
  agent profile, alignment, platform and the new `AccountInventoryTests`.
- `test_setup` has the same failures as the unmodified baseline (protected-path
  checks on drvfs and a world-writable `/tmp`), plus the three new
  questionnaire tests for the same reason. With the release lookup stubbed, the
  three new tests and the existing default/conflict questionnaire test passed.

**Host:**

| Suite | Result |
| --- | --- |
| `--network-policy` | 14 OK |
| `--network` | 19 OK. `test_tls_destination_binding_controlled_profiles` confirms the controlled two-host account inventory and `policy-denied` for `claude.ai` and `claude.com`; evidence `policy=anthropic-2026-11-08-v2`. |
| `--guard` | 19 OK, 1 idle skip |
| `--qualification` | 15 OK |
| `--setup-runtime` | Initial run: 1 pass, 1 failure. The provider test did not answer the new acknowledgement prompt (`PTY prompt timeout: Authentication method`). Only the test answer list was fixed. |

Host reruns, with `SANDBOX_TEST_TMPDIR` on native storage:

| Suite | Result |
| --- | --- |
| `test_wrapper.py` | 64 OK, including `AccountInventoryTests` and the help tests |
| `test_setup.py` | 60 OK, including the three acknowledgement and notice tests |
| `--setup-runtime` | 2 OK, including the fresh provider setup with the acknowledgement |

A real managed setup rerun showed the notice and acknowledgement and installed
policy `anthropic-2026-11-08-v2`. Its locally qualified sessions are the ones
used for the authenticated checks below.

### Operator-reported authenticated checks

All checks ran through the managed restricted wrapper in provider mode:
- profile `anthropic-account`;
- policy `anthropic-2026-11-08-v2`, digest `0c0c8651…a5ac`;
- guard `abi3-seccomp-mux-v1`;
- locally qualified installation;
- shared state;
- CLI 2.1.316.

No credentials, URLs or bodies are recorded.

| Check | Result |
| --- | --- |
| Logout, fresh login and ordinary requests | Passed; the session in use was authenticated through the narrowed profile |
| Forced refresh | `expiresAt` set to one minute in the past; the request returned `ACCOUNT_REFRESH_OK` and exit 0. The stored expiry advanced from 07:31:58 to 07:57:52. The exit diagnostics held only one `transport-closed` record and no policy denials. |
| Second refresh | After a second forced expiry, re-entering an interactive session refreshed the token |
| `/usage` panel | "Failed to load usage data" right after session start, but loaded after the first request in the same session with the same policy. This matches the CLI's 5-second usage timeout and refresh-coordination path, not a policy denial. |

The `/usage` failure was not reproduced as a denial.

Denials observed in an earlier v2 session:
- optional traffic: `statsig.anthropic.com`, `github.com`, `pypi.org`,
  `registry.npmjs.org`;
- at one instant: `claude.ai`, `console.anthropic.com` and
  `mcp-proxy.anthropic.com`.

The last two hosts and the optional-traffic hosts were never allowed. The
feature behind the `claude.ai` attempt is unidentified and was not needed for
login, requests, refresh or usage. Fallback D3 (restoring the four-host profile)
was not needed.

After the checks, the policy's `tested.authentication` metadata was updated to
record them. Destinations and revision are unchanged, but the digest changes to
`f26ff7ad…a7fa`, so installations must rerun setup and requalify.

## Retried ClientHello binding and cleanup (N22, N24): 2026-11-08

Change: `openspec/changes/bind-retried-tls-hello/`. Destination-binding
enforcement identity is now `tls-clienthello-sni-v2`. After the initial
ClientHello, the proxy holds client bytes until the upstream's first handshake
message is classified. After a TLS 1.3 HelloRetryRequest, the retried ClientHello
must name the same host before it is forwarded. TLS 1.2 renegotiation is
documented as an accepted, uninspected limitation. N24 cleanup:
- the per-session `resolv.conf` write is removed;
- revisions are defined once in `network/revisions.py`;
- the host probe runs through pipes and reports failures with an actionable message;
- `test_tls_proxy.py` imports independently of the test runner's start directory.

### Observed gap

Unfiltered, an OpenSSL 3.0.22 server restricted to P-256 sends a
HelloRetryRequest to a default Python client whose ClientHello names
`allowed.test`. When it then receives a ChangeCipherSpec and a ClientHello naming
`alternate.test`, it answers with a ServerHello; its SNI callback saw both names.

Reproduction: in memory with `ssl.MemoryBIO`, in
`tests/test_tls_proxy.py::test_real_openssl_retry_binding`, and with the new
fixture endpoint `/retry-switch-control`, which returned `serverhello` in a
local run. The retry gap was therefore exploitable against OpenSSL-based
endpoints that serve both names.

### Executed in the restricted Claude session

The session has no `AF_UNIX` bind, no Podman service, and `/tmp` is `noexec`.
`SANDBOX_TEST_TMPDIR` pointed to an executable drvfs directory outside the
repository.

| Command | Result |
| --- | --- |
| `test_tls_client_hello.py` | Passed: 11 tests. New: record-boundary rule, retry-mode prefixes (CCS, early data, byte-by-byte), retry-mode rejections and the `ServerHello` observer (HRR, TLS 1.2/1.3 ServerHello, alert, non-TLS, one-byte records, early decision, fixed storage) |
| `test_tls_proxy.py` | Passed: 12 tests, run three times. New: matching retry with held early data and CCS; zero-byte rejection of switched, missing, ECH, alert, trailing and non-TLS retried hellos with `tls-retry-identity` or the fixed reason; held pipelined second hello; no-retry TLS 1.3, TLS 1.2 and alert flights forwarded unchanged; deadline, EOF and overflow; concurrent failure isolation; reservation release; and a real OpenSSL HRR handshake through the proxy plus the switched-SNI rejection, with an unfiltered positive control. With the gate removed, 9 cases fail |
| `test_session.py` | Passed: 15 tests, 7 skipped (AF_UNIX). New: probe output relayed when the caller's stderr is a socket, and a silent status-78 probe reported with the actionable message. The test fails against the previous inherited-descriptor probe |
| `test_guard.py` | Passed: `GuardRevisionSource` (18 runtime cases skipped). Fails on an edited `GUARD_REVISION` define |
| `test_network_policy.py` | Passed: 14 tests, the snapshot case skipped here (needs protected native ancestors). A v1 manifest is rejected |
| `test_mux.py`, `test_alignment.py`, `test_agent_profile.py`, `test_platform.py`, `test_qualification.py` | Passed (runtime-only cases skipped) |
| `test_wrapper.py`, `test_setup.py` | Unavailable here: drvfs reports mode 0777 and refuses `chmod`. The same 62 wrapper errors occur on the unchanged checkout. To run on the host |
| `bash -n claude-container.sh`, `git diff --check` | Passed |

### Executed on the WSL host

Operator run on 2026-11-08, with a native temporary directory and rootless
Podman. There were no initial failures.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_wrapper.py` | Passed: 62 tests |
| `python3 -m unittest discover -s tests -p test_setup.py` | Passed: 57 tests |
| `python3 -m unittest discover -s tests -p test_session.py` | Passed: 15 tests, none skipped. The socket-stderr probe and the v1 readiness rejection ran |
| `bash tests/run-runtime.sh --guard` | Passed: 19 tests, 1 skipped (the 305-second idle check belongs to `--guard-idle`). Guard sha256 `0c647dfe…7ec9`, unchanged revision `abi3-seccomp-mux-v1`. Controlled TLS evidence reported `enforcement=tls-clienthello-sni-v2`. The TLS binding fixture passed through the production guard, relay and proxy. Its assertions include `/retry-switch-control` = `serverhello` and the rejection of a switched retried hello after a real fixture HelloRetryRequest, under normal, pressure and delayed-close-ack faults |
| `bash tests/run-runtime.sh --network-policy` | Passed: 14 tests. The snapshot test confirms that the session directory holds only `config`, `logs` and `transport`; v1 manifests are rejected |
| `bash tests/run-runtime.sh --network` | Passed: 19 tests in 890 s. Results: v2 readiness; 64 slow inspections at a 41 MiB peak against a 256 MiB limit; 64 verified TLS connections at a 46 MiB peak; pids and memory exhaustion enforced in the session cgroup; the synthetic Messages API run through the real Claude Bash tool |
| `bash tests/run-runtime.sh --qualification` | Passed: 15 tests, `status=locally-qualified` |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| Managed `--container-setup`, offline and provider launches | Operator reported success after rebuilding the installation and images |

The guard run printed a `DeprecationWarning` for an invalid `\S` escape in the
readiness shim of `tests/test_network_runtime.py`. The regular expression still
worked. The escape is now doubled in the generated script.

Not separately observed: the operator did not record a provider launch of the
pre-change installation failing readiness. That rejection is covered by the
`tls` case of `test_readiness_binds_policy_guard_and_protocol` (`--network`), by
the v1 readiness case in `test_session.py` and by the v1 manifest rejection.

Unavailable: whether real Anthropic endpoints send a HelloRetryRequest to the
installed client. This was not measured, and no credentials or model calls
were used.

## Restricted session helper extraction: 2026-11-08

Change: `openspec/changes/extract-network-session/`. `network/session.py` now owns
preflight, the guard probe, proxy lifecycle, restricted arguments and proxy
cleanup. `claude-container.sh` went from 850 to 729 lines and calls `prepare`,
`start`, `agent-args` and `stop`.

### Executed in the restricted Claude session

This session has no `AF_UNIX`, no Podman service and only `noexec` or
permission-emulating storage. The helper suite ran on the 9p checkout mount,
which allows execution.

| Command | Result |
| --- | --- |
| `SANDBOX_TEST_TMPDIR=<exec dir> python3 -m unittest discover -s tests -p test_session.py` | Passed: 14 tests, 6 skipped. The skips are the readiness-dependent `start` success and fail-closed cases, which need a Unix socket fixture. Covered here: argument refusal, prepare outputs and refusals, invalid proxy ID and engine status, the 10-second readiness bound, process-group termination of an interrupted `start` with recovery by `stop`, ownership-confirmed `stop` paths, deadline bounding with a TERM-ignoring engine, the diagnostics tail, and exact NUL-safe `agent-args` per mode |
| `test_alignment.py` | Passed: 9 tests. Covered: the helper in the shared inventory; the wrapper calls all four operations and contains no in-line lifecycle, with a detection self-test; the literal scan, which caught and fixed two agent literals in the new tests |
| `test_agent_profile.py`, `test_network_policy.py`, `test_qualification.py`, `test_platform.py`, `test_mux.py`, `test_tls_*.py` | Passed (runtime-only cases skipped) |
| `bash -n claude-container.sh`, `git diff --check` | Passed |
| Simulated port with the dummy profile (`network/`, `setup/` and shared tests copied unchanged, `diff -rq` identical) | Shared suites including `test_session.py` passed unchanged |

### Executed on the WSL host

Operator run on 2026-11-08, native temporary directory, rootless Podman. No
initial failures.

| Command | Result |
| --- | --- |
| `test_session.py` | Passed: 14 tests, none skipped (socket-dependent `start` cases included) |
| `test_wrapper.py` | Passed: 62 tests, with the real `session.py` in the restricted fixture, including `test_proxy_probe_timeout_and_interruption_clean_only_proxy` and `test_stalled_controls_and_repeated_signal_are_bounded` |
| `test_setup.py` | Passed: 57 tests, including the manifest test with `network/session.py` |
| `run-runtime.sh --guard` | Passed: 18 tests, 1 skipped (idle case, run separately) |
| `run-runtime.sh --guard-idle` | Passed: 1 test (346 s) |
| `run-runtime.sh --network-policy` | Passed: 14 tests |
| `run-runtime.sh --network` | Passed: 19 tests |
| `run-runtime.sh --qualification` | Passed: 15 tests |
| `run-runtime.sh --setup-runtime` | Passed: 2 tests |

### Managed setup and launches

Operator run on 2026-11-08. A managed `--container-setup` completed for the
offline and the provider mode. The offline launch started a working container
without model access, as expected. The provider launch worked normally,
Claude Code included. The session running this change uses that installation.

## Agent profile extraction: 2026-11-08

Change: `openspec/changes/extract-agent-profile/`. This record covers only the
checks that ran inside a restricted Claude sandbox session. That session denies
`AF_UNIX`, has no usable Podman service or compiler, and has no native directory
with protected ancestors (`/tmp` and the home are mode 1777, the checkout is on a
0777 Windows mount). Runtime, guard build, wrapper and setup suites were
therefore not run here. They remain required acceptance and are listed below.
No credentials, model requests or engine operations were used.

### Executed here

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_agent_profile.py` | Passed: 8 tests, 1 skipped (protected-path positive case needs native protected storage) |
| `python3 -m unittest discover -s tests -p test_alignment.py` | Passed: 7 tests (literal scan, injected-literal detection, wrapper/profile consistency) |
| `python3 -m unittest discover -s tests -p test_network_policy.py` | Passed: 14 tests, 1 skipped (protected snapshot) |
| `python3 -m unittest discover -s tests -p test_qualification.py` | Passed: 15 tests, 7 skipped (runtime) |
| `test_mux.py`, `test_tls_client_hello.py`, `test_tls_proxy.py`, `test_platform.py` | Passed: 26, 7, 5, 4 tests |
| `test_guard.py`, `test_network_feasibility.py` | Skipped (runtime only); import-level checks passed |
| Effective policy comparison, HEAD `network/policy.py` + `network/policies/default.json` against the new loader with profile rules | Identical canonical profiles and revision `anthropic-2026-11-06-v1 02b7baf6…fbca` |

`test_setup.py` and `test_wrapper.py` cannot start in this session: setup
temporary state requires protected ancestors, and wrapper fixtures require
`AF_UNIX`. As a diagnostic only, `test_setup.py` was also run with `/tmp`'s
group/other write bits hidden from in-process `os.stat`. Its error set matched
HEAD exactly (29 environment errors in both, all from subprocesses on
`noexec`/unprotected storage). This found and fixed four test-edit regressions.
The new rollback test passed under the same diagnostic. This is not acceptance
evidence.

### Simulated port

`network/`, `setup/` and the 22 shared test files were copied unchanged to a
scratch tree, with a dummy profile and policy:
- `dummy-container`, prefix `DUMMY_CONTAINER`, images `localhost/dummy-*`;
- authentication methods `login` and `key`, with hosts under
  `exampleprovider.test`.

`diff -rq` against this checkout's `network/` reported no differences. In the
scratch tree these passed without edits:
- `test_alignment.SharedComponentAlignment`;
- `test_agent_profile`, `test_network_policy`;
- `test_qualification.QualificationContracts`;
- `test_mux`, `test_tls_client_hello`, `test_tls_proxy`, `test_platform`.

### Host acceptance: 2026-11-08

Run by the operator on the WSL2 host (`6.6.87.2-microsoft-standard-WSL2`, rootless
Podman with the existing same-host user service), native storage, no credentials
or model requests beyond the local synthetic Messages fixture.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_setup.py -v` | Passed: 57 tests, including the new profile installation, rollback and workspace-decoy tests |
| `SANDBOX_TEST_TMPDIR=<native> python3 -m unittest discover -s tests -p test_wrapper.py -v` | Initial run: 61 passed, 1 failed (`test_socket_fallback_and_invalid_sources`) |
| Same, `-k test_socket_fallback` after the test fix | Passed |
| `podman build --pull=never --tag localhost/claude-guard-toolchain:development …` | Cached, toolchain ID `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c` (unchanged) |
| `SANDBOX_GUARD_TOOLCHAIN=<id> bash tests/run-runtime.sh --guard` | Passed: 18 tests, 1 skipped (305-second idle check, separate `--guard-idle`). Production `sandbox-egress-guard` SHA-256 `0c647dfea75667a46a8cd4cc4dfea4ee3d10363752ea7ce5957162bacd6d7ec9` |
| `… ./claude-container.sh --container-build --version` | Runtime image `4cf5ae97d03e3d1d6a92c7d9dc36fa3d5389dfd68b8529eae6ee75e630dc67a1`, `COPY … /opt/sandbox-egress/`; Claude Code 2.1.316 |
| `bash tests/run-runtime.sh --network-policy` | Passed: 14 tests, including the protected snapshot case |
| `bash tests/run-runtime.sh --network` | Passed: 19 tests in 736 s, including the real Claude tool through the guard, relay and proxy. 64 slow inspections and 64 verified TLS connections stayed within `pids.max=128` and `memory.max=268435456`. Pids and memory exhaustion were enforced and failed closed |
| `bash tests/run-runtime.sh --qualification` | Passed: 15 tests (installed offline/provider gates, stale/unsafe reports, cancellation, concurrency) |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |

The initial wrapper failure was environmental and unrelated to this change. With
`XDG_RUNTIME_DIR` unset, the wrapper falls back to
`/run/user/<uid>/podman/podman.sock`, which exists on this host. The test
asserted that the socket was missing. The test now checks the selected fallback
endpoint when that socket exists, and the missing-socket diagnostic otherwise.
`claude-container.sh` socket selection is unchanged.

Every TLS run reported policy identity `anthropic-2026-11-06-v1 45f6456484…e1f5`
and `tls-clienthello-sni-v1`. The controlled-test policy identity differs from
the default policy's because those fixtures add a controlled profile.

A second `--guard` run reproduced the same guard SHA-256 `0c647dfe…7ec9` and
passed 18 tests, with the idle check still skipped. Running `./claude-container.sh`
from the checkout with no mode set refused before any engine call, with the
`--container-setup` guidance. This confirms missing-setup admission only. It does
not test a stale protected installation.

### Managed setup rerun: 2026-11-08

The operator reran `claude-container.sh --container-setup` against the existing
managed installation `~/.local/lib/claude-container`. Choices: provider/account,
shared state, YOLO enabled, endpoint default. Images were refreshed and the guard
was recompiled.

- Built and tagged:
  - runtime `8f1182709a773704974ab23a914d0df75ced9754a791e61dd6a0c157253558af`
    (`COPY … /opt/sandbox-egress/`);
  - toolchain `0b69ba43…402c` (unchanged);
  - proxy `c56cb591c3086db9f06188ee3644c8d57925db7d01c95580a6f73f23e32c4fea`
    (`/opt/sandbox-egress/proxy.py`).
- The packaged guard reported `sandbox-egress-guard abi3-seccomp-mux-v1`.
- Setup printed `Sandbox qualification: locally-qualified` and `Sandbox: ready`,
  then activated the release.
- The profile drove the prompts. They showed the same text as before the change:
  - "account reuses Claude account login; api uses an API key supplied at launch";
  - `protected profile: anthropic-account`;
  - `auth login --claudeai`.
- A provider launch from a separate workspace through the managed launcher
  reported:
  - policy `anthropic-2026-11-06-v1 02b7baf6…fbca`, unchanged from before the
    change;
  - guard `0c647dfe…7ec9`;
  - `sandbox-egress-guard: enforced revision=abi3-seccomp-mux-v1 abi=3`.

  It ran a full Claude session, the one that recorded these results. Inside it,
  `/run/sandbox-egress` and `/tmp/sandbox-runtime` exist and `/run/claude-egress`
  does not. On exit the session reported the expected sanitized
  `transport-closed` diagnostic.

These items were not exercised manually on this installation:
- refusal of the old qualification before the rerun;
- an offline launch;
- an interrupted update.

Automated runtime evidence above covers them on protected installations: the
stale and changed-code report refusal and both modes in `--qualification` and
`--network`, and owned recovery and rollback in `--setup-runtime` and
`test_setup.py`.

### Idle acceptance

`bash tests/run-runtime.sh --guard-idle` passed:
`test_guarded_multiplex_idle_resume` ran in 353.5 s through the production guard,
relay and proxy. It used `tls-clienthello-sni-v1` and controlled policy
`anthropic-2026-11-06-v1 45f6456484…e1f5`. All acceptance items for this change
are recorded.

## Multiplex stream-failure isolation (N23): 2026-11-08

Change: `openspec/changes/archive/2026-11-08-isolate-mux-stream-failures/`. Measured on WSL2
`6.6.87.2-microsoft-standard-WSL2` x86_64, usable Landlock ABI 3, rootless Podman
server 4.9.3, Netavark, cgroups v2/systemd and standard OCI seccomp.
SELinux/AppArmor were disabled. Host Python was 3.11.2. Runtime checks used the
existing same-host Unix service, disposable native volumes and protected test
installations. No real credentials, provider authentication, model requests or
user-service activation were used. The actual Claude CLI test talks only to the
local synthetic Messages fixture with a synthetic key.

Measured candidate identities:

- Runtime image: `d3df53d6595a3e8edb7dacac648092ab498d191475b9bd07252fab705bc4bedb`.
- Production proxy image: `da6f4176269a91cc85843d713ec217388951c0c469fff78059fbdca9c9842f25`.
- Guard: `6dc1ab5478118317f1228b21c04b7dfe95de7a5472e4fb811bb0a53ba0342a2c`.
- Guard toolchain: `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c`.
- `network/mux.py`: `13a8ec8eeb6ad261680855cf855072c675499129e4267ed5a22104a2d1db0fb8`.
- `network/relay.py`: `3f37c023096e497bba83ea5d65193b5aaa781e708e56b25806debeb19a43484f`.

Both candidate images were built from the checked-out Containerfiles with
`podman build --pull=never`, retaining existing dependency layers. Controlled TLS
tests build disposable fixture images from this production proxy and pin their
identities separately; these images add only synthetic certificates/upstream
fixtures. No operator image tags or installations were replaced.

### Component evidence and unchanged limits

The regression against the original implementation failed on both endpoint
roles: a withheld CLOSE acknowledgement closed an unrelated stream at the real
ten-second deadline (two cases, 20.066 s total). Before the change, a separate
controlled blocked-writer experiment closed the channel after 66 OPEN/CLOSE
pairs with 64 controls queued. These injected component faults do not establish
their frequency in real Claude sessions.

The revised mux suite passes 26 tests (23.631 s). It covers real ten-second
acknowledgement expiry in both roles, delayed acknowledgement/capacity recovery,
concurrent close ownership, exhausted outstanding slots with an established
working stream, crossing open/data/credit/EOF frames, invalid transitions,
discard accounting, coalesced closure bursts, queue recovery, caller cancellation
at queue/lock/drain, session teardown and permanent write stalls. Shortened
component deadlines and instrumented socket pairs remain separate from runtime
acceptance. Initial development runs also caught a misplaced acknowledgement
flag and a misplaced test assertion; both were corrected before final passes.

There remain 64 outstanding stream slots, 64 queued controls, one control sender,
at most 64 shared channel-owned stream-close tasks, 16 KiB DATA frames, 256 KiB
receive credit per stream and a 16 MiB session buffer bound. Missing ACK retains
compact state and its admission slot until remote CLOSE/channel teardown, never
payload buffering or a running application tunnel. Queue admission, writer-lock
acquisition and drain share a finite 30-second control-write deadline. The local
ACK wait remains ten seconds after transmission; partial frames retain their
separate absolute ten-second deadline, idle stream operations 300 seconds and
tunnel lifetime 12 hours. No runtime limits were raised or removed.

### Production-path evidence

`bash tests/run-runtime.sh --guard` passed 18 discovered tests in 158.377 s,
including 17 executed tests and the separately opt-in idle test skipped. Mocked
guard component checks remain instrumentation only; the checks below use the
unmodified static production guard, confined relay and trusted proxy.

The test-owned wire boundary lives outside those processes and translates only
test stream IDs, leaving TLS bytes intact. One case withholds the first CLOSE
acknowledgement for 11 seconds while an independent TLS stream completes all 75
progress chunks; a subsequent approved TLS request succeeds on the original
channel. Another temporarily stops consuming proxy output and injects 8,140
sequential immediately closed streams until shared socket backpressure is
observed, then resumes reading. The established TLS stream completes and another
approved connection succeeds on the same channel. Exact internal queue occupancy
is asserted by the component test; runtime evidence observes propagated socket
pressure and recovery without claiming an internal runtime queue measurement.
Both cases retain denied-authority and mismatched-SNI zero-byte rejection
controls through the production code. No shipped fault flag, syscall mock or
application-command exception is involved.

The first runtime-pressure attempt failed with the intermediate proxy
`38a99d69448babe57da92bdfa2bb8af9c41998fcc3652bc5e25e3a3ceeab53fb`:
the unrelated TLS reader timed out. Investigation addressed cancelled-worker
reclamation for coalesced OPEN/CLOSE and the test boundary's partial-write
pressure release. The full final guard pass above supersedes that attempt; the
initial filtered run remains failed (4 discovered tests, one skipped, 225.008 s).

### Integration and installation checks

| Check | Result |
| --- | --- |
| Wrapper unittest suite | Passed: 62 tests, 218.419 s |
| TLS parser/proxy suites (`test_tls_*.py`) | Passed: 12 tests, 0.774 s |
| `bash tests/run-runtime.sh --network-policy` | Passed: 13 tests, 1.951 s |
| `bash tests/run-runtime.sh --setup` | Passed: 54 tests, 23.490 s |
| Production network acceptance | All 19 cases covered: initial 15 passes plus successful scoped reruns of the four fixture failures (see below) |
| Protected qualification acceptance | Passed: 13 tests, 115.937 s; requested runtime and proxy built from current sources |
| Setup runtime acceptance | Passed: 2 tests, 158.856 s; candidate runtime/proxy, actual protected installation and rollback |
| Real-duration 305-second idle acceptance | Passed: 1 test, 366.554 s; final candidate pair, actual 305-second idle pause |
| Change strict validation, Bash syntax, Python parsing and whitespace | Passed |
| Real authentication, native Linux/active LSMs and real user-service activation | Unavailable; not exercised by N23 |

Concurrent initial qualification/setup runs encountered actual bounded Podman
operation timeouts, including a 30-second identity probe, setup preparation and
proxy-budget inspection. A provider probe also ended early in one run, and a
candidate smoke returned status 1 after successful qualification in another.
These were failures, not skipped controls; concurrency was present but is not
proof of the cause of each failure. Initial qualification runs were 13 tests in
229.630 s and 183.406 s (one failure each); a subsequent run passed all 13 in
168.082 s but still selected the historical proxy. Setup runs failed one of two
tests in 178.831 s, 86.477 s and 80.725 s respectively. Final reruns retain all
production deadlines. Qualification acceptance now builds its disposable proxy
from current sources instead of selecting the historical TLS-change tag.
The setup acceptance harness explicitly
routes only its prepared-runtime image lookup to the requested candidate, as it
already does for its disposable proxy, without retagging operator defaults.

The first full network run executed 19 tests in 766.918 s: 15 passed and four
failed because the shared fixture supplied no ordinary runtime mode, retaining
the pre-N20 implicit-offline assumption. The four diagnostics were missing-setup
refusals, including the bootstrap-tampering and Windows-workspace cases. The
fixture now explicitly selects offline; provider cases override it as before.
All four scoped reruns passed: guarded argv/stdin/status/TTY in both state modes
(1 test, 62.699 s), explicit offline/delegation rejection (1 test, 24.839 s),
bootstrap tampering before application execution (1 test, 2.695 s), and Windows
workspace persistence/restrictions (1 test, 31.342 s). The original full run
remains failed; these scoped results complete its missing coverage. Other
production-network cases passed, including both profile inventories, synthetic
Claude tool execution, 64 verified TLS connections, effective 256 MiB/128-process
budgets, actual process/memory exhaustion, CA off/on, signals and owned cleanup.

Final selected-image qualification and setup were run sequentially after the
network reruns, with no production-code or deadline changes. Qualification covers
missing/stale/unsafe evidence, changed input identities, cancellation, concurrent
atomic publication, fixed probes and real provider enforcement. Setup covers a
fresh provider installation with host CA trust, a new terminal/managed launcher,
unchanged rerun, offline migration, failed proxy/smoke candidates preserving the
previous activation and reports, and unrestricted fresh setup/shell use. The
initial failures above remain part of the record; final successful reruns do not
retroactively change their outcomes. The exact cause of every transient initial
failure was not established.

Deployment requires matching protected code and both images, followed by setup
or manual local qualification. Running sessions retain their previous transport
until restarted. Failed qualification preserves the prior activation; rollback
uses matching previous code/images and current matching evidence. These checks
do not activate an operator installation or publish release-measured evidence.

### Specification synchronization and archive: 2026-11-08

All 14 implementation/acceptance tasks and all four planning artifacts were
complete before archiving. The `network-egress` main spec now contains the
updated multiplex transport requirement and the two added closing-state/control-
pressure requirements. Comparison verified all delta descriptions and scenarios,
with title/Purpose and every unrelated requirement preserved exactly; no delta
operation headers remain. Change strict validation, main-spec validation (9/9)
and whitespace checks passed. Main specs retain long-requirement warnings,
including the existing multiplex requirement; no unrelated requirement was
refactored for lint. The complete change, including `.openspec.yaml`, was moved
to the archive path above with file hashes preserved. Only specs/documentation
changed after the implementation acceptance runs; measured transport hashes and
candidate image identities remain unchanged.

## Missing-setup admission (N20): 2026-11-08

Change: `openspec/changes/archive/2026-11-08-clarify-missing-setup-startup/`. Measured on WSL2
`6.6.87.2-microsoft-standard-WSL2` x86_64, usable Landlock ABI 3, rootless Podman
server 4.9.3 with Netavark, cgroups v2/systemd and standard OCI seccomp.
SELinux/AppArmor were disabled. Host Python was 3.11.2; OpenSpec CLI was 1.16.0.
Runtime tests used the existing same-host Unix service and disposable native
volumes with protected ancestors. No real credentials, authenticated/model
requests or user-service activation were used.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_wrapper.py -v` | Passed: 62 tests, 176.186 s; synthetic state and executable temporary storage |
| `bash tests/run-runtime.sh --setup` | Passed: 54 tests, 16.615 s; setup unittest suite on disposable protected native storage |
| `bash tests/run-runtime.sh --qualification` | Passed: 13 tests, 119.379 s; report contracts and actual installed offline/provider enforcement |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests, 176.374 s; protected provider/offline/unrestricted installation, managed launch and failed-update preservation |
| `bash -n claude-container.sh` / `git diff --check` | Passed |
| `openspec validate clarify-missing-setup-startup --strict` | Passed; existing main-spec long-requirement warnings remain separate |
| Real authentication and systemd user-service activation | Unavailable; not exercised or required by this change |

Admission coverage includes unset/empty mode, interactive and redirected input,
shell/build/worktree composition, maintenance-only requests, unavailable tools,
unrelated invalid controls and misleading workspace configuration. These cases
return status 1 with setup guidance before engine calls or state creation.
The suggested command works from another workspace and through symlinks whose
names contain spaces and shell metacharacters without executing those characters.
Explicit invalid modes retain their existing diagnostic. Managed saved modes,
nonempty overrides and explicit empty overrides are tested through the actual
wrapper; adapter stand-in checks separately retain argv/stdin/cwd/status behavior.
Help, setup and fixed qualification keep their own dispatch and argument checks.

Installed acceptance confirms missing/stale/unsafe reports still block ordinary
restricted launch, fixed probes cannot run supplied applications, cancellation
cleans owned resources and concurrent gates publish complete reports. Setup
acceptance exercises a new terminal without exported wrapper settings, provider
rerun, offline migration, CA trust, unrestricted shell use and failed proxy/smoke
candidates preserving the previous activation and reports. All listed full suites
passed in this run; no runtime control or deadline was relaxed.

Measured input identities:

- Wrapper SHA-256: `ab3ee7a2e8a9381f3e68901d11ffe032b3648c2b27509bf8fb6514d143b5b9c4`.
- Runtime image: `a96af83c8276d42d029a501ecfc6f886c446055ed5157a934cfeac486d9b0ef9`.
- Qualification provider proxy: `16604a740686c469ede6695bda2c3dc6ded5f9203979b5060acc383dcb0ef12f`.
- Guard toolchain: `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c`.

Setup acceptance builds and removes its own proxy candidates from the checked-out
source. These results apply to this implementation and disposable installations;
they do not activate an operator installation or add a release-measured report.
Existing restricted installations must deploy the protected wrapper through setup
or manual installation and regenerate matching qualification. The existing
last-working-release rollback procedure remains applicable.


### Specification synchronization and archive: 2026-11-08

All 10 tracked tasks and all planning artifacts were complete before archiving.
The `container-launcher`, `container-setup` and `network-egress` deltas were
synchronized into their main specs: three existing requirements updated and two
launcher requirements added. Title/Purpose sections and every unrelated
requirement were preserved. Post-sync comparison confirmed that every delta was
fully applied before moving the change, including its `.openspec.yaml`, to the
archive path above. Change strict validation, main-spec validation (9/9) and
whitespace checks passed. Main-spec validation retains long-requirement warnings,
including the updated managed-preference requirement; these warnings do not
invalidate ordinary validation. The runtime implementation is unchanged from
the acceptance runs recorded above.

## Provider idle channel regression: 2026-11-08

Change: `openspec/changes/archive/2026-11-08-fix-provider-idle-disconnect/`. Measured on WSL2
`6.6.87.2-microsoft-standard-WSL2` x86_64, usable Landlock ABI 3, rootless Podman
server 4.9.3 with Netavark, standard OCI seccomp, SELinux/AppArmor disabled.
No real credentials, authenticated provider requests or model calls were used.

| Check | Result |
| --- | --- |
| Wrapper synthetic suite | Passed, 59 tests |
| Multiplex and actual relay component suite | Passed, 16 tests; shortened test-only deadlines |
| TLS ClientHello parser / TLS proxy component suites | Passed, 7 / 5 tests |
| Policy suite on disposable native storage | Passed, 13 tests, including protected ancestors |
| Production guard suite | Passed, 15 executed tests; dedicated slow idle test skipped by default |
| `bash tests/run-runtime.sh --guard-idle` | Passed, 1 test in 361.548 seconds, including a real 305-second idle gap |
| Same idle acceptance with pre-fix receiver | Expected failure: verified TLS worked before idle, then loopback CONNECT failed with errno 111 after 305 seconds |
| Qualification suite | 11/13 initially passed; TLS cancellation readiness and concurrent platform admission failed during concurrent suite execution. Both passed on a separate two-test rerun (46.513 seconds); no qualification control was weakened |
| Production-wrapper network suite | 18/19 initially passed (979.809 seconds). Bootstrap fault acceptance stopped in preliminary qualification with `controlled TLS probe ended early`; the unchanged test passed separately (52.034 seconds), and also passed separately with the old receiver (57.571 seconds) |
| Bash syntax / whitespace / OpenSpec strict validation | Passed |
| Real authenticated idle session compatibility | Unavailable; requires separate credential/model-call authorization |

Idle acceptance used the production static guard, confined relay and trusted
proxy with unchanged timeout constants, a controlled TLS endpoint and a disposable
exact-destination policy. Matching TLS, streaming/WebSocket, denied destinations
and 15 zero-byte TLS rejection controls ran before the idle gap. A fresh verified
TLS tunnel succeeded afterwards. The proxy only admits one bootstrap channel,
so this successful resume did not replace or reconnect that channel. The old
receiver was taken from commit `f8db098cb54ce1edda894db66d1da9ce6a9f32c3` into a
separate disposable checkout; its expected failure reproduced the reported error.

Measured identities (not a new release-measured qualification entry):

- Runtime base image: `a96af83c8276d42d029a501ecfc6f886c446055ed5157a934cfeac486d9b0ef9`.
  The protected relay/multiplex sources were mounted read-only by the production
  guard fixture, as in restricted wrapper launches.
- Rebuilt production proxy: `9817b1083f1c6f27831c5d51f2c57bbe3a587c9336b9002f36f09806f5563c8b`.
- Controlled TLS image for the passing idle case: `2ca69d9606e8db80e037b23187ed171cb3e0034e964579d65fd67028031e6165`.
- Guard SHA-256: `6dc1ab5478118317f1228b21c04b7dfe95de7a5472e4fb811bb0a53ba0342a2c`;
  immutable toolchain: `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c`.
- Shared `network/mux.py` SHA-256: `2e63d6f7a7ec573c6f09420fe1f2755a795d7f54f581f60c1d0ec114df38333d`.
- Controlled policy revision/digest: `anthropic-2026-11-06-v1`
  `45f645648427d15e9616b4212b168ed08a5d7347a5c10e2c3a4d5bcde8c4e1f5`.

These results do not deploy or activate a managed installation. Follow the
matching-code/image rebuild and qualification procedure in `docs/setup.md` and
relaunch existing sessions. Production guard evidence is separate from link-time
syscall-mock component coverage in the guard suite.
The network suite included both bundled profile inventories against controlled
TLS endpoints, proxy loss, 64-stream budgets and actual process/memory exhaustion.
Initial admission/readiness failures and successful reruns are separate results;
the full network and qualification suites did not each pass in a single run.
Their intermittent failures were not reproduced in the isolated reruns, and no
claim is made that this change fixes those admission/readiness failures.

## Local restricted-platform qualification (N19): 2026-11-07–08

Implementation is tracked by
`openspec/changes/archive/2026-11-08-validate-linux-restricted-compatibility/`. Shared protected
eligibility now admits Linux/WSL2 x86_64 with stable rootless Podman server >= 4.9,
Netavark, a verified same-host Unix service, standard OCI seccomp and usable
Landlock ABI >= 3. Exact kernel/server pins and upper bounds are removed.
Actual guard installation and a complete matching local qualification remain
mandatory. Enabled SELinux/AppArmor is permitted without a compatibility
guarantee; policies and mount labels are never changed to obtain a pass.

Measured environment: Ubuntu 24.04 on Linux
`6.6.87.2-microsoft-standard-WSL2` x86_64, usable Landlock ABI 3,
Podman client 4.3.1/server 4.9.3, Netavark 1.4.0 (package
`netavark_1.4.0-4_amd64`), aardvark-dns 1.4.0, runc 1.3.4/libseccomp 2.5.5,
systemd cgroup v2 with cpu/memory/pids controllers. OCI seccomp is enabled;
SELinux and AppArmor are disabled on this host. The client endpoint is
`unix:///run/podman/podman.sock`, mapped to host socket
`/run/user/1000/podman/podman.sock`. Runtime, production proxy, toolchain and
guard identities are the same as the N18 table below. The server-reported
Netavark executable is `/usr/lib/podman/netavark`, SHA-256
`b4344a1e60cf5614544df1cce0c9457219570f80aad7d7e039e724773c2841e6`.
An old client truncates formatted server metadata; a bounded read-only raw
Unix-service info query supplies authoritative backend identity. No guessed
backend executable path is accepted.

The installed operation uses disposable native state and protected fixed
fixtures, not checkout test programs or supplied application commands. Both
state modes exercise production guard/relay paths, controlled dual-stack IP and
UDP peers, positive controls, existing/late Unix endpoints and aliases,
publication/retargeting/descriptor/alternate-syscall rejection, actual local pair
and file exchange, descendants and effective N18 settings. Provider qualification
adds controlled certificate-verified TLS, mismatched-SNI zero-byte rejection,
denied authority and proxy loss. Its exact synthetic policy/certificates remain
separate from production inventories and do not change production address checks.

Reports are private atomic files inside each protected release. Current boot,
engine/backend/security identities, code/guard, immutable images, mode/profile/
policy, CA trust and hardening determine the fingerprint. Missing/stale/unsafe
reports stop ordinary application execution. Active LSM policy identity is not
assumed reusable: the gate runs again at launch. The shipped release acceptance
inventory is empty, so these installations correctly say `locally-qualified`,
not `release-measured`; this document preserves measured regression evidence
without manufacturing portable release fingerprints.

| Check / command | Result | Evidence |
| --- | --- | --- |
| Platform unit suite | Passed: 4 tests, 0.002 s | Native/WSL kernel examples, later stable and packaged versions, malformed/prerelease evidence, ABI and enabled LSM eligibility |
| Wrapper unit suite | Passed: 59 tests, 166.070 s | Both state modes, unchanged unrestricted behavior, early prerequisites, hardening and bounded cleanup |
| `bash tests/run-runtime.sh --setup` | Passed: 52 tests, 15.934 s | Shared eligibility, mandatory candidate qualification/status, protected inventory and synthetic rollback/PTY |
| `bash tests/run-runtime.sh --network-policy` | Passed: 13 tests, 0.862 s | Protected complete helper inventory, snapshot and TLS policy checks |
| TLS parser/proxy and mux unit suites | Passed: 7 parser tests (0.213 s), 5 proxy tests (0.246 s), 9 mux tests (0.222 s) | Inspection, zero-byte rejection, streaming, isolation and protocol regressions |
| `bash tests/run-runtime.sh --qualification` | Passed: 13 tests, 123.575 s | Real installed offline/provider operations; missing/stale/unsafe reports; fixed-operation/input rejection; early/TLS-stage cancellation, concurrent atomic publication, preserved old records and ordinary-check shutdown budget |
| Qualification contract rerun | Passed: 6 tests, 1.388 s | Explicit subprocess timeout plus descendant cleanup, failed positive control/final cleanup, identity change, active-LSM requalification and exact acceptance labels |
| `bash tests/run-runtime.sh --guard` | Passed: 15 tests, 51.637 s | Real production filter/Landlock, Unix endpoints, descriptor and provider transport checks; component mocks remain separate |
| Full `bash tests/run-runtime.sh --network` | Passed: 19 tests, 741.627 s | Actual report preparation/reuse, synthetic Claude tool/API, shared/isolated invocation/stdin/TTY, concurrent policies, interrupted creation, hardening/budgets/exhaustion, CA off/on, all controlled TLS profiles and Windows-backed workspace |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests, 168.411 s | Fresh protected provider/unrestricted setup, managed launch, provider rerun and offline migration, private matching reports before activation, preserved previous report/release after failed proxy or smoke candidates, separate authentication status |
| Bash/Python syntax, tracked/untracked whitespace and OpenSpec strict validation | Passed | Changed shell scripts, Python AST parsing, `git diff --check`, explicit untracked source checks and strict N19 artifact validation |
| Native Linux / enabled SELinux or AppArmor runtime | Unavailable | No separate native host or active-LSM target is available. Synthetic eligibility cases are not native enforcement evidence; no distribution matrix or compatibility guarantee is claimed |
| Real authentication / user-service activation | Unavailable / not run | All credentials, TLS endpoints and state are synthetic; no paid requests, actual account login or real service/installation activation |

Development verification found an early `readlink` call masking the existing
missing-GNU-timeout diagnostic (two wrapper subcase failures). Resolving the
normal wrapper path after its prerequisites restored both cases; the final full
59-test run above passes. An earlier setup-runtime attempt failed provider
qualification while unrestricted setup passed; a subsequent scoped provider
rerun passed (138.532 s). The first failure is not relabeled as a pass or assigned
an unverified cause. An intermediate filtered network run passed the arguments
case but failed the following fixture setup when an already-read test module
tried to overwrite its read-only guard. Fixture refresh now unlinks only its own
old artifact before copying the immutable binary; this did not relax production
path or guard checks. Final review additionally aligned TLS-subprocess cancellation
with the driver cleanup budget and moved publication after the last cleanup.
A focused real TLS-stage cancellation test passed (23.475 s), and contract tests
verify that final-cleanup failure cannot publish a report.

All required N19 credential-free checks have passing evidence on this WSL
target. Native/active-LSM runtime and authenticated compatibility remain
separate unavailable checks, not implicit passes. No host security policy was
weakened, private-path exception introduced or real user service enabled.
Existing operator installations must rerun setup to deploy the complete protected
release, or explicitly qualify a prepared protected manual installation. These
tests did not activate an operator installation. N20-N25 remain separate.

## Restricted container hardening (N18): 2026-11-07

Implementation is tracked by
`openspec/changes/archive/2026-11-08-harden-restricted-containers/`. Restricted agent and session
proxy creation now use `--cap-drop=all --security-opt=no-new-privileges`.
Proxies additionally use `--pids-limit=128 --memory=256m`; bounded host-side
inspect and an injected fixed protected probe verify configured budgets,
effective cgroup v2 values, zero proxy capability sets, NoNewPrivs and seccomp
before the agent starts. The helper is included in protected setup releases.
Unrestricted session arguments and existing mount/CA/delegation rules are retained.

Measured environment: Linux `6.6.87.2-microsoft-standard-WSL2` x86_64,
Landlock ABI 3, rootless Netavark, Podman client 4.3.1/server 4.9.3, systemd
cgroup manager and cgroup v2 with `memory`/`pids` controllers. Standard OCI
seccomp remains enabled; SELinux/AppArmor are disabled on this measured host.
No host security policy was changed. Native Linux/active-LSM compatibility is
not established by these checks; N19 was still unimplemented at this checkpoint.

| Artifact | Identity |
| --- | --- |
| Runtime image | `a96af83c8276d42d029a501ecfc6f886c446055ed5157a934cfeac486d9b0ef9` |
| Production proxy image used by fixtures | `16604a740686c469ede6695bda2c3dc6ded5f9203979b5060acc383dcb0ef12f` |
| Guard SHA-256 | `6dc1ab5478118317f1228b21c04b7dfe95de7a5472e4fb811bb0a53ba0342a2c` |
| Toolchain image | `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c` |
| Controlled budget fixture image | `db65b5242c5b7254915ca9ac498be08336946321ea80a5d73588c7405bd0ec78` |
| Controlled exhaustion fixture image | `4f0c8b076385e1a9ea021cf27102df9bd9e1b0d1b9606de6ffc82178acc0f25f` |
| Controlled policy SHA-256 | `45f645648427d15e9616b4212b168ed08a5d7347a5c10e2c3a4d5bcde8c4e1f5` |

The controlled images add only synthetic TLS endpoints and test-only exact
loopback policy entries as described in the destination-binding record below.
The production proxy image and guard were not modified. No real credential,
public provider login/refresh or paid model request was used. All state,
installations and resource-exhaustion workloads were disposable; no real user
service was enabled or operator installation activated.

| Check / command | Result | Evidence |
| --- | --- | --- |
| `CLAUDE_TEST_TMPDIR=/tmp python3 -m unittest discover -s tests -p test_wrapper.py -v` | Passed: 59 tests, 199.363 s | Restricted/unrestricted argument grid, both state modes and shell/Claude; ignored/missing/malformed/mismatched budgets and capabilities fail before agent creation; probe timeout/interruption preserve owned cleanup |
| `bash tests/run-runtime.sh --setup` | Passed: 50 tests, 21.647 s | Protected inventory, preferences, PTY, maintenance, activation and rollback synthetic checks |
| TLS parser/proxy and mux unit suites | Passed: 12 TLS tests (0.776 s), 9 mux tests (0.481 s) | Existing inspection, concurrency, framing, streaming and failure behavior |
| `bash tests/run-runtime.sh --guard` | Passed: 15 tests, 56.657 s | Production containers now use capability drop/no-new-privileges; controlled proxy uses both budgets; unchanged real IPC and TLS/streaming/WebSocket acceptance |
| `bash tests/run-runtime.sh --network-policy` | Passed: 13 tests, 0.968 s | Protected snapshot checks include the new helper inventory; destination/policy/readiness identity regressions |
| `bash tests/run-runtime.sh --network -k restricted_hardening` | Passed: one test, 26.730 s | Offline/provider, shared/isolated state, zero agent/proxy capabilities, NoNewPrivs=1, Seccomp=2, keep-id file ownership, pair exchange and real proxy readiness |
| `bash tests/run-runtime.sh --network -k proxy_budgets` | Passed: one test, 18.196 s | 64 simultaneous partial ClientHellos, then 64 certificate-verified TLS connections with concurrent streaming, under actual session proxy budgets |
| `bash tests/run-runtime.sh --network -k resource_exhaustion` | Passed: one test, 34.252 s | Process limit returns EAGAIN and increments pids.events; memory allocation is killed with exit 137 and OOM evidence inside the proxy cgroup; proxy removal leaves egress closed and wrapper exit 37 intact |
| Full `bash tests/run-runtime.sh --network` | Initial run: 16 passed, 3 failed, 390.708 s | Offline arguments/stdin exceeded its 30-second per-launch test deadline; two cleanup assertions counted an unrelated concurrent session proxy. This is not an all-pass suite |
| `bash tests/run-runtime.sh --network -k guarded_arguments` | Passed: one test, 31.855 s | Isolated rerun verifies shared/isolated state, stdin, spaced/empty arguments, exit 37 and TTY without changing deadlines or runtime enforcement |
| `bash tests/run-runtime.sh --network -k interrupted_and_failed_creation -k provider_uses_real_proxy` | Passed: two tests, 48.861 s | Cleanup assertions are scoped to the disposable runtime; provider fixture additionally retains an unrelated same-role container. CA off/on, streaming/WebSocket and interrupted/failed creation of both roles pass |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: two tests, 65.220 s | Disposable protected provider/unrestricted setup, helper packaging, managed launches, CA, rerun/offline mode and failed-candidate rollback; no real login or service activation |
| Bash/Python syntax, whitespace and OpenSpec strict validation | Passed | `bash -n claude-container.sh`, changed Python AST parsing, `git diff --check`, strict N18 change validation |
| Real authentication and user-service activation | Unavailable / not run | Outside credential-free acceptance; no new real-provider compatibility claim |

The focused budget run measured `memory.max=268435456` and `pids.max=128`.
With 64 partial ClientHellos active, `memory.current=40873984`,
`memory.peak=41353216` and `pids.current=68`. With 64 verified TLS connections,
the values were `memory.current=40644608`, `memory.peak=41353216` and
`pids.current=68`. The count includes controlled upstream server threads and
the exec sampler; these figures are fixture measurements, not a claim about
all future workloads or a substitute for enforced budgets.

Development checks exposed and corrected a race where shutdown could terminate
the timeout leader before its TERM-ignoring exec child. The final wrapper owns
and terminates the probe process group before reaping its leader; the regression
passes timeout and signal cases without a surviving active client. An initial
direct setup-unit run used `/tmp`, whose writable ancestors are correctly
rejected by protected-path checks (4 failures and 22 errors). The supported
native disposable setup harness then passed all 50 tests without weakening path
validation. Historical and initial failures are not counted as final passes.
The full network attempt also exposed two legacy cleanup assertions that
required the entire host to have no containers with the egress role label.
Both now inspect mount ownership under the test's private runtime instead;
unrelated sessions are neither treated as test leaks nor removed. The provider
regression includes an unrelated same-role container and verifies it survives.

All 19 production-wrapper network scenarios have passing evidence across the
initial 16 passes and the three isolated reruns. The initial full attempt is
retained as failed, not relabeled as an all-pass run. No required N18 acceptance
scenario remains failed or unavailable. N18 is complete for this checked-out
implementation and measured environment. Existing operator installations must
rerun setup to deploy the protected helper and wrapper together; these tests
did not activate an operator installation. N19 is still separate.


## TLS destination-binding follow-up: 2026-11-07

### Historical observation and component provenance

The local, Git-ignored `todo.md` reports that the production sandbox with the
unchanged `anthropic-api` policy accepted `CONNECT api.anthropic.com:443` followed
by a TLS handshake naming `www.cloudflare.com`. The reported client verified the
Cloudflare certificate and a `HEAD /` with that Host returned HTTP 403. The record
states that no credentials or model requests were used. This is reported
historical evidence of a shared-endpoint name mismatch, not proof of arbitrary
application-content access. Exact proxy/image/guard identities, resolved address,
client versions and an independently replayable transcript were not recorded in
that observation; they must not be inferred from other validation runs.

During the subsequent exploration, an in-memory component check generated a
517-byte ClientHello with Cloudflare SNI and observed it forwarded unchanged by
production `Proxy.tunnel`/bridge under Anthropic CONNECT, with the upstream
connection replaced by instrumentation. An 18-byte non-TLS payload also passed.
That check used no external network and established neither successful TLS
certificate verification nor production guard/rootless acceptance.

The revised implementation introduces mandatory `tls-clienthello-sni-v1`
inspection. Its measured results are recorded separately below; historical
transport/login/refresh passes do not certify the new proxy. No real credential,
login, token refresh or model request is authorized by the synthetic checks.


### Revised destination-binding acceptance

Measured on 2026-11-07 using the same-host Unix rootless Podman service, server
4.9.3 / Netavark, WSL `6.6.87.2-microsoft-standard-WSL2` x86_64 and usable
Landlock ABI 3. OCI seccomp and the additive guard filter remain active; no
privilege, namespace, SELinux or CA-verification relaxation was introduced.
The outer Podman client reports 4.3.1. Runtime image
`a96af83c8276d42d029a501ecfc6f886c446055ed5157a934cfeac486d9b0ef9`
reports Claude 2.1.316, Node v22.23.4 and Python 3.11.2.

| Identity | Measured value |
| --- | --- |
| Production proxy image | `16604a740686c469ede6695bda2c3dc6ded5f9203979b5060acc383dcb0ef12f` |
| Required proxy enforcement | `tls-clienthello-sni-v1` |
| Production guard SHA-256 | `6dc1ab5478118317f1228b21c04b7dfe95de7a5472e4fb811bb0a53ba0342a2c` |
| Guard revision / transport | `abi3-seccomp-mux-v1` / mux v1 |
| Toolchain image | `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c` |
| Controlled policy revision / SHA-256 | `anthropic-2026-11-06-v1` / `45f645648427d15e9616b4212b168ed08a5d7347a5c10e2c3a4d5bcde8c4e1f5` |
| Final guarded TLS fixture image | `dc8677433382ba816bf2503112abab81ebdc1ca7e185392edae4cb07e592d77f` |
| Final API/account fixture image | `6dc3655fece722b4565a34aad166c349b3b5a07c4e8eb13d523f57e6cbae9afc` |

Known retired ESNI/ECH name-hiding extensions (`0xffce`, `0xff02`,
`0xff03`, `0xff04`) are also rejected; the final parser and controlled production
regressions cover these alongside RFC 9849 ECH/GREASE. Their draft protocol
references are recorded in `network/README.md`.

The fixtures extend the unchanged packaged policy with `controlled-test`,
`controlled-api` and `controlled-account` entries. The latter two retain the
respective required hostname/port inventories and add explicit test-only loopback
addresses. Test-image resolution sends these exact names to the controlled TLS
listener. Production DNS/address checks still execute; packaged base profiles
continue to reject local exceptions. Synthetic certificates cover both shared
names and the API/account inventories. These fixtures are not public-provider
authentication evidence or operator policy changes.

| Check / command | Result | Evidence and limits |
| --- | --- | --- |
| `python3 -m unittest discover -s tests -p 'test_tls*.py' -v` | Passed: 12 tests | Generated TLS 1.2/1.3 hellos, every input split, record reassembly, normalization, malformed vectors, ECH/GREASE, exact/overflow limits, 500 deterministic mutations; proxy/relay zero-byte rejection, direct mux access, absolute timeout, 64 stalled inspections, budget overflow and channel-death release |
| `python3 -m unittest discover -s tests -p test_mux.py -v` | Passed: 9 tests | Existing framing/state/credit/backpressure, stream isolation, 80 sequential requests, cancellation and channel death |
| `bash tests/run-runtime.sh --network-policy` | Passed: 13 tests | Protected native paths/snapshots plus mandatory manifest enforcement identity, including absent/old/wrong identities |
| `bash tests/run-runtime.sh --setup` | Passed: 50 tests | Protected parser inventory, maintenance/rollback/PTY and synthetic credential-free setup behavior |
| `bash tests/run-runtime.sh --wrapper` | Passed: 56 tests | Engine, invocation/state/CA/delegation, signals and bounded owned cleanup |
| `bash tests/run-runtime.sh --guard` | Passed: 15 tests in 49.355 seconds | Final production parser/proxy image through the static guard and confined relay, shared-address zero-byte rejection, fragmented verified TLS 1.3 with retry, TLS 1.2 session reuse, mixed healthy/rejected/stalled traffic, 80 repeated requests, streaming/long-lived/WebSocket and certificate denial; unchanged IP/IPC enforcement gate |
| `bash tests/run-runtime.sh --network` | Initial run: 15 passed, one timed out in 302.478 seconds | All destination-binding/profile cases passed. The existing offline arguments/stdin/TTY case exceeded its 30-second test deadline under concurrent test load; this attempt is not reported as an all-pass suite |
| `bash tests/run-runtime.sh --network -k guarded_arguments` | Passed: one test in 41.420 seconds | Isolated rerun verifies shared/isolated state, argument/stdin forwarding, exit 37 and TTY; resolves the failed case without weakening deadlines or enforcement |
| `bash tests/run-runtime.sh --network -k tls_destination_binding` | Passed: one test in 58.606 seconds | Final proxy image and final fixture, controlled custom/API/account profiles; exact names and ports, verified TLS 1.2/1.3, fragmented TLS, retry/resumption, absent/malformed/duplicate/conflicting/different SNI, non-TLS, ECH, record/handshake limits, EOF and absolute deadline all exercised, including retired ESNI/ECH codes; every rejected initial input has zero upstream bytes |
| `bash tests/run-runtime.sh --network -k readiness` | Passed: one test in 22.077 seconds | Separate absent TLS enforcement, wrong guard, mux version and policy readiness records all fail before the agent sentinel and clean owned resources |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: two tests in 68.891 seconds | Disposable protected provider setup CA on/off, fresh launcher and reconfiguration; candidate with historical proxy readiness is rejected and previous release stays active; no real login or service activation |
| `bash -n claude-container.sh`, Python AST parsing, `git diff --check`, OpenSpec strict validation | Passed | Shell/Python syntax and artifact consistency; new untracked files also checked for whitespace |
| Real provider login/refresh/model acceptance with revised proxy | Unavailable / not run | Existing historical account results remain separate; no real credentials were read and no model request was sent. Real-key API acceptance remains optional |

Three initial harness launches failed in Podman before tests with
`ContentLength ... Body length 0`; reruns with maintained terminal input started
successfully. An initial direct setup-unit invocation used a read-only HOME and
could not create disposable state; the supported native harness passed. Setup
runtime development also exposed an old prepared proxy rejected by the new
readiness contract and a fixture selector that reused the previous good image;
final tests explicitly select disposable new/old images and verify rejection and
rollback. No operator-owned image tags were replaced to make those tests pass.

### Acceptance scenario map

| Delta scenarios | Evidence |
| --- | --- |
| Authority validation; redirect/target changes | Existing policy, wrapper-network and guarded TLS tests; TLS mismatch assertion in `tests/tls_binding_fixture.py` |
| Matching names/certificates; shared-address mismatch | Verified alternate-name unfiltered control, matching verified tunnels, and zero-byte counter assertions in `tests/tls_binding_fixture.py` through guard and wrapper |
| Missing/ambiguous identity; non-TLS/unverifiable negotiation | `tests/test_tls_client_hello.py`, `tests/test_tls_proxy.py`, and controlled guarded fixture; ECH and GREASE both rejected |
| Agent bypasses relay | `TLSProxyTests.test_direct_mux_rejection_zero_upstream_bytes_and_reuse` executes the production proxy over mux directly; guarded relay/wrapper acceptance is separately recorded above |
| Fragmented/coalesced input | Every-split/parser tests, original-byte proxy echo tests, and verified TLS with record-fragmented ClientHello through the production guard/relay |
| Exhaustion/EOF/deadline; concurrent failures/channel death | Parser exact/over limits, proxy fixed-storage/deadline/cancellation tests, controlled zero-byte rejection and mixed-stream progress, and existing production proxy-death/cleanup checks |
| Old proxy or mismatched readiness | Manifest negatives, four readiness mismatch controls, and setup candidate rollback against a disposable historical-readiness image |
| Sensitive/malicious diagnostic contents | Proxy secret-like SNI rejection tests and existing audit-redaction/log-cap tests; raw hello and rejected SNI never enter production logs |
| Operator reviews guarantees | Wrapper help, setup mode guidance, README, setup/network docs and AGENTS.md distinguish initial TLS binding from encrypted application routing |
| Controlled regression/compatibility matrix | Final guard and controlled API/account wrapper tests above; historical real-provider checks remain labeled separately |
| Historical observation provenance | Historical subsection above preserves reported status and missing metadata; the component upstream stub is not production acceptance |

N15, N16 and N17 are complete for the measured target and this implementation.
N01 sibling rollout remains pending. The checked-out release and candidate image
must be installed together to use this guarantee; existing operator installations
were not activated or changed by these disposable acceptance tests.

### Operator-reported setup and model behavior: 2026-11-07

The operator subsequently reported rerunning setup and asking a model identified
as Opus 5.5 to attempt to escape the sandbox. The model refused the request under
its own safety guardrails. The operator accepted the result and authorized spec
synchronization, change archival and a commit of the implementation.

This is operator-reported setup and model-behavior evidence. A refusal does not
exercise the sandbox boundary or replace the controlled enforcement tests above.
No command transcript, CLI version, installed image/policy/guard identities or
executed bypass attempts were supplied for this manual check, so it does not
establish additional authenticated compatibility or containment results.


### Specification synchronization and archive

The completed change was archived as
`openspec/changes/archive/2026-11-07-bind-provider-tls-destinations/` after all
25 tasks were verified complete. Its `network-egress` delta was merged into the
main specification: six requirements added and one updated, preserving the
existing Purpose and all 17 unrelated requirements. Every delta requirement was
compared against the merged main spec before archiving. Strict validation of
`network-egress` passed, all nine main specs passed ordinary validation, and all
12 TLS parser/proxy tests passed again before the commit.

The global archived-task check passes this change but reports six pre-existing
incomplete tasks in `2026-11-01-align-container-sandboxing` (20/26 complete).
That historical archive is unchanged by this work and is not evidence of
incomplete destination-binding implementation. Other existing main specs retain
warnings about long requirement descriptions.

## Interactive setup implementation: 2026-11-07

The `add-interactive-container-setup` change adds dedicated terminal-only host
preparation, reviewed non-secret preferences and managed launch through protected
versioned releases. See [setup behavior and requirement coverage](setup.md).
Direct wrapper invocation retains its prior environment-based contract.
First-run setup now proposes provider/account as requested; questionnaire tests
accept those defaults and verify that reruns preserve saved offline and
unrestricted choices. This does not change the direct wrapper's offline default.

Finalized on 2026-11-07: all 26 tracked tasks and four planning artifacts are
complete. The 12 setup requirements and updated launch-engine requirement are
synchronized into the durable specifications. All nine main specifications pass
normal validation, with existing nonblocking requirement-length warnings; the
change passed strict validation before archival. The
[archived change](../openspec/changes/archive/2026-11-07-add-interactive-container-setup/)
preserves its schema metadata, design, completed tasks and delta specifications.

| Check | Result | Evidence and limits |
| --- | --- | --- |
| `bash tests/run-runtime.sh --setup` | Passed, 50 synthetic tests | Fake Podman/user-service commands and disposable native state; real PTYs cover early setup, choices/cancellation, saved reruns, help, launch forwarding and signals. Schema/privacy, exact engine/socket replies, recipe acquisition, maintenance scoping, publication/lock rollback and compiler-owned cleanup are covered. Adversarial regressions cover command migration/retirement rollback, every symlink hop, kernel dot-dot semantics, unchanged physical command entries, legacy upgrade and descendants surviving leader exit or pipe closure. |
| `bash tests/run-runtime.sh --setup-runtime` | Passed, 2 real rootless acceptance tests | Fresh provider setup compiles the production guard using the prepared immutable toolchain; new-terminal launch requires no wrapper exports; rerun reuses the guard; offline/unrestricted setup and shell work; intentionally failing update leaves the last working release selected. |
| `bash tests/run-runtime.sh --wrapper` | Passed, 56 regression tests | Existing direct-wrapper defaults, state/CA, exact engine/socket replies, invocation composition, argument/TTY handling and owned exit/signal/cleanup behavior remain intact. The known successful restart-check message changes level without hiding actual errors or changing a nonzero application status. |
| Bash syntax, whitespace and strict change validation | Passed | `bash -n claude-container.sh network/build-guard.sh tests/run-runtime.sh`, `git diff --check`, new-text whitespace inspection and `openspec validate add-interactive-container-setup --strict`. |
| Host CA selection during setup | Passed, real provider off/on | Candidate smoke checks the four existing CA variables, the single read-only `/claude-home/ca/bundle.pem` file, and their absence when disabled; no certificate directory mount or TLS relaxation. |
| Sandbox enforcement readiness | Passed on the measured WSL target | Actual installed wrapper/guard path; Unix socket creation and direct egress denied, connected pair and own-loopback accepted, provider proxy deny path confirmed. Claude `--version` succeeds without a model request. |
| Existing same-host service reuse | Passed | Client-visible `unix:///run/podman/podman.sock`, rootless service reports `/run/user/1000/podman/podman.sock`; bind/build source paths retain true native host paths. No real service settings changed. |
| User smoke acceptance: 2026-11-07 | Passed, user-reported | The user confirms the configured sandbox works as expected: Claude Code can use its tools while direct communication with external hosts is blocked. This manual functional observation is recorded separately from the automated enforcement tests and does not extend their tested destination/transport coverage. |
| Real systemd user socket activation | Unavailable in this run | Accepted/declined/failed/no-manager branches use synthetic commands; the available real service was reused. Setup must obtain its own user confirmation before enabling a real socket. |
| Real account login/reuse through the new wizard | Unavailable in this run | Synthetic login success/failure/cancellation verifies direct terminal inheritance and selected state/policy; real credentials were neither accessed nor imported. Prior manual account evidence below remains separate. |
| Real API-key request | Optional / unavailable | Setup stores no key and performs no automatic paid request; provider/API instructions retain the existing key-forwarding mechanism. Account setup never requires an API key. |
| Full image rebuild/upstream availability | Synthetic orchestration passed; real rebuild not exercised | Real checks reused prepared runtime/proxy/toolchain images and compiled the guard. Exact base acquisition, immutable inspection, missing-image/build errors and no pin substitution are covered with fake engines. |

Environment: kernel `6.6.87.2-microsoft-standard-WSL2`, amd64/x86_64;
rootless Podman client 4.3.1 / server 4.9.3, Netavark; Python 3.11.2; standard
OCI seccomp, measured SELinux/AppArmor-disabled target. No policy is disabled by
setup. Runtime image ID:
`a96af83c8276d42d029a501ecfc6f886c446055ed5157a934cfeac486d9b0ef9`;
proxy: `2f725558923e421a4dd309f71c09f9147367801b6155e5066889395cde669d29`;
toolchain: `0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c`.
Tests run with container-provided Python and native Podman volume paths because
the coding container's home is read-only or has unsuitable protected ancestors.
No prerequisite/path/privacy check is relaxed for the test environment. Only
setup-owned temporary containers, releases, tags and volumes are cleaned; user
state, existing images and real service settings are preserved.

User-reported setup failure correction: the installation root previously reused
the credential-directory validator and rejected an otherwise protected existing
caller-owned 0755 directory after maintenance consent. Installation-root checks
now require caller ownership/access and protected ancestors, accept 0755 without
chmod, and diagnose invalid existing roots during preflight. Missing roots and
command parents are created privately. Credential/state/release privacy remains
unchanged. The setup plan and completion output show an exact shell-quoted PATH
export and shell-startup-file guidance when the command directory is absent.

Podman diagnostic correction: the attached client's known successful restart
check is relayed at INFO, with its timestamp/message intact. Tests cover terminal
plain/ANSI formatting, nonterminal `time=... level=... msg=...` formatting, every
chunk boundary, unterminated and binary data, ordinary newline-free prompts and
genuine errors. The adapter never changes global Podman log level or application
status; its FIFO/client cleanup shares the existing session deadline. Restricted
preflight validates the optional installed helper's protected path. Real WSL
acceptance checks that the client's actual restart-check output is informational.

Adversarial review corrections: command relocation now retires the previous
owned dispatcher after successful publication, with rollback on retirement
failure. The dispatcher supplies its actual entry path to the launch helper;
every symlink entry is traced with kernel dot-dot semantics and checked against
writable mounts. Path aliases referring to the same physical command entry are
not retired; distinct directory entries remain separate even for hardlinks.
Recognized legacy commands are atomically upgraded, and unidentified legacy
normal launches fail closed. Unit regressions exercise old/new paths, copied and
symlinked entry points, legacy upgrade and publication/retirement failure. Real
unrestricted setup also relocates the command and launches through the new path.

Setup timeout cleanup no longer returns solely because the group leader has
exited. It signals the owned process group and finishes remaining descendants
even if they close captured pipes without exiting. Two isolated Linux-subreaper
regressions verify termination and collection after leader exit, including a
TERM handler that closes stdout/stderr while the descendant keeps running. Repro
children are reaped by their test helper; no real credentials or services are used.


## Enforced WSL ABI-3 implementation: 2026-11-07

The current implementation replaces the earlier restricted-startup hold with
mandatory platform, protected-asset and in-container checks. The historical
sections below describe superseded candidates and their failures; they are not
current startup requirements. No kernel upgrade is required.

| Support key | Verified target / behavior |
| --- | --- |
| Kernel / architecture | 6.6.87.2-microsoft-standard-WSL2, x86_64 (engine reports amd64) |
| Landlock / guard | ABI 3; MAKE_SOCK/REFER plus inherited additive native seccomp |
| Engine / backend | Rootless Podman client 4.3.1, server 4.9.3, Netavark, explicit same-host Unix service |
| Runtime policy | Standard OCI seccomp active before bootstrap; SELinux/AppArmor disabled in the measured environment; no policy disabled by the wrapper |
| Storage | Protected native installation/state/transport; native and Windows v9fs workspaces tested for ordinary file persistence |
| Guard artifact | Static revision abi3-seccomp-mux-v1, filter native-x86_64-v1, transport v1 |
| SHA-256 | `6dc1ab5478118317f1228b21c04b7dfe95de7a5472e4fb811bb0a53ba0342a2c` with the recorded immutable GCC/musl toolchain |
| Other platforms / policies | Refused pending independent evidence; no automatic unrestricted fallback, upgrade, relabel or privilege addition |

The final guard suite passes **15 tests** with the production artifact and
separately linked component instrumentation. Repeated production builds match;
there are no interpreter/dynamic segments or mock runtime hooks. Tests use
synthetic state, certificates, services and keys, with no real authentication or
external model requests. Guard stdio rejects sockets, namespace/process and
anonymous-inode handles and O_PATH capabilities; unrelated FDs close before
preparation. Existing OCI seccomp must already be active.

| Check / command | Result | Evidence and limits |
| --- | --- | --- |
| `bash tests/run-runtime.sh --guard` | Passed: 15 tests | Production kernel enforcement, component setup failures, descriptor hygiene, static packaging and reproducibility; no mocked pass counts as kernel containment |
| IP/DNS/UDP/host bypasses behind production guard | Passed | IPv4/IPv6, host aliases, LAN/metadata, external DNS/QUIC datagrams and unapproved resolution fail; own TCP/UDP loopback succeeds |
| Existing/late Unix services and aliases | Passed | Unguarded network=none control reaches stream/datagram/seqpacket services; guard denies those types across workspace, parent/worktree, shared state and isolated-home binds, including symlink/hardlink aliases and late arrivals |
| Connected-pair and filesystem behavior | Passed | Stream/seqpacket pairs cannot retarget or listen; private naming and same-session FD transfer work; publication/link/rename on host binds fails; ordinary file REFER and Git/worktree operations work |
| Other bypass paths | Passed | VSOCK creation succeeds in the unguarded control and fails under the filter; other socket families, compat int-0x80, x32, io_uring and pidfd_getfd are denied; threads/exec retain confinement, later allow filters cannot weaken it, and namespace/mount attempts do not escape |
| `python3 -m unittest discover -s tests -p test_mux.py -v` | Passed: 9 tests | 64 concurrent streams, 80 sequential requests, bounded credit/backpressure, other-stream progress, malformed/version/ID/state/length/credit fuzz cases, cancellation and channel death |
| Guarded multiplexed TLS | Passed | 80 sequential HTTPS requests, eight concurrent streams, payload exceeding 1 MiB, 15-second streaming and WebSocket upgrade/frame transfer through the sole preconnected channel; bad certificates and unapproved destinations fail |
| `bash tests/run-runtime.sh --network-policy` | Passed: 12 tests | Exact authorities, public/private/mixed/rebinding address cases, no second DNS lookup, protected paths/aliases, static digest, reserved mount targets, immutable snapshots/manifests and redacted logs |
| `bash tests/run-runtime.sh --network` | Passed: 14 tests in 229.775 seconds, plus the added delegation-grid case separately | Real production-wrapper offline/provider, both state modes, empty/spaced argv, stdin, TTY, exit 37, CA off/on, CLI native/YOLO modes, owned concurrency/interruption, bootstrap failure after proxy setup, readiness identity mismatch, proxy death, stalled cleanup and Windows workspace persistence |
| Restricted delegation grid | Passed | Exact opt-in rejected in both modes/state/shell/YOLO combinations; non-exact values disable delegation, invalid disabled overrides are ignored and the launch endpoint stays host-side |
| Actual Claude tool execution | Passed with synthetic API | Installed Claude 2.1.316 consumes a controlled Messages SSE tool response and runs its real Bash tool in both state modes; the tool verifies Unix denial and writes the expected sentinel; no real provider authentication/model inference is claimed |
| `bash tests/run-runtime.sh --wrapper` | Passed: 55 tests | Existing engine, state/privacy, invocation, worktree, delegation, maintenance and bounded signal/cleanup regressions; targeted CA regression also rerun after the isolated-parent fix |
| `bash tests/run-runtime.sh` | Passed: 13 tests in 204.275 seconds | Existing unrestricted runtime/state/CA/delegation/worktree/image-context and lifecycle regressions |
| Real account request with existing OAuth credentials | Passed, operator-reported | On 2026-11-07 the protected provider/account invocation returned ACCOUNT_PROFILE_OK in stream-json output and exit 0; see the manual evidence below |
| Optional real-key API authentication | Unavailable, non-blocking | Support and synthetic integration coverage remain implemented. Original check 6.4 is now optional by operator decision; no real-key request is claimed as passed |
| Fresh account login and credential reuse | Passed, operator-reported | A fresh isolated state completed auth login --claudeai with Login successful and exit 0; a separate request returned ACCOUNT_LOGIN_OK, success, no API error and exit 0 |
| Account token refresh | Passed, operator-reported | After the recorded token expired, a request returned ACCOUNT_REFRESH_OK, success, no API error and exit 0; expiry advanced from 09:16:05.307 to 18:54:31.676 UTC on 2026-11-07 without another login |
| Internal sandbox compatibility | Unavailable | The synthetic real Bash-tool test retains outer confinement and native permission bypass; it does not establish a successful Claude internal-sandbox operation |

Policy/session readiness now binds policy revision, bootstrap digest and protocol
version. The agent sees no policy/log/manifest or proxy administration mount;
FD 3 is present only in the confined relay branch and closed before application
exec. Each session has private PID/IPC/network namespaces and a fixed private
XDG_RUNTIME_DIR. Actual mountinfo validation rejects nested host directories
inside private IPC roots, allowing only the verified provider transport and the
engine's regular /run/.containerenv metadata file. Host process/device trees are
not accepted as workspace/state sources.

The isolated CA mount parent is created caller-owned and mode 0700 before engine
setup, preventing subordinate-UID ownership of persistent state; existing paths
are validated without recursive permission repair or credential copying.

The synthetic SSE fixture follows the documented [Messages streaming event
flow](https://platform.claude.com/docs/en/build-with-claude/streaming), reviewed
2026-11-07. It supplies only fixed synthetic responses, never records request
bodies/prompts/headers, and confirms tool success through an actual filesystem
sentinel rather than CLI exit status or final response text alone.


### Operator-reported account validation: 2026-11-07

The operator ran the protected wrapper with provider mode and the
`anthropic-account` profile, unsetting ANTHROPIC_API_KEY, CLAUDE_CONFIG_DIR and
CLAUDE_CONTAINER_STATE_DIR to use the existing shared HOME/.claude credentials.
The command requested ACCOUNT_PROFILE_OK with print, stream-json, verbose and
partial-message output, a one-turn limit and stdin redirected from /dev/null.
The reported assistant response contained exactly ACCOUNT_PROFILE_OK; the
operator separately reported wrapper exit code 0. The response identified model
`claude-sonnet-5-5` and timestamp 2026-11-07T00:59:26.711Z. The preceding installed
wrapper version check reported Claude 2.1.316 and enforced guard ABI 3 with digest
`6dc1ab5478118317f1228b21c04b7dfe95de7a5472e4fb811bb0a53ba0342a2c`.

The selected policy was `anthropic-2026-11-06-v1`, digest
`02b7baf6078da290da3494d206963388e39367c1b82d7710c9f6679aabe4fbca`.
No policy destinations, TLS settings, privileges or runtime security controls
were broadened for this check. This is operator-reported evidence of a real
account-authenticated request and stream-json response through the restricted
wrapper. It does not establish fresh browser login/callback behavior, token
refresh, sustained streaming or account-specific WebSockets. No raw credential,
login URL, request/session identifier or response transcript is recorded here.
The policy file's tested metadata remains its original dated inventory snapshot;
this later partial acceptance does not change its revision or digest.

On 2026-11-07 the operator decided that unavailable API keys must not leave
API-key support pending or block this change. API-key support and mandatory
synthetic coverage stay implemented; original real-key check 6.4 is retained as
an optional manual check, unavailable and not passed. It is excluded from the
mandatory task count rather than checked off without a real request. There are
39/39 mandatory tasks complete after the account refresh evidence below.
Existing-credential access, fresh isolated login, saved-credential reuse and
automatic refresh after expiry have passed in the reported HTTPS/SSE account
flow. Real-provider claims remain limited to those observations; optional
real-key API acceptance is still unavailable and not passed.


### Operator-reported fresh account login and reuse: 2026-11-07

Following the existing-credential check, the operator selected a new private
CLAUDE_CONTAINER_STATE_DIR created with mktemp, leaving the original HOME/.claude
credentials untouched locally. In provider mode with the anthropic-account
profile and no API key/config override, `auth login --claudeai` reported
`Login successful` and login_exit_code=0. The CLI displayed a manual-code prompt;
the exact browser callback versus pasted-code completion path was not reported,
so neither mechanism is independently claimed verified.

A separate wrapper invocation in the same isolated state requested
ACCOUNT_LOGIN_OK with a one-turn limit, stream-json output and stdin from
/dev/null. The operator reported subtype=success, api_error_status=null,
result=ACCOUNT_LOGIN_OK and request_exit_code=0. This verifies a fresh sign-in
and saved-credential use in a new container session. It does not demonstrate
refresh of an expired token by itself; the later renewal evidence is recorded
below. Callback mechanisms not observed directly remain unverified. No token, authorization
code, login URL or full response transcript is stored in this record.


### Operator-reported pre-refresh expiry baseline: 2026-11-07

After the fresh isolated login and ACCOUNT_LOGIN_OK request, the operator ran a
metadata-only check in the same test state. Reported now_utc was
2026-11-07T01:20:57.795473+00:00 and expires_at_utc was
2026-11-07T09:16:05.307000+00:00. Only these timestamps were shared; no tokens or
credential-file contents were supplied. The renewal check is planned for
2026-11-07T09:17:00Z or later, reusing this isolated state without another login
or manual credential/clock changes. Success requires a real request with
ACCOUNT_REFRESH_OK and exit 0 plus an advanced expiry timestamp. This baseline
alone was not refresh evidence; it is paired with the subsequent result below.


### Operator-reported automatic account refresh: 2026-11-07

The operator retained the same fresh isolated test state and followed the
request-after-expiry procedure without another login or manual credential/clock
changes. A final pre-request metadata check reported:

| Observation | UTC timestamp / result |
| --- | --- |
| Clock before request | 2026-11-07T10:53:14.601241+00:00 |
| Expiry before request | 2026-11-07T09:16:05.307000+00:00 |
| Real account response | subtype=success, api_error_status=null, result=ACCOUNT_REFRESH_OK |
| Wrapper result | refresh_exit_code=0 |
| Clock after request | 2026-11-07T10:56:09.331663+00:00 |
| Persisted expiry after request | 2026-11-07T18:54:31.676000+00:00 |

The old expiry was already in the past before the request. A successful
account-authenticated request plus the advanced persisted expiry meets the
manual automatic-renewal criterion; success with an otherwise still-valid token
alone would not have done so. This completes mandatory account acceptance 6.5
for the observed login, saved-credential and refresh flow under provider mode.
The source is operator-reported sanitized output, not an agent inspection of real
credentials. No token, authorization code, request/session identifier or raw
transcript is recorded or added to automated fixtures.

Evidence scope remains explicit: browser login is performed outside the
container; the CLI offered a manual-code prompt and completed sign-in, while the
exact callback/pasted-code mechanism was not independently observed. Real account
requests used the configured stream-json/partial-message output. Sustained
streaming, large payloads and WebSocket transport are covered by the controlled
production guard/proxy fixtures, not claimed as real authenticated WebSocket or
long-lived account-service checks. Unexercised SSO/cloud/optional feature flows
remain unverified. The optional real-key API check remains unavailable and
non-blocking by the operator's decision. No endpoint exception, privilege,
security-policy weakening or default-policy revision was needed.


### Specification synchronization and archive: 2026-11-07

All 39 mandatory tasks and all planning artifacts were complete before archival.
The four delta capabilities were compared to the main specs, then synchronized:
network-egress was created with 18 requirements; container-isolation,
container-launcher and container-podman-access each received three modified
requirements. Existing titles, Purpose sections, unrelated requirements and
scenarios were preserved. Post-sync comparison verified that every delta was
fully applied before moving the change, including the new capability.

Main-spec validation passed for all eight capabilities, with non-blocking
length warnings for several full requirement descriptions; approved normative
content was retained. Strict change validation passed before archival. The
archive is [2026-11-07-add-enforced-network-egress](../openspec/changes/archive/2026-11-07-add-enforced-network-egress/),
with its .openspec.yaml metadata preserved. The optional real-key API check
remains unavailable/non-blocking and is not reported as passed.

Finalization regression: `python3 -m unittest discover -s tests -p test_wrapper.py -v`
passed all 55 tests in 136.465 seconds. Bash syntax and whitespace checks passed.
No real credentials or model calls were used for this finalization run; prior
rootless and operator-reported authentication evidence remains scoped above.


## Native bootstrap component: 2026-11-06

Tasks 1.1 and 1.5 of the revised `add-enforced-network-egress` plan now supply the
portable IPC contract and isolated native bootstrap. Restricted wrapper startup
is still held closed; bootstrap packaging/integration and full acceptance remain
unchecked. No new kernel or changed seccomp/SELinux policy was introduced.

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Static guard component suite | Passed | `bash tests/run-runtime.sh --guard`: eight tests pass in 2.682 seconds, using disposable native state, no credentials and no model calls |
| Real kernel rejection | Passed negative check | Production executable reports `Landlock ABI 3 is unsupported; require ABI >= 9` and exits 78 without executing the application sentinel |
| Hermetic executable and reproducibility | Passed | ELF has no interpreter/dynamic segment or mock configuration names; two builds with the same immutable toolchain produce identical SHA-256 `1ed6fb7ad6668434810a1402c152aa32c8752cfa947383c3d2a54b6cce5c3544`; revision `landlock-ipc-v1` |
| Preparation failures | Passed component checks | A separately linked mock executable exercises ABI 3/8, unavailable query, failed descriptor cleanup, wrong private filesystem, privilege setup failure, ruleset/rule rejection and enforcement failure; all stop before the application sentinel |
| Descriptor/argument/runtime handling | Passed component checks | Extra descriptors close; socket stdio is rejected; empty/spaced argv, stdin and exit 37 are preserved; private runtime symlinks/unsafe modes and proxy ownership/permissions/read-only failures are rejected |
| Pre-policy hooks | Passed negative check | Production static guard still rejects real ABI 3 under LD_PRELOAD, LD_AUDIT, BASH_ENV, ENV, PYTHONSTARTUP, NODE_OPTIONS and mock-named environment settings; initialization sentinel remains absent |
| Real supported-kernel IPC enforcement | Unavailable | Task 1.6 requires an operator-provided ABI >= 9 rootless environment. Current host and its containers share ABI 3; test mocks do not implement enforcement |
| Complete IP/IPC/alternate-transport release gate | Incomplete | Tasks 1.6–1.8 and 1.4 remain unchecked. No bootstrap activation or supported restricted session is claimed |
| Wrapper regressions | Passed | `python3 -m unittest discover -s tests -p test_wrapper.py -v`: all 55 tests pass in 134.698 seconds, including the retained restricted-startup hold |
| Runtime runner smoke | Passed | `bash tests/run-runtime.sh -k image_smoke`: one real-rootless test passes in 4.104 seconds across both state modes; the new optional guard-runner branch does not change ordinary runner behavior |
| Structural checks | Passed | Bash syntax, whitespace including new source/component files, and strict OpenSpec change validation pass |

The rootless toolchain uses Alpine base digest
`sha256:c64c687cbea9300178b30c95835354e34c4e4febc4badfe27102879de0483b5e`,
GCC `13.2.1_git20240309-r1`, musl-dev `1.2.5-r4`, and binutils `2.42-r1`.
Its immutable image ID is
`0b69ba43c894c4599fcfc0fa7b5e3c150ec26fcf7a2690e3c83708688ff9402c`.
Build logs contain the existing ambient-capability warnings but succeed without
adding privileges or changing policy. Compilation runs without networking after
operator preparation of that toolchain. Reproducibility above applies to this
exact toolchain image; it does not assert unchanged future package repositories.
Test binaries and the runner's volume are removed; no host compiler is installed.

## IPC design blocker and restricted startup hold: 2026-11-06

Implementation of `add-enforced-network-egress` is paused. A real-rootless
candidate-wrapper probe reached a controlled TLS service outside an offline
agent through a filesystem Unix socket in its writable workspace. The agent had
only `lo`, no delegated Podman socket, and no authorized egress relay. The output
was `UNAPPROVED_HOST_IPC_REACHED_WITH_ONLY_LOOPBACK`; the probe completed in
4.701 seconds. The same exposure can exist in shared application state. This
invalidates the full isolation claim despite the earlier passing IP checks.

The reproducible credential-free harness now includes this IPC case:
`bash tests/run-runtime.sh --network-feasibility`. A green harness result means
that both the IP properties and the **IPC bypass** were reproduced; it does not
mean the security gate passed. Its explicit `DESIGN BLOCKER` line identifies the
unapproved workspace socket crossing a namespace with only loopback attached.
Fixtures use only disposable certificates, controlled endpoints and owned
containers/native volumes. No real credentials, login, or model requests are used.

Restricted startup is now held closed before image/state operations, including
the otherwise measured backend/version. There is no fallback or bypass flag.
Unrestricted mode must be selected explicitly and retains the existing broader
network behavior. The prospective `--network` acceptance cases remain incomplete
and blocked by this hold; their historical candidate results below do not apply
to a released restricted feature. The dedicated `restricted_startup_hold` case
checks that no agent/state is created. Do not remove the hold or mark tasks 1.4
and 7.1 complete until the IPC design and enforcement evidence are reviewed.

A one-time socket-file scan is insufficient as the complete solution: host
applications can create new sockets after startup in shared writable trees.
The current plan also forbids custom seccomp profiles and preserves live host
workspace/shared-state binds. A kernel-enforced IPC boundary or a different bind
strategy needs an explicit design/compatibility decision; no exception to that
scope has been silently accepted. Planning artifacts remain the original proposed
design pending that decision.

| Work completed before the hold | Result | Limits |
| --- | --- | --- |
| Wrapper regressions | Passed | 54 tests in 137.568 seconds, including explicit maintenance authorization and network preflight failures; these regressions explicitly select unrestricted mode |
| Existing rootless acceptance | Passed | 13 tests in 157.484 seconds: identity/state/privacy, tmpfs, CA, worktrees, delegation/child binds, lifecycle, concurrency, image tools and build filtering |
| Trusted policy/proxy tests | Passed | 12 tests, most recent run 0.448 seconds, including malformed/duplicate policies, protected paths/aliases/snapshots, exact authorities, address rejection, connection without second DNS lookup, oversized headers and log redaction |
| Candidate network lifecycle | Passed for measured IP properties | Five cases in 70.413 seconds: concurrent different policies/shared and isolated state, owned signal cleanup, failed/interrupted creates for agent/proxy, offline default, real proxy TLS/streaming/WebSocket/CA and proxy death; this predates the IPC blocker and is insufficient for full enforcement |
| Candidate stalled proxy removal | Passed | One case in 18.016 seconds: stalled TERM-ignoring engine shim remains bounded, status 37 preserved, remaining proxy ID reported and then removed by fixture cleanup |
| Candidate redirect/port/host rejection | Passed | Targeted production-proxy case in 14.371 seconds after special-address hardening: redirects, deceptive suffix, alternate port, direct IP authority and admin-style HTTP request denied; token-bearing redirect target absent from protected diagnostics |
| Candidate native CLI modes | Passed for startup only | One case in 31.167 seconds: six real Claude 2.1.316 version invocations under ordinary/native-bypass/YOLO modes across shared/isolated state, plus effective optional-traffic variables; no authenticated behavior is claimed |
| Authenticated API/account login, refresh, transports | Unavailable | No real credentials or model calls authorized/used; these remain separate acceptance tasks |

The date/versioned policy inventory and optional-traffic settings were checked
against official standalone CLI documentation and byte presence in the installed
native Claude 2.1.316 binary (ordinary text-only search skips the binary).
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_AUTOUPDATER`,
`DISABLE_TELEMETRY`, `DISABLE_ERROR_REPORTING`,
`ENABLE_CLAUDEAI_MCP_SERVERS`, and `CLAUDE_CODE_DISABLE_ARTIFACT` were present.
Environment and version checks do not establish real telemetry/login/refresh
compatibility. API and account inventories remain unverified for authentication.

## Network topology feasibility: 2026-11-06

This is a feasibility gate for `add-enforced-network-egress`, not production
wrapper enforcement or authenticated provider compatibility. The unchanged image
reports Claude Code 2.1.316, Node 22.23.4 and Python 3.11.2. The environment is
Linux 6.6.87.2-microsoft-standard-WSL2, Podman client 4.3.1/server 4.9.3,
rootless Netavark, seccomp enabled with its standard profile, SELinux disabled.

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Unix proxy topology | Passed | `bash tests/run-runtime.sh --network-feasibility`: one test passes in 5.768 seconds with two concurrent sessions; controlled HTTPS bodies and certificate/hostname verification traverse a loopback relay and a read-only socket-directory bind |
| Direct bypass attempts | Passed | Each agent has only `lo`; direct IPv4/IPv6 TCP, host aliases, private/LAN and metadata addresses fail; external DNS/UDP and QUIC-port datagrams fail; own loopback is a positive control |
| Socket and session ownership | Passed | Caller UID/GID with keep-id can connect but cannot unlink the read-only socket; distinct session tokens are returned; disposable fixtures, containers and runner volume are removed |
| Security policy | Passed in available environment | No privileges, extra capabilities, custom seccomp, relabels, disabled labels, or host networking added; this does not establish SELinux-enforcing support |
| Same-host service bind paths | Passed | Runner uses native disposable volume paths identically on host and client, with explicit Unix service access |
| Local-engine client and SELinux-enforcing host | Unavailable | Current container supplies the same-host service client; no independently validated local rootless/SELinux-enforcing environment is available |
| Provider authentication and production proxy | Unavailable | Fixture proxy has a test-only exact loopback upstream; it is not the production policy implementation and uses no real credentials or model requests |

The initial candidate support matrix is limited to the measured same-host Unix
service/rootless Netavark/server 4.9.3 topology. Other backends/versions and local
client paths remain unverified. Runtime integration must not silently substitute
an internal bridge, privileges, or unrestricted networking for a failed gate.

## Delegated-socket carriage return rejection: 2026-11-01

Checks for `reject-delegated-socket-carriage-returns` run as UID/GID 1000
on Linux 6.6.87.2-microsoft-standard-WSL2, using Python 3.11.2, Bash 5.2.15,
GNU coreutils timeout 9.1, OpenSpec 1.16.0, Podman client 4.3.1 and server
4.9.3. The same-host Unix service reports Linux rootless operation. The
existing runtime image reports Claude Code 2.1.316, OpenSpec 1.16.0,
Python 3.11.2, Bubblewrap 0.8.0, and GNU nano 7.2.

| Check | Result | Evidence and limits |
| --- | --- | --- |
| CR rejection | Passed | Targeted synthetic tests reject CRLF, a final CR without LF, leading CR, CR within the rootless field, CR between fields, and CR inside a host path; ordinary startup and explicit build both fail with an endpoint-specific invalid-response error before image inspection, build, or creation |
| Response compatibility and error precedence | Passed | Existing exact-record tests retain acceptance of zero/one final LF and exact socket mount paths containing spaces, and reject additional records; new tests retain query-failure diagnostics after CR-containing stdout and confirm disabled delegation skips the separate socket query |
| Full synthetic suite | Passed | `python3 -m unittest discover -s tests -p test_wrapper.py -v`: 52 tests pass in 156.464 seconds |
| Full rootless runtime suite | Passed | `bash tests/run-runtime.sh`: 13 tests pass in 171.075 seconds, covering both state modes, signals, build filtering, CA, child binds, delegation, concurrency, temporary mounts, image tools, persistence, CLI, worktrees, and runtime permissions; runner cleanup succeeds |
| Syntax, documentation, and contract | Passed | `bash -n claude-container.sh`, `git diff --check`, wrapper help, and `openspec validate reject-delegated-socket-carriage-returns --strict` pass; README and help explicitly document delegated-response CR rejection |
| Authenticated internal sandbox | Unavailable | No credentials or model calls are used; image tool versions and wrapper/runtime checks do not establish authenticated internal sandbox compatibility |

The completed change is archived at
`openspec/changes/archive/2026-11-01-reject-delegated-socket-carriage-returns/`
with all six tasks complete. The delegation-response delta was synchronized
into `container-podman-access`, preserving its existing scenarios and unrelated
content. All seven main specifications passed `openspec validate --specs --strict`.
The named-change validation above predates archive; use main-spec validation
after archive. `todo.md` remains excluded by `.gitignore` and is not committed.

## Session lifecycle and response hardening: 2026-11-01

The completed change is archived at
`openspec/changes/archive/2026-11-01-harden-session-lifecycle-and-engine-responses/`
with all 11 tasks complete. Both delta specifications were synchronized into
the main specifications, and all seven main specifications passed
`openspec validate --specs --strict` before archive. The named-change validation
record below predates archive; use main-spec validation after archive.

Checks for `harden-session-lifecycle-and-engine-responses` use synthetic state,
UID/GID 1000, the existing built runtime image, and the same-host rootless Unix
service. No credentials, login, paid model call, or authenticated internal
sandbox operation is used. The pre-existing user edit to `.gitignore` is retained.
The environment reports Linux 6.6.87.2-microsoft-standard-WSL2, Podman client
4.3.1, server 4.9.3, and host GNU coreutils timeout 9.1.
The image reports Claude Code 2.1.316, OpenSpec 1.16.0, Python 3.11.2,
Bubblewrap 0.8.0, GNU nano 7.2, and Podman client 4.3.1. These version queries
and runtime checks do not establish authenticated internal sandbox compatibility.

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Synthetic shutdown faults | Passed | Targeted regressions cover ignored TERM/INT/HUP, failed/stalled kill/removal (including TERM-ignoring control clients), first-signal status, exit 0/nonzero/125 preservation, no leaked fake clients, and owned temporary cleanup |
| Interrupted creation | Passed | Synchronized interruption before/after CID publication recovers only session-owned identity; a foreign label result is rejected; collision retries and post-publication create failures retain correct status and cleanup |
| Prerequisites and normal duration | Passed | Missing/unsupported GNU timeout is rejected before resources; help works without it; a 21-second build followed by a 21-second session succeeds without a normal-work deadline |
| Initial runtime lifecycle probe | Failed | Podman's default 10-second forced-removal stop wait outlived the control-call deadline; the unrelated-session fixture also needed to close stdin before waiting for shell exit |
| Corrected runtime lifecycle probe | Passed | `bash tests/run-runtime.sh -k bounded_signal`: readiness-synchronized cooperative and ignored TERM/INT/HUP in both state modes pass in 45.497 seconds, including owned-container disappearance and preservation of a concurrent unrelated session; forced removal now sets `--time 0` |
| Exact verification records | Passed | Targeted synthetic tests accept zero/one final LF and reject empty, leading/embedded blank, extra trailing blank, and nonblank records at both query sites; failure after valid stdout remains a query error and all rejected cases gate image/build/create |
| Response-mode composition | Passed | Shared/isolated state, Claude/shell, build/worktree, delegation off/on, endpoint precedence/remapping and host socket paths containing spaces pass targeted checks; disabled delegation performs no separate socket query |
| Full runtime suite | Passed | `bash tests/run-runtime.sh`: all 13 tests pass in 134.869 seconds, including the new signal matrix plus existing image smoke, mounts, state, CA, worktree, delegation, child binds, concurrency, CLI and runtime permissions; fixture resources cleaned up |
| Final synthetic and structural checks | Passed | 50 wrapper tests pass in 130.427 seconds on stable sources, including interruption of collision reconciliation; Bash syntax, whitespace including new planning files, and strict named-change OpenSpec validation pass; the pre-existing `.gitignore` diff is unchanged |

## Runtime defaults hardening: 2026-11-01

The completed change is archived at
`openspec/changes/archive/2026-11-01-harden-container-runtime-defaults/` with
all 16 tasks complete. Its four delta specifications were synchronized into
the main specifications, and all seven main specifications passed
`openspec validate --specs --strict` before archive. The named-change validation
record below predates archive; use main-spec validation after archive.

Checks for `harden-container-runtime-defaults` run as UID/GID 1000 on Linux
6.6.87.2-microsoft-standard-WSL2, with Podman client 4.3.1 and server 4.9.3.
The same-host Unix service is now reachable and reports Linux rootless operation.
This is a later environment than the unavailable-service checks below; historical
results remain unchanged. All new checks use synthetic state and no model calls.

The rebuilt image reports Claude Code 2.1.316, OpenSpec 1.16.0, Python 3.11.2,
Bubblewrap 0.8.0, GNU nano 7.2, and Podman client 4.3.1. These versions were
queried directly from the new image without credentials or an authenticated
sandbox operation. No new internal sandbox compatibility conclusion is claimed.

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Pathless launch endpoints | Passed | Synthetic checks reject pathless/slash-only/relative Unix endpoints before any Podman call with delegation off/on and overrides; help remains side-effect free |
| Disabled delegation environment | Passed | `bash tests/run-runtime.sh -k delegation_clears` builds a disposable image defining `CONTAINER_HOST`; all four state/delegation combinations verify absence when disabled and the fixed endpoint plus rootless service access when enabled; fixture image and volume cleaned up |
| Host endpoint preservation | Passed | Synthetic client asserts its original Unix `CONTAINER_HOST` on every Podman call; runtime runner uses a remapped Unix launch endpoint throughout |
| Explicit temporary mounts | Passed | `bash tests/run-runtime.sh -k explicit_temporary` verifies tmpfs type, flags and exact sizes for `/tmp`, `/run`, `/var/tmp`, sticky modes, writes and direct execution denial on `/tmp` and `/var/tmp`, disappearance across sessions, and `/var/log` write denial in both state modes with delegation off/on |
| Scoped host umask | Passed | Synthetic tests observe caller masks `0022` and `0002` at build/create/start/cleanup calls, while every newly created state directory remains `0700` |
| Measured runtime permissions | Passed | `bash tests/run-runtime.sh -k runtime_permissions` observes container umask `0022`, ordinary file mode `0644`, directory mode `0755`, and private state `0700` in both state modes under host masks `0022` and `0002`; the wrapper does not override container umask |
| Build-context filtering | Passed | `bash tests/run-runtime.sh -k build_context` applies the actual `.containerignore` to a disposable synthetic context; real `COPY .` plus a builder assertion sees only `Containerfile` and `.containerignore`, excluding metadata, credentials/state, environment files, caches, and unrelated nested paths; owned fixture image and runner volume cleaned up |
| Production image build | Passed | `podman build --tag localhost/claude-code:latest --file /mnt/d/Workspace/sandboxes/claude-container/Containerfile /mnt/d/Workspace/sandboxes/claude-container` succeeds with filtering; resulting image ID `e5c37c049ca9d38c9c3165ad91d5b1ea077e55a9adf69071451d49f0210331e0`; the build reports ambient capability warnings but completes without added privileges |
| Integrated synthetic checks | Passed | 37 wrapper tests pass; Bash syntax checks on wrapper, smoke script, and runner, whitespace checks including new files, and strict OpenSpec change validation pass |
| Initial full runtime run | Failed in fixture cleanup | All runtime assertions completed, but removal of the isolated CA fixture raised `PermissionError` because the engine created its mount parent with a mapped root owner; reproduced by the targeted CA test |
| Corrected CA fixture | Passed | The test now creates only its own synthetic isolated CA mount parent as caller-owned `0700`; `bash tests/run-runtime.sh -k ca_mount` passes, including CA-off/on assertions and cleanup in both state modes; production CA handling is unchanged |
| Final full runtime run | Passed | `bash tests/run-runtime.sh`: all 12 tests pass in 102.762 seconds against the rebuilt image, covering filtering, CA, child absolute-path binds, inherited environment removal, concurrent sessions/exit codes, explicit temporary mounts, tools, profile separation, filesystem boundaries/persistence, native CLI modes, worktrees, and measured permissions |

## Archive disposition

On 2026-11-01, the user authorized synchronization, archive, and commit of
`align-container-sandboxing` with the previously reported runtime blockers.
The change is archived at
`openspec/changes/archive/2026-11-01-align-container-sandboxing/` with 20 of 26
tasks complete. Tasks 2.3, 3.4, 4.3, 5.1, 5.4, and 6.2 remain unchecked because
their real-engine acceptance could not be completed. Archiving does not turn
these checks into passes. All four delta specifications were synchronized and
all seven main specifications passed strict validation before archive.

The named-change validation command recorded below was run while the change
was active. After archive, use `openspec validate --specs --strict` to validate
the synchronized main specifications.

## Environment

Checks on 2026-11-01 ran as UID/GID 1000 in a container on Linux
6.6.87.2-microsoft-standard-WSL2, x86_64. The available client is Podman 4.3.1;
Python is 3.11.2 and the planning CLI is OpenSpec 1.16.0. These are the checking
environment's versions, not versions established for a rebuilt runtime image.

The workspace under `/mnt/d` reports mode 0777 even for a newly created private
directory. Synthetic wrapper tests therefore use native executable temporary
storage, not workspace directories, for their fake executable, HOME, sockets,
and credential state. Temporary test resources are removed after each test.

No host service socket was exposed at `/run/podman/podman.sock` or the default
caller runtime path, and no `CONTAINER_HOST` was configured. Local engine
operations fail before usable engine information is returned:

```text
Error: command required for rootless mode with multiple IDs: exec: "newuidmap": executable file not found in $PATH
```

The wrapper preserves the engine diagnostic and exits with an actionable
`cannot query Podman; check the local rootless service` error. Installing helpers
inside this read-only container is not a substitute for a working host engine.
No runtime security policy was relaxed to bypass the unavailable engine.

## Executed checks

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Wrapper behavior suite | Passed | 33 tests using a fake Podman and synthetic state; no real engine or model requests |
| Bash syntax | Passed | `bash -n` on wrapper, image smoke script, and runtime runner |
| Whitespace | Passed | `git diff --check` and whitespace inspection of new files |
| OpenSpec validation | Passed | `openspec validate align-container-sandboxing --strict` |
| Default runtime discovery | Passed as opt-in gating only | Eight runtime checks are skipped unless explicitly enabled; this establishes no runtime behavior |
| Enabled runtime suite | Failed at engine precondition | Eight tests attempted; the missing `newuidmap` error prevents container startup |
| Disposable runtime runner | Failed at engine precondition | `bash tests/run-runtime.sh` exits 125 on its initial engine query, before creating a volume |
| Image inspection | Failed at engine precondition | `podman image exists localhost/claude-code:latest` cannot query the engine |
| Image build, CLI/tool smoke, actual image versions | Unavailable | No working launch engine; the Containerfile was not changed or rebuilt |
| Real boundary, identity, persistence, worktree, CA, and child-bind acceptance | Unavailable | Tests are delivered but have not passed against real containers |
| Real concurrent-session lifecycle and cleanup | Unavailable | Fake-engine lifecycle checks pass; real concurrent containers remain unverified |
| SELinux enforcing acceptance | Unavailable | No suitable engine/environment was exposed |
| Claude internal sandbox tool operation | Unavailable | No authenticated sandbox request was made; no compatibility conclusion is claimed |
| ShellCheck | Unavailable | Not installed; a Podman fallback cannot run without an engine |

## Coverage and remaining acceptance

| Contract | Synthetic evidence | Required real-engine evidence |
| --- | --- | --- |
| `container-launcher`: verified engine and supported contexts | Rootful/non-Linux/empty/malformed/query errors, local and explicit Unix contexts, named/TCP/SSH rejection | Actual engine info and wrapper-in-container launch |
| `container-launcher`: interface and help | Argv including spaces/empty strings, stdin, TTY, shell mode, side-effect-free help | Native Claude help/version in both state modes |
| `container-launcher`: image behavior | Physical script path, absence vs inspection failure, build failure status | Image build/inspect and installed versions |
| `container-launcher`: owned lifecycle | Collisions, stopped/all-name enumeration, decimal suffixes, retry limit, exit 125, INT/TERM/HUP, owned cleanup | Real simultaneous shell sessions and removal |
| `persistent-state` | Shared default/custom directory, isolated home, conflicts, private creation, ownership/access/mode errors, resolved aliases and escaping configuration symlinks | Persisted writes, profile separation, and filesystem ownership |
| `container-podman-access` | Exact opt-in values, selected-endpoint verification/precedence, remapped host paths, inaccessible/invalid sources and results, launch-mode combinations | Same-host Unix service, actual remapped socket, child absolute-path bind |
| `container-isolation` | Read-only/identity/tmpfs argv, no privilege or policy bypass, independent YOLO/socket combinations | External sentinel denial, `/usr` write denial, ephemeral `/tmp`, actual mount flags |
| Existing `workspace-mounts` | Physical cwd, parent selection, spaces, shell/build composition | Shared Git metadata, writable siblings, no inferred outside metadata mount |
| Existing `host-ca-trust` | Disabled/enabled variables, read-only single-file mount, mixed-case controls, missing bundle errors | Read-only mounted bundle and all four CA variables in both state modes |
| Existing `runtime-image` | Existing Containerfile retained | Actual Python/Bubblewrap/nano availability, editor variables, Claude/OpenSpec startup |

Automated tests never use the caller's real Claude configuration or API keys,
perform login, or submit paid model requests. Real runtime tests create synthetic
host HOME and state directories. The same-host runner binds only the test
project, its disposable native volume, and the explicitly delegated host socket;
the socket grants the runner broader host-user authority as documented in README.

The native sandbox check is separate from the automated suites. On an appropriate
authenticated session, run a harmless command through Claude's internal sandbox
and verify both its actual execution and expected output file. Record versions
and diagnostics if it fails. Neither `bwrap --version`, successful basic namespace
probes, a zero CLI status, nor Antigravity's validation record establishes Claude
sandbox compatibility. Retain standard seccomp, SELinux, capabilities, and tmpfs
`noexec` while checking; a policy change requires a separate decision.

## Reproduction

Run the synthetic suite on executable native Linux temporary storage:

```bash
python3 -m unittest discover -s tests -p test_wrapper.py -v
bash -n claude-container.sh tests/image-smoke.sh tests/run-runtime.sh
git diff --check
openspec validate align-container-sandboxing --strict
```

If `/tmp` is `noexec`, set `SANDBOX_TEST_TMPDIR` to a private native Linux directory
that allows execution. The suite deliberately rejects privacy checks performed
on filesystems that report all directories as 0777.

To finish runtime acceptance, expose a reachable same-host rootless Unix service
to this environment and set `CONTAINER_HOST=unix:///absolute/client/socket`, or
run from the host with working local rootless Podman. Keep original host absolute
workspace/build paths. Ensure the selected service's reported host socket path
is bindable by the launch engine. Then build and run:

```bash
./claude-container.sh --container-build --version
bash tests/run-runtime.sh
# Optional: use the image's Python for synthetic tests as well.
bash tests/run-runtime.sh --wrapper
```

The runner creates a disposable native Linux volume, supplies it through
`SANDBOX_TEST_STATE_ROOT` at its real host path, and removes that volume on exit.
It requires an already built image and active rootless API service. For direct
execution on a host with Python, use:

```bash
SANDBOX_RUNTIME_TESTS=1 python3 -m unittest discover -s tests -p test_runtime.py -v
```

Direct host execution uses native temporary state. With a Unix service client
inside a container, use the runner or explicitly provide `SANDBOX_TEST_STATE_ROOT`
backed by private native storage at the same absolute host path. `/tmp` inside
an arbitrary client container is not automatically a valid bind source on the
host. Record actual engine/kernel/architecture, image CLI/OpenSpec versions,
commands, and acceptance results here after a successful run. Do not mark the
outstanding OpenSpec runtime tasks complete based only on synthetic coverage.

## ABI-3 bootstrap revision — 2026-11-06

The revised initial target is Linux 6.6.87.2-microsoft-standard-WSL2 x86_64,
Landlock ABI 3, rootless Podman client 4.3.1/server 4.9.3 with Netavark,
standard OCI seccomp enabled and SELinux disabled. Earlier ABI-9 requirements and
ABI-3 rejection results above describe the superseded prototype. No upgrade is
required by the revised design. Full restricted startup is still held closed.

`bash tests/run-runtime.sh --guard`: **passed, 10 tests**, no skips. Production
revision `abi3-seccomp-mux-v1`, static binary SHA-256
`846834e148a7a999cbde789a4d52d64727b6eb02e7f54121ec2a178089777069`, using the
previously recorded immutable GCC/musl toolchain. Repeated builds matched; the
ELF has no dynamic/interpreter segment or mock environment hooks.

Real production-guard tests passed on that WSL kernel for ABI-3 MAKE_SOCK/REFER
and additive seccomp installation under the standard OCI profile; denied new
Unix/VSOCK/other-family sockets, datagram/raw socket pairs, compat int-0x80,
x32, io_uring setup/enter/register and pidfd_getfd; allowed IPv4/IPv6 creation
without an external route; own loopback; fixed-peer stream/seqpacket pairs,
explicit destination sends and SCM_RIGHTS within those pairs; denied socket
publication/link/rename on the host workspace bind; preserved ordinary file
rename/link and Node/Python subprocesses; and Claude 2.1.316 --version. A separate
real test passed for the sole verified provider preconnection and FD 3 handoff.
This provider test exchanges synthetic bytes, not proxy policy or TLS traffic.

The real test caught and corrected an old minimal-header error: MAKE_SOCK is bit
9, not bit 7 (MAKE_DIR). Shared-header mocks alone had not detected this. Real
kernel checks are mandatory; historical ABI-9 mock passes remain component-only.

A connected pair can bind/autobind a private pathname or abstract name without
becoming a listener or changing its fixed peer. The operator explicitly approved
this narrow allowance after the probe. Tests cover private naming, failed listen,
fixed-peer delivery and denied publication on host binds. New unconnected Unix
sockets and named Unix services remain unavailable, including on private tmpfs.

Mocked component tests separately cover ABI below 3, blocked queries, malformed
rule/metadata preparation, blocked filter installation, descriptor/stdio hygiene,
unsafe runtime paths, pre-policy loader hooks, argv/stdin and exit propagation.
They do not count as kernel enforcement evidence. Full existing/late socket
mount-matrix tests, multiplexed TLS/streaming/WebSocket acceptance, production
wrapper integration/lifecycle and actual authenticated Claude tool execution
remain pending. No credentials or model calls were used.

## Authenticated check commands and evidence limits

These commands describe optional real-key check 6.4 and the account acceptance
procedure for 6.5. Actual account results are recorded above; the commands alone
are not evidence. Repeating them with real credentials requires operator approval. First prepare the
protected installation, guard, images, policy and runtime as described in README.
Run from a disposable workspace and record CLI version, policy revision, marker
output and passed/failed/unavailable status without saving keys, headers, login
URLs or raw session transcripts. Existing API/account endpoint inventories remain
candidates until their actual flows pass. Do not add an exception after a denial
without an explicit reviewed policy revision.

```bash
# Common prepared provider environment (installation and egress_image from README).
export CLAUDE_CONTAINER_NETWORK=provider
export CLAUDE_CONTAINER_NETWORK_POLICY="$installation/agent/policies/default.json"
export CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR="$HOME/.local/state/claude-egress"
export CLAUDE_CONTAINER_EGRESS_IMAGE="$egress_image"

# Optional API check: only with an available key and explicit model-call authorization.
CLAUDE_CONTAINER_NETWORK_PROFILE=anthropic-api \
    "$installation/claude-container.sh" -p 'Reply exactly API_PROFILE_OK. Do not use tools.'

# Account: only after authorizing a real login in the selected state.
env -u ANTHROPIC_API_KEY CLAUDE_CONTAINER_NETWORK_PROFILE=anthropic-account \
    "$installation/claude-container.sh" auth login --claudeai
env -u ANTHROPIC_API_KEY CLAUDE_CONTAINER_NETWORK_PROFILE=anthropic-account \
    "$installation/claude-container.sh" -p 'Reply exactly ACCOUNT_PROFILE_OK. Do not use tools.'
```

The installed 2.1.316 `auth login --help` confirms `--claudeai`, `--console`,
`--email` and `--sso`; do not assume an unverified no-browser option exists.
Host browser steps are outside the boundary. Verify actual container token
exchange, callback/manual-code behavior, streaming and later token refresh;
a successful login or CLI exit alone does not prove refresh. Do not edit/import
real tokens to manufacture a refresh result. Record unavailable/unsupported flows
without weakening TLS, namespaces, seccomp or endpoint policy. SSO hosts require
a separate explicit profile revision and are not automatically enabled.

## Guard test home mount (`sandbox-ref-3`): 2026-11-10

`tests/test_guard.py` started the production guard container with a read-only
root and no writable native home. Claude and Codex never write there for
`--version`, but OpenCode 1.18.3 creates `$HOME/.local` at startup and failed
with `EROFS`. Real launches are unaffected: every wrapper mounts a writable
home. The test now mounts an empty `notmpcopyup` tmpfs at the profile home, as
the wrappers do. A copying tmpfs failed with "no space left on device",
because it copied the npm cache from the Claude image into 64 MiB.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --guard`, before the change | Passed: 19 tests, 1 skipped |
| `bash tests/run-runtime.sh --guard`, after the change | Passed: 19 tests, 1 skipped |

## Setup test for API-key-only profiles (`sandbox-ref-4`): 2026-11-10

At import, `tests/test_setup.py` required an authentication method with
`login_args`. OpenCode's four profiles are API-key methods only, so the shared
test failed with `StopIteration`. `setup/setup.py` already handles such
profiles. The test now works as follows:
- the generic provider method is the profile's first method, which setup
  proposes by default;
- the interactive login method is optional;
- only the login-argument checks are skipped without one.

For Claude and Codex the first method is the login method, so their checks
are unchanged.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --setup` | Passed: 63 tests |
| `python3 -m unittest tests.test_alignment` | Passed |
| Scratch copy whose `account` method uses `credential_env` instead of `login_args`, `--setup` | Passed: 63 tests; the `sandbox-ref-3` version of the test fails there with `StopIteration` |

## Setup test with a nested configuration home (`sandbox-ref-5`): 2026-11-10

Two checks in `tests/test_setup.py` created `<home>/<config_home>` or
`<state>/<config_home>` without its parent directories. That works only for a
single-component `config_home` such as `.claude` or `.codex`. OpenCode's
`config_home` is `.config/opencode`. The test now creates the parent first;
`setup/common.py` already handled nested paths.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --setup` | Passed: 63 tests |
| `python3 -m unittest tests.test_alignment` | Passed |
| OpenCode `--setup` with this test | Passed: 63 tests (before the fix: `FileNotFoundError` in both checks) |

## Optional agent installation files (`sandbox-ref-6`): 2026-11-10

The Pi port showed that the installation manifest covered only the wrapper,
`network/`, `setup/` and `agent/`. Pi's wrapper also reads `.version`, so a
guided-setup installation and the qualification test installation lacked a
file the wrapper needs. The profile schema gains an optional `install.files`
list (at most eight distinct relative paths outside `network/`, `setup/` and
`agent/`, and not the wrapper, `Containerfile` or `.containerignore`).
`setup/common.py` adds them to its manifest, and the qualification identity
binds them as installed code. The shared qualification test installation
also copies `Containerfile`, `.containerignore` and the declared files.
Claude declares none, so its installation is unchanged.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_agent_profile tests.test_alignment` | Passed, including the new invalid `install.files` mutations |
| `bash tests/run-runtime.sh --setup` | Passed: 63 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 18 tests |

## Wrapper-built runtime image (`sandbox-ref-7`): 2026-11-10

The Pi port showed that setup's direct `podman build` of `Containerfile`
cannot build an image the Pi wrapper accepts: the Pi recipe needs the
`PI_VERSION` and `INSTALL_BUN` build arguments and a `build-inputs-hash` label
that only the wrapper computes. The profile gains an optional
`install.runtime_build`, either `recipe` (the default, unchanged) or
`wrapper`. With `wrapper`, setup runs the installed release's
`<wrapper> --container-build` alone, under maintenance, with the candidate
image tag and an explicit `unrestricted` mode that only admits the build-only
operation, then inspects the candidate identity. The toolchain and proxy
images keep the recipe path. Claude declares nothing, so its setup is
unchanged.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_agent_profile tests.test_alignment` | Passed, including the invalid `install.runtime_build` values |
| `bash tests/run-runtime.sh --setup` | Passed: 64 tests, including the recipe and wrapper dispatch |
| `bash tests/run-runtime.sh --qualification` | Passed: 18 tests |

## Setup test with a wrapper-built runtime (`sandbox-ref-8`): 2026-11-10

`test_fresh_and_refresh_builds_keep_previous_runtime_tag` patched
`build_image`, which `prepare_artifacts` no longer calls directly since
`sandbox-ref-7`; it reached the patch only through the default `recipe` path.
With a profile declaring `install.runtime_build: "wrapper"` (Pi) the test
failed. It now patches the runtime dispatch point `build_runtime`, so it holds
for both values. No setup code changed.

| Check | Result |
| --- | --- |
| `bash tests/run-runtime.sh --setup` | Passed: 64 tests |
| Pi `--setup` with this test | The test passes (before the fix: `build_image` called 0 times) |

## Interactive account sign-in from setup (`sandbox-ref-9`): 2026-11-10

`agy` (Antigravity CLI 1.5.3) has no login subcommand: Google sign-in happens
only in its interactive TUI. A profile account method may now declare empty
`login_args`. Setup then offers `Run <name> <method> sign-in now? It opens
<name> interactively; exit it when signed in.`, runs the installed wrapper with
no agent arguments on the terminal in the scratch workspace (plus
`--container-git-worktree` when saved), and reports `verified (<name> <method>
interactive sign-in session exited successfully; no model request tested)`. The
status describes the session exit, not a confirmed sign-in. When the offer is
declined or the session fails, setup prints `Next authentication action:
<command> (sign in inside the interactive session, ...)`. Methods with
arguments and API-key methods are unchanged.

| Check | Result |
| --- | --- |
| `tests/test_agent_profile.py`, `tests/test_alignment.py` | Passed; `[]` is accepted, nine arguments, duplicates and a string are rejected |
| `bash tests/run-runtime.sh --setup` | Passed: 65 tests, including the new empty-`login_args` case; the existing login case now compares the arguments after the wrapper path |
| `bash tests/run-runtime.sh --qualification` | Passed: 18 tests |
| Shared suites | Run unchanged by Codex, OpenCode and Pi `--shared` on adoption |

## Reference propagation tool (`add-reference-propagation`): 2026-11-10

Wave 4 replaces the ad hoc adoption scripts of Wave 3 with `tools/propagate.py`
and `docs/propagation.md`. The tool is reference-only (not a shared file), so no
new tag was created; `network/`, `setup/` and the shared tests are unchanged.

| Check | Result |
| --- | --- |
| `tests/test_propagate.py` | Passed: 5 tests on disposable git repositories (dry run, apply, preconditions, scope, history files, whole-word tags, checklist, same-tag run) |
| `tests/test_alignment.py`, `tests/test_agent_profile.py` | Passed |
| `bash tests/run-runtime.sh --setup` | Passed: 65 tests (unchanged) |
| Replay of `sandbox-ref-8` to `sandbox-ref-9` on clones of Codex, OpenCode and Pi at their pre-adoption commits | The dry-run plan named the same four files and the same documents as the Wave 3 adoptions. After `--apply`, each clone's tree equals its real adoption commit except `docs/validation.md`, which is written by hand; Codex's `tests/test_reference_copy.py` passed |
| Partial scope: Antigravity clone at `51a88d8` (egress only) | `network/agent_profile.py` and `tests/test_agent_profile.py` planned; `setup/setup.py` and `tests/test_setup.py` reported as not adopted |
| Same-tag run (`sandbox-ref-9` to `sandbox-ref-9`) on clones of the four current wrappers | No files and no documents to change |
| `openspec validate add-reference-propagation --strict`, markdownlint on `docs/propagation.md`, `git diff --check` | Valid, no findings, clean |

## Setup smoke diagnostics and shared-state privacy (`sandbox-ref-10`): 2026-11-11

Change `surface-setup-smoke-errors`. An operator's Pi setup failed with only
`Setup command failed (exit 1)`. The cause, `State must be private: ~/.agents`,
became visible only after the smoke stderr was captured by hand. This tag:

- prints a bounded, sanitized stderr excerpt when the smoke launch fails;
- adds the optional profile field `native.private_shared_dirs`;
- makes the private-directory refusal name the reason and the fix.

Claude's profile keeps the default (`false`), so its behavior is unchanged.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_agent_profile tests.test_alignment` | Passed: 21 tests, 1 skipped. Includes the new field (default, `true`/`false`, rejection of `1`, `"true"`, `null` and unknown keys) and the identifier scan of shared files |
| `bash tests/run-runtime.sh --setup` | Passed: 68 tests. New cases: refusal reasons and unchanged modes; shared-directory privacy under both field values, with no engine call; smoke excerpt on failure and on a missing marker; no excerpt on success; hostile and oversized stderr bounded to 5 printable lines of 2048 characters |
| `bash tests/run-runtime.sh --qualification` | Passed: 18 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash -n claude-container.sh` | Passed. ShellCheck (Podman image `koalaman/shellcheck:stable`) reports 11 informational or warning findings. They predate this change: the file is unchanged, and the warnings concern variables assigned through `read` from the session helper |
| `openspec validate surface-setup-smoke-errors --strict`, `git diff --check` | Valid, clean |

Siblings adopt this tag with `tools/propagate.py`. Pi and OpenCode also set
`native.private_shared_dirs: true` in their profiles, because their wrappers
refuse non-private shared directories.

## Operator authenticated session: 2026-11-11

The operator ran an authenticated Claude session in provider mode with the
setup-default profile `anthropic-account`. In the TUI, they asked the model to confirm
that it could use the harness tools and to report the sandbox's access limits.
The model did both, and the operator found the result correct.

This covers an authenticated model request with tool use through the sandbox.
Real-key API (`anthropic-api`) remains unavailable. Full profile verification under the readiness checklist is not
claimed. The checklist also covers streaming and long-lived requests,
WebSockets, sign-in, token reuse and refresh, CA behavior and shell mode.

The five-wrapper parity table was aligned in the same change
(`align-parity-table`). The table extracted from each `docs/network-contract.md`,
from the `| Wrapper |` header to the first blank line, has the same SHA-256 in
all five repositories: `0b3c30bc8b2a5ba4a1623ede2b4da35234198f34e376cdeae4dc499c89c17b63`.

## Lab-host fixes integrated (`sandbox-ref-11`): 2026-11-11

Change `integrate-lab-host-fixes`. It merges the operator branch
`test/podman5-socket-url` (head `aa338f5`, forked at `sandbox-ref-2`) into
`main` (`b633a2d`, `sandbox-ref-10`) and keeps the branch behavior as it is.
The branch commits are:

- `f3fe54f` Podman 5 `unix://` host socket paths;
- `9931840` and `009da2b` Debian packages over verified HTTPS, and the host
  CA as a `build-ca` secret for the runtime and guard toolchain builds;
- `be5617e` qualification on kernels without IPv6;
- `21de614` budgets enforced only for delegated cgroup controllers;
- `0894a3c` and `50a1cd0` the read-only `/run/secrets` mask for agents,
  proxies and qualification gate containers;
- `43a17d7` the agent `/dev` tmpfs, devpts and read-only `/dev/shm`, for
  terminals when the engine forces `/dev` read-only;
- `5ecac3f` and `aa338f5` the lab-host records and the five archived
  changes.

The lab-host evidence for these commits is recorded in the sections that
the branch adds above.

Conflict resolution:

- `openspec/specs/container-setup/spec.md`: the `main` requirements and the
  branch requirement are both kept.
- `setup/setup.py`: `build_runtime()` gains the host CA bundle. A
  recipe-built runtime passes it to the build as the `build-ca` secret, as
  on the branch. A wrapper-built runtime (`install.runtime_build: wrapper`)
  receives setup's trust selection explicitly, through
  `<PREFIX>_TRUST_HOST_CA` and `<PREFIX>_CA_BUNDLE`, instead of inheriting
  the operator's shell values. This is the new `container-setup`
  requirement "Wrapper-built runtime receives host CA trust".
- `tests/test_setup.py`: both sides are kept. Three smoke tests now
  provide the engine controller query that the branch added to the smoke:
  two from the branch, and `test_failed_smoke_shows_a_bounded_sanitized_stderr_excerpt`
  from `main`, which meets the query only after the merge.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 347 tests, 66 skipped. `test_ignored_signals_force_owned_removal` failed once on timing (3.43 s against 3.5 s) before the resolution and passed afterwards; it is a known timing-sensitive test |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 26 tests. It needs `localhost/claude-guard-toolchain:development`, rebuilt from the new recipe (`215f5ffc1023`) |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh --network` | Passed: 20 tests |
| Runtime image build from the new `Containerfile` | Passed: Debian fetched over `https://deb.debian.org`, sources stay HTTPS, no `/tmp/apt-bootstrap-ca.pem`; development tag `localhost/claude-code:integrate-ref-11` (`949298d43d2d`) |
| `bash tests/run-runtime.sh` (`test_runtime.py`, including `image-smoke.sh` in both state modes) with that image | Passed: 16 tests |
| `tests/test_image_pins.py`, `tests/test_alignment.py`, `tests/test_agent_profile.py` | Passed: 5 and 21 tests |
| `bash -n` on `claude-container.sh`, `tests/image-smoke.sh`, `tests/run-runtime.sh`; `git diff --check` | Passed, clean |
| `--container-setup` with refresh approved, operator-run on this host | Passed (operator-reported): the runtime, toolchain and proxy images were rebuilt; `Sandbox qualification: locally-qualified`; `Sandbox: ready`. Runtime `0fb0d09b935d`, toolchain `215f5ffc1023`, proxy `3352c336ff71`. Engine Podman 4.9.3 with runc 1.3.4; controllers `[cpu memory pids]`, so every budget is enforced. The operator also ran a session and found it correct |
| Agent device layout in a session on the new release | Passed: `/dev` is a `rw,nosuid,noexec` tmpfs (64 MiB), `/dev/pts` is devpts, `/dev/shm` and `/run/secrets` are read-only empty tmpfs |
| `--container-setup` on the Rocky Linux 9 lab host, on the tagged state | Passed (operator-reported, 2026-11-11): the runtime, toolchain and proxy images were rebuilt (tag suffix `setup-144be313169b4ddfb01b3f77a33a9f40`); `Sandbox qualification: locally-qualified`; `Sandbox: ready`. Both state directories were prepared as private. No authenticated model request |
| `--container-setup` on the newer WSL host (kernel `6.18.58.1-microsoft-standard-WSL2`), on the tagged state | Passed (operator-reported, 2026-11-11): the runtime, toolchain and proxy images were rebuilt (tag suffix `setup-d790d5e028ab491abe23e91f54c11824`); `Sandbox qualification: locally-qualified`; `Sandbox: ready`. No authenticated model request |

Every restricted installation must rebuild and rerun setup or qualification.
The qualification identity (IPv6 state, enforced budget sets), the shared
code digests and the runtime image identity all change.

Known follow-up: the guard accepts any tmpfs mounted read-only at
`/run/secrets`. A read-only mount still allows `connect()` to an existing
socket, so a stricter check (mountinfo root `/` and an empty directory) will
be evaluated after the host tests. The behavior is unchanged in this tag.

The five-wrapper parity table now names `sandbox-ref-11`. The sibling tables
match it once each wrapper adopts the tag with `tools/propagate.py`.

## Qualification working directory and runtime-build test (`sandbox-ref-12`): 2026-11-12

Change `fix-shared-gate-workdir-and-runtime-build-test`. Two shared defects
found while adopting `sandbox-ref-11` in the wrappers:

- **Qualification containers depended on the image `WORKDIR`.**
  - The gate containers (`Gate.common()`) and the security-identity probe
    (`qualification_records.security_probe_args()`, extracted from
    `fingerprint()`) now pass `--workdir /`. Before, Podman created and
    chowned a `WORKDIR` missing from the image layers, which failed for the
    Rocky host's domain UID under `--userns=keep-id` (seen in Codex).
  - The probes use only absolute paths. The guarded probe keeps the
    wrapper's own `--workdir`.
- **A shared setup test assumed a recipe-built runtime.**
  - `test_runtime_build_receives_host_ca_only_when_trusted` now pins
    `install.runtime_build: recipe`. Before, it failed in Pi
    (`runtime_build: wrapper`).
  - Wrapper-built runtimes stay covered by
    `test_runtime_build_follows_the_profile`.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 348 tests, 66 skipped. New: `--workdir /` in the gate common arguments and in the security probe arguments |
| `test_runtime_build_receives_host_ca_only_when_trusted` with the profile set to `wrapper` (one-off run) | Passed. The previous version of the test fails in the same run |
| `bash tests/run-runtime.sh --qualification` | Passed: 27 tests, real gate containers |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| Pre-fix Codex image `8ae054805108` (`WORKDIR /workspace`, in no layer) with the gate's common arguments | With `--workdir /`: the container starts in `/` and `/workspace` does not exist. Without it: Podman creates `/workspace` at start (time 11:15:33, equal to the start time) |
| Domain-UID host (Rocky Linux 9) | Pending: the operator runs it after wrapper adoption |

The shared code digests change, so restricted installations rerun
qualification after adopting this tag.

## Engine-provided `/dev` for pseudo-terminals: 2026-11-12

Change `use-engine-dev-for-pseudo-terminals`, launcher only. No shared file
changes, so no new reference tag.

Agent and shell containers no longer mount their own `/dev` tmpfs or
`devpts`. The explicit `devpts` from `sandbox-ref-11` took the kernel
defaults `mode=600,ptmxmode=000`, so no process in a session could open a
pseudo-terminal. The terminal itself still attached, because the engine
allocates the console outside that `devpts`. Antigravity found the defect,
because agy runs tool commands in a PTY. The same fix passed its operator
tests on this host, the Rocky Linux 9 lab host and the newer WSL host.

Measured on this host (Podman 4.9.3, image
`localhost/claude-code:setup-11645a29317d4621bf77bc5efc1437af`,
`--read-only --userns=keep-id --cap-drop=all`):

| Layout | `/dev/pts` options | `pty.openpty()` | `/dev` |
| --- | --- | --- | --- |
| Explicit `/dev` tmpfs and `devpts` (previous) | `mode=600,ptmxmode=000` | "out of pty devices" | `ro,nosuid,noexec` |
| Explicit `/dev`, `devpts` and `--device /dev/ptmx` | `mode=600,ptmxmode=000` | "out of pty devices": the engine replaces `/dev/ptmx` with a `pts/ptmx` link | `ro,nosuid,noexec` |
| Engine `/dev` (adopted) | `mode=620,ptmxmode=666` | `/dev/pts/0` | `ro,nosuid` |

`--mount type=devpts,destination=/dev/pts,ptmxmode=0666` is rejected:
"ptmxmode: invalid mount option".

On Podman 5, `/dev` is now the engine's writable tmpfs without `noexec`. No
device can be created without capabilities. The requirement
"Terminal-compatible device mounts" is replaced by "Engine-provided device
mounts allow pseudo-terminals".

| Check | Result |
| --- | --- |
| `test_pseudo_terminals_and_device_masks` (new) with the previous launcher | Failed: "out of pty devices" |
| `test_pseudo_terminals_and_device_masks` with the fix | Passed |
| `tests/test_wrapper.py` | Passed: 75 tests, 1 skipped. With the previous launcher, the updated assertions fail (27 failures) |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 349 tests, 67 skipped (the runtime tests are opt-in) |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 17 tests, including `test_explicit_temporary_mounts_and_lifecycle` and `test_pseudo_terminals_and_device_masks` |
| Operator `--container-setup` and an interactive session on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-12): setup completed on all three hosts, and the operator talked to the model (Opus 5.5) in an attached terminal session on each |

Qualification digests the launcher, so restricted installations rerun
`--container-setup`. The runtime image is unchanged.

## Toolchain library: 2026-11-13

Change `add-toolchain-library`, shared code (`setup/toolchains.py`, the
`TOOLCHAINS` and `TOOLCHAINS_DIR` profile suffixes, the installed and qualified
file lists) and this wrapper's launcher. Reference tag `sandbox-ref-13`.

Sessions mount an operator-managed host library read-only, with `nosuid` and
`nodev`, at `/toolchains`. The operator manages it with
`--container-toolchain add|list|remove|verify`.
- Toolchains are relocatable prefixes from digest-pinned image paths or
  checksummed local archives, each checked in the runtime image without
  network before it is accepted.
- Default toolchains are appended after the image `PATH`; `env.sh` puts a
  toolchain first for one command.
- The guard, proxy, policy and network modes are unchanged.

| Check | Result |
| --- | --- |
| `tests/test_toolchains.py` (new, shared) before `setup/toolchains.py` existed | Failed: module missing |
| `tests/test_toolchains.py` | Passed: 21 tests (recipe validation, archive checksum, unsafe members, permissions, image source and maintenance, hardened check, failed check, replace/remove, lock, `requires`, default conflicts, generated files, `launch-env`, base reference) |
| New `tests/test_wrapper.py` cases with the previous launcher | Failed as intended (dispatch, mount, private creation, unsafe library, disabled mount, appended `PATH`, restricted `--mount-target`) |
| `tests/test_wrapper.py` | Passed: 81 tests. Two existing cases now expect the specified behavior: an exposed home workspace contains the default library and stops unless the library is moved or omitted; `~/.local/share` may contain only `sandbox-toolchains` |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 380 tests, 71 skipped (the runtime tests are opt-in) |
| `bash tests/run-runtime.sh` (image `localhost/claude-code:setup-11645a29…`) | Passed: 19 tests, including the archive and image sources, a failing check, the read-only mount, the default environment that keeps the image's `node` and `python3`, and the omitted mount |
| `bash tests/run-runtime.sh --network` (full suite; its synthetic installation now includes `setup/toolchains.py`, `setup/common.py` and `Containerfile`) | Passed: 22 tests, 1 skipped (the opt-in documented examples) |
| `bash tests/run-runtime.sh --network -k toolchain` | Passed: a toolchain added on the host while an offline session was running became usable in that session, with no direct network |
| `SANDBOX_TOOLCHAIN_EXAMPLES=1 bash tests/run-runtime.sh --network -k documented_toolchain` | Passed: all six recipes in `docs/toolchains/` added, then used in one offline session (see below) |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed on all three hosts (operator, 2026-11-13) |
| Operator toolchain check on this host: a toolchain added with `--container-toolchain add` and used by the agent session | Passed (operator, 2026-11-13) |

Documented examples, verified 2026-11-13 in an offline session:

| Recipe | Source identity | Result |
| --- | --- | --- |
| `java21` | `docker.io/library/eclipse-temurin@sha256:0a3f329821dcadf54b2a3033a15e2e9f007069a9db43d7f51897e6b80e726b07` (`/opt/java/openjdk`) | Temurin 21.0.13 runs on the glibc 2.36 runtime although the image is Ubuntu-based |
| `maven3.9` | `docker.io/library/maven@sha256:99e61abcff91a9b1333463bd8451fb18495d6eba9250ac66a338b518f8278320` (`/usr/share/maven`) | `mvn -v` 3.9.16 with Java from `java21` through `requires`; jansi prints a native-library warning because `/tmp` is `noexec` |
| `go` | `docker.io/library/golang@sha256:4fa7c968ba93f1635670522dbb01a2c78150443e1385746924566079f36570ea` (`/usr/local/go`) | `go test` passes with `GOTMPDIR` under the workspace |
| `node24` | `node-v24.22.3-linux-x64.tar.xz`, SHA-256 `4f2b175a…66fcfb` (nodejs.org `SHASUMS256.txt`) | `node --version` v24.22.3 through `env.sh`; `node` by name stays the image's v22 |
| `python3.13` | `cpython-3.13.18+20261110-x86_64-unknown-linux-gnu-install_only.tar.gz`, SHA-256 `50c774f6…b37cc` (release `SHA256SUMS`) | `ssl`, `sqlite3` and `venv` import; `python3` by name stays `/usr/bin/python3` |
| `rust` | image built from `docs/toolchains/rust-musl.Containerfile` (`docker.io/library/rust@sha256:7c7d4eb4d05b7781187a327809466cfddf29753f6defdc3d19a0e291951b7a37` plus the musl target) | `cargo build --offline` of a new crate for `x86_64-unknown-linux-musl`, linked by `rust-lld`, runs and prints `Hello, world!` |

The defaults `java`, `mvn`, `go` and `cargo` also ran by name in that session.
SELinux and AppArmor enforcement were not tested; the README says so.
Qualification digests the launcher and `setup/toolchains.py`, so every
restricted installation reruns `--container-setup`.

## Qualification fixture and test runner (`sandbox-ref-14`): 2026-11-13

Change `fix-qualification-fixture-setup`. Two test defects present since
`sandbox-ref-13`, found while Codex adopted that tag. Production code is
unchanged.

- **The shared qualification runtime fixture lacked `setup/`.**
  - Since `sandbox-ref-13`, `SHARED_CODE` includes `setup/toolchains.py`.
    The `QualificationRuntime` installation in `tests/test_qualification.py`
    did not copy it, so six real-engine tests failed with
    `No such file or directory: …/installed/setup`. The same failure appeared
    here and in Codex.
  - The fixture now copies `FIXTURE_SETUP_FILES` (`setup/common.py`,
    `setup/toolchains.py`). A unit test checks that the tuple covers every
    `setup/` entry of `SHARED_CODE`.
- **`bash tests/run-runtime.sh --wrapper` failed** with 190 failures, also on
  `main`.
  - The runner set no `SANDBOX_TEST_TMPDIR`, so wrapper fixtures were created
    under the image's world-writable `/tmp`, which the toolchain library
    refuses as an ancestor.
  - The runner now mounts a private executable tmpfs at `/sandbox-test-tmp`
    (`0700`, `U=true`, 1 GiB) and sets `SANDBOX_TEST_TMPDIR` to it in every
    mode. This file is not shared.
- **Procedure.** The `sandbox-ref-13` record lists neither `--qualification`
  nor `--wrapper`, and that tag left the parity cells on `sandbox-ref-12`.
  `docs/propagation.md` step 1 now requires every mode that
  `tools/propagate.py` prints for the changed shared files, plus
  `--qualification` for any change to a file in `SHARED_CODE`.

| Check | Result |
| --- | --- |
| New fixture unit check with an empty tuple | Failed as intended |
| `python3 -m unittest tests.test_qualification tests.test_alignment` (private tmpfs) | Passed |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 381 tests, 71 skipped |
| `bash tests/run-runtime.sh --wrapper` on `main` before the runner fix | Failed: 190 failures, toolchain library under the world-writable `/tmp` |

Runner modes after both fixes, with image `localhost/claude-code:setup-11645a29…`:

| Mode | Result |
| --- | --- |
| `--wrapper` | Passed: 81 tests |
| `--setup` | Passed: 71 tests |
| `--setup-runtime` | Passed: 2 tests |
| `--qualification` | Passed: 28 tests, including the six that had failed |
| `--guard` | Passed: 20 tests, 1 skipped |
| `--network` | Passed: 22 tests, 1 skipped (the opt-in documented toolchain examples) |
| default (`tests/test_runtime.py`) | Passed: 19 tests |
| `--shared` | Not offered by this runner; the unit discovery covers the shared suites |

No qualification input changed, because test files are not digested.
Installations qualified on `sandbox-ref-13` stay valid; no rerun of
`--container-setup` is needed for this tag.

Operator follow-up (2026-11-13): `main` and `sandbox-ref-14` pushed; the
operator reports that the tests passed in all environments (this host, the
Rocky Linux 9 lab host and the newer WSL host).

## XDG variables protected from toolchains (`sandbox-ref-15`): 2026-11-13

Change `protect-xdg-toolchain-variables`, shared code (`setup/toolchains.py`).
Found while planning the OpenCode adoption. OpenCode places its state with
`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` and `XDG_STATE_HOME`, and
Podman keeps the last `--env` for a name (checked on this host). A default
toolchain with an XDG variable would therefore have moved OpenCode's state in
new sessions. Every `XDG_` variable is now protected, like the wrapper prefix,
both in `add` and in `launch-env`.

| Check | Result |
| --- | --- |
| New `xdg variable` recipe case and `launch_env` index case with the previous module | Failed as intended |
| `python3 -m unittest tests.test_toolchains tests.test_alignment` (private tmpfs) | Passed |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 382 tests, 71 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 81 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 19 tests |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-13); `main` and `sandbox-ref-15` pushed |

Images: `localhost/claude-code:setup-11645a29…`. `setup/toolchains.py` is
qualified code, so restricted installations rerun `--container-setup`.

## Agent-neutral toolchain comment (`sandbox-ref-16`): 2026-11-13

Change `neutral-toolchain-comment`. The `sandbox-ref-15` comment in the shared
`setup/toolchains.py` named an agent ("OpenCode"). In OpenCode, whose profile
lists the identifier `opencode`, the agent-identifier scans of
`tests/test_alignment.py` and `tests/test_reference_copy.py` failed on it.
The comment is now neutral. No code changed.

| Check | Result |
| --- | --- |
| `git grep -i` of `network/`, `setup/` and the shared tests (without `network/bin`) for the identifiers of all five profiles | No match |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 382 tests, 71 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-13); `main` and `sandbox-ref-16` pushed |

The digest of `setup/toolchains.py` changes, so restricted installations
rerun `--container-setup`.

## Toolchain variables shared across wrappers (`sandbox-ref-17`): 2026-11-14

Change `share-toolchain-env-across-profiles`. Porting the toolchain library to
Antigravity found two defects of the shared `setup/toolchains.py`:

- Antigravity removes `DBUS_SESSION_BUS_ADDRESS` with `--unsetenv`. On this
  host's engine (Podman server 4.9.3, client 4.3.1), `--unsetenv` does not
  remove a value given with `--env`:
  `podman run --env DBUS_SESSION_BUS_ADDRESS=x --unsetenv DBUS_SESSION_BUS_ADDRESS …`
  prints `x`. A default toolchain that set the variable would reach the
  session. For a name repeated with `--env`, the last value wins.
- The protected set included the current wrapper's profile variables. A
  recipe accepted by one wrapper (for example one setting `GEMINI_API_KEY`
  through Claude) made another wrapper's `launch-env` fail, so that wrapper
  started no session with the shared library.

Changes:

- `DBUS_SESSION_BUS_ADDRESS` joins the neutral protected set.
- The protected names form two groups:
  - **neutral:** the same in every wrapper. `add` rejects them and
    `launch-env` fails on them, as before;
  - **profile:** the wrapper's prefix, configuration, approval and
    credential variables. `add` still rejects them, while `launch-env`
    leaves them out of the session and prints one warning per toolchain and
    variable.
- The README "Protected variables" bullet describes both groups.

| Check | Result |
| --- | --- |
| New `tests/test_toolchains.py` cases with the `sandbox-ref-16` module | Failed as intended (bus variable rejected in `add`; bus variable in the index; profile variables from the shared index) |
| `python3 -m unittest tests.test_toolchains tests.test_alignment tests.test_agent_profile` (private tmpfs) | Passed: 45 tests |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs; the `--shared` mode of the wrappers) | Passed: 384 tests, 71 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 71 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 81 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 19 tests |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-14); `main` and `sandbox-ref-17` pushed |

The digest of `setup/toolchains.py` changes, so restricted installations
rerun `--container-setup`.

## Shared session boundaries (`sandbox-ref-18`): 2026-11-15

Change `harden-shared-session-boundaries`, from the cross-wrapper review of
2026-11-14:

- **Agent variables (H1, shared part):** `agent/profile.json` gains the
  optional `native.protected_env`, a list of variables and `_`-terminated
  prefixes that the agent itself reads. The profile loader validates it
  (format, prefixes of at least three characters, no duplicates, no neutral
  names). `setup/toolchains.py` treats them as profile variables: `add`
  rejects them, and `launch-env` leaves them out with one warning naming the
  toolchain. The neutral names moved into `network/agent_profile.py`
  (`NEUTRAL_ENV`, `NEUTRAL_ENV_PREFIXES`), unchanged. Claude declares
  `CLAUDE_CODE_`, `ANTHROPIC_`, `DISABLE_TELEMETRY`, `DISABLE_AUTOUPDATER`,
  `DISABLE_ERROR_REPORTING` and `ENABLE_CLAUDEAI_MCP_SERVERS`. Before this
  change a toolchain could set `ANTHROPIC_BASE_URL`, which Claude does not
  override in any mode.
- **Working directory (M4):** `toolchains.check()` runs with `--workdir /`,
  like qualification since `sandbox-ref-12`. The Claude `Containerfile`
  creates `/workspace` in the package step, and `tests/test_image_pins.py`
  gained `workdir_violations` from Codex.
- **State and workspace (M3):** the shared `writable_mounts()` refuses an
  isolated state directory that is, contains or lies inside the workspace
  (the parent in worktree mode), so managed launches refuse it in every
  wrapper with this tag. The Claude launcher refuses it on direct launches,
  after the tool prerequisites and before any engine call.
- **Signals (M2, Claude part):** `podman start --attach` uses
  `--sig-proxy=false`, like the other four wrappers; the wrapper's shutdown
  alone forwards INT, TERM and HUP.
- **Alignment tests (L2):** the mismatch test now runs the real check. The
  check reads the launcher's code and its help text separately: every profile
  variable must appear in the code (except `TOOLCHAINS_DIR`, read by shared
  code), and every prefix-derived variable in the help text (except
  `QUALIFICATION_INPUT`, set by setup). Ignoring the help text entirely, as
  the review proposed, failed in all five wrappers on `TOOLCHAINS_DIR`. The
  new test passes on copies of the four adopters.

| Check | Result |
| --- | --- |
| New tests with the old code | Failed as intended: Claude toolchain variables reached the session, `WORKDIR /workspace` not created, state overlap accepted, mismatch test vacuous |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs; the `--shared` mode of the wrappers) | Passed: 391 tests, 72 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 72 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests |
| `bash tests/run-runtime.sh --wrapper` | Passed: 83 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 19 tests |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-15); `main` and `sandbox-ref-18` pushed |

Runtime image: setup image `0fb0d09b935d`, tagged
`localhost/claude-code:latest` only for the runs and untagged by name
afterwards. `setup/common.py`, `setup/toolchains.py` and
`network/agent_profile.py` change, and so does the `Containerfile`, so
restricted installations rerun `--container-setup`, which rebuilds the image.

## Reference shell (`sandbox-ref-19`): 2026-11-15

Change `establish-sandbox-reference`. `sandbox-container` takes over the
reference role from `claude-container`: its history was imported unchanged
(merge `9ff66c8`, tree equal to `claude-container` `094ec39`, tags
`sandbox-ref-1` to `sandbox-ref-18` kept), so every entry above was recorded
for the Claude wrapper while it held this role and is history, not evidence of
the shell.

- **Reference shell:** `sandbox-container.sh` opens Bash with the profile
  `sandbox-container` (`"auth": {}`, no approval-bypass variable, empty policy
  profiles). `offline` is the default, `unrestricted` is explicit, `provider`
  is refused before any engine operation. An offline launch without the guard
  manifest stops with setup guidance before engine queries. Bash history lives
  in `~/.config/sandbox-container` (or the isolated home); the wrapper sets
  `HISTFILE` after the toolchain environment.
- **Image:** same pinned `node:22-bookworm-slim` base and HTTPS apt block as the
  agent wrappers, `@fission-ai/openspec@2.0.0`, no agent CLI, `bash` entrypoint.
- **Shared code:** profiles may declare no authentication method and no
  approval bypass; such a policy has no profiles; session helper, setup and
  qualification refuse provider mode for them; setup offers only offline and
  unrestricted and defaults to offline.
- **Shared tests:** module-level tests use the fixture profiles in
  `tests/fixtures/` (`fixture-agent` with two `.test` methods, `fixture-shell`
  without methods). Setup checks that launch the wrapper moved to the per-agent
  `tests/test_setup_wrapper.py`; the qualification runtime gate uses the real
  wrapper and profile. Alignment checks neutral `SANDBOX_*` names against the
  wrapper prefix and forbids checkout-profile reads in the other shared tests.
- **Provider evidence:** the reference has no provider mode, so
  `tests/provider_session.py` drives `network/session.py` from a protected
  fixture installation with the production guard, relay and proxy; TLS binding,
  real proxy, CA, budget, exhaustion and proxy-death cases run through it.
  Wrapper provider lifecycle tests (signals, recovery, stalled cleanup) and the
  Claude authenticated/CLI tests stay in the agent wrappers.
- **Launcher fix:** the lifetime notice used Bash `SECONDS` (whole seconds), so
  a short failing session crossing a second boundary was reported as a reached
  limit; it now measures with `EPOCHREALTIME`. The new boundary test failed with
  the old launcher and passed 32 consecutive isolated runs plus two full
  `--wrapper` runs with the fix. The same defect remains in the agent wrappers.

Environment: WSL2 kernel 6.6.87.2-microsoft-standard-WSL2 x86_64, Podman
server 4.9.3 (rootless, same-host Unix service), runtime image
`localhost/sandbox-container:latest` (`f7a1e11124c3`), guard toolchain
`215f5ffc1023` tagged `localhost/sandbox-container-guard-toolchain:development`.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 399 tests, 66 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 66 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests (real offline setup, qualification `locally-qualified`, persistent history) |
| `bash tests/run-runtime.sh --qualification` | Passed: 28 tests, 1 skipped (TLS stage needs provider mode) |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped (305-second idle check) |
| `bash tests/run-runtime.sh --network` | Passed: 16 tests, 1 skipped (documented toolchain downloads) |
| `bash tests/run-runtime.sh --network-policy` | Passed: 15 tests |
| `bash tests/run-runtime.sh --network-feasibility` | Passed: 1 test |
| `bash tests/run-runtime.sh --wrapper` | Passed: 80 tests (after the lifetime fix; one earlier full run failed on the boundary defect) |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 19 tests |
| `tools/propagate.py` dry run against a clone of `codex-container` (`sandbox-ref-18` to a local tag) | Passed: 16 modified and 4 added shared files, documents and runner checklist listed |
| `git diff --check`, `bash -n sandbox-container.sh` | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-15), managed launch from a project included; `main` and `sandbox-ref-19` pushed. The newer WSL host needed host CA trust (VPN with TLS inspection), so setup there used a non-default answer and imported the host CA bundle |

Every agent wrapper must adopt `sandbox-ref-19` in its own change; the shared
test ownership moves with it.

## Adoption blockers (`sandbox-ref-20`): 2026-11-16

Change `fix-adoption-blockers`, found while planning Claude's adoption of
`sandbox-ref-19`. No wrapper adopts `sandbox-ref-19`; all adopt this tag.

- **Shared `tests/test_guard.py`:** `guarded_multiplex` took the proxy image with
  `environment[profile_env('EGRESS_IMAGE')]`, which names the fixture variable,
  while each wrapper's `test_network_runtime.provider_fixture()` returns its own
  names. It now takes the single harness entry ending in `_EGRESS_IMAGE`.
- **`tools/propagate.py`:** `--apply` also points a manifest written while
  `claude-container` held the reference role at this repository (`SIBLING`,
  docstring, skip message); the dry run reports it; a manifest without a
  `SIBLING` line is refused.

| Check | Result |
| --- | --- |
| `codex-container` copy with `sandbox-ref-19` applied, `--guard -k guarded_multiplex` | Failed as expected: `KeyError: 'FIXTURE_AGENT_EGRESS_IMAGE'` |
| Same copy with the changed `tests/test_guard.py` | Passed: 3 tests, 1 skipped (idle check) |
| `python3 -m unittest discover -s tests -p test_propagate.py` | Passed: 8 tests |
| Clone of `codex-container` next to this checkout, `--apply` from `sandbox-ref-18` to a local tag, then its `tests/test_reference_copy.py` | Passed: 5 tests; the sibling check ran against `sandbox-container` instead of skipping |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 402 tests, 66 skipped |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh --network` | Passed: 16 tests, 1 skipped |
| `git diff --check` | Passed |

No installed code, image or profile changes: installations need no new setup.

## Lifetime notice clock (2026-11-16)

The real-expiry lifetime notice was intermittently missing: about one run in ten
of `test_session_lifetime_limit_and_early_exit` in `antigravity-container`, and
once in the Codex `--network` suite, with exit status 255 but no notice. Bash
`EPOCHREALTIME` follows the wall clock, and WSL2 steps it backwards to
resynchronise with the host: in 30 raw `podman create --timeout 3` plus
`podman start --attach` runs, the monotonic clock always measured at least
3.9 s, while the wall clock measured 2.15 s once (a 1.84 s backward step).

The launcher now measures the session from just before `podman create` with
`/proc/uptime` (monotonic, centiseconds since boot), falling back to `SECONDS`
only if `/proc/uptime` cannot be read. The threshold is unchanged: the notice
appears when a failing session has lasted at least the limit.

| Check | Result |
| --- | --- |
| `python3 -m unittest tests.test_wrapper -k lifetime -k boundary -k timeout` (disposable container), 5 runs | Passed 5 of 5 |
| `antigravity-container`: `bash tests/run-runtime.sh -k test_session_lifetime_limit_and_early_exit`, 10 runs | Passed 10 of 10 (before the fix: failed 2 of 10) |
| `bash -n` on the launcher | Passed |

No installed code, image or profile changes: installations need no new setup.

## Guard test home (`sandbox-ref-21`): 2026-11-16

Change `fix-guard-agent-home`, found in OpenCode's adoption of `sandbox-ref-20`.

- **Shared `tests/test_guard.py`:** `production_container` ran the real agent
  image with the fixture profile's home (`/fixture-home`) as its writable tmpfs.
  It now mounts `AGENT_HOME`, the checkout's real home, which
  `tests/sandbox_profile.py` exposes next to `AGENT_COMMAND`.

| Check | Result |
| --- | --- |
| `opencode-container` on `sandbox-ref-20`, `bash tests/run-runtime.sh --guard` | Failed as expected: `test_production_filter_and_landlock_on_real_rootless_kernel`, `EROFS: read-only file system, mkdir '/opencode-home/.local'` |
| Same checkout with the changed `tests/test_guard.py` and `tests/sandbox_profile.py` (temporary, restored) | Passed: 20 tests, 1 skipped |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 402 tests, 66 skipped |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `git diff --check` | Passed |

No installed code, image or profile changes: installations need no new setup.

## Launcher contract (2026-11-16)

Change `define-launcher-contract`: analysis and contract only, no code, spec
or shared-file change and no tag. Results in `docs/launcher-contract.md` and
`docs/launcher-test-map.md`.

Read: the six launchers and their `tests/test_wrapper.py` at sandbox-container
`4e0f116`, claude-container `6cac46f`, codex-container `6951d1e`,
antigravity-container `116c7a8`, opencode-container `36299d4`, pi-container
`f6c194d` (all on `sandbox-ref-21`), and each launcher's `--container-help`
run with an empty `HOME` and no engine.

| Check | Result |
| --- | --- |
| Phase rows (seven phases) | 95: 59 same, 15 union, 5 hook, 11 user decisions (U1-U9), 5 cross-references to other rows |
| User decisions | U1-U9 recorded with their answers |
| Wrapper test cases mapped | 488 of 488 (S 80, C 83, X 85, A 80, O 69, P 91), none unmapped |
| Hook cells naming an undefined hook | 0 |
| Visible changes without a spec delta row | 0 |
| `openspec validate define-launcher-contract --strict` | Passed (`skip_specs`) |
| `git diff --check` | Passed |

Independent review of the contract (2026-11-16): a read-only reviewer checked
`docs/launcher-contract.md` and `docs/launcher-test-map.md` against the six
launchers, tests, profiles and specs.

| Check | Result |
| --- | --- |
| Findings | 28: 6 high (H1-H6), 13 medium (M1-M13), 9 low (L1-L9); every high finding verified against the launcher source |
| Resolutions | all 28 recorded in "Review findings"; user decisions U10-U14 for the five that needed one |
| Test map after regeneration | 488 of 488 cases mapped (S 80, C 83, X 85, A 80, O 69, P 91), 25 marked "shared (rewrite)" |
| Visible changes without a spec delta row | 0 |
| `openspec validate define-launcher-contract --strict` | Passed (`skip_specs`) |
| `git diff --check` | Passed |

Second independent review of the contract (2026-11-16), on the corrected
document.

| Check | Result |
| --- | --- |
| Findings | 34: 7 high (H-a to H-g), 14 medium, 13 low; the earlier resolutions H2-H6, M1-M11, L1, L3-L5, L7 and L9 confirmed present |
| Resolutions | all recorded in "Review findings › Second review"; user decisions U15-U18 |
| Test map after regeneration | 488 of 488 cases mapped, 41 marked "shared (rewrite)"; four other shared test files listed |
| `openspec validate define-launcher-contract --strict` | Passed (`skip_specs`) |
| `git diff --check` | Passed |

## Shared launcher core (change `implement-shared-launcher`): 2026-11-17

`launcher/core.sh` implements `docs/launcher-contract.md` (decisions U1-U18,
both reviews). `sandbox-container.sh` is the thin entry script and
`agent/launcher.sh` the reference's profile data (shell profile, no hooks).
Shared tests: `tests/test_launcher.py` (106 cases: the reference's launcher
cases run through the fixture shell root, plus cases for the fixture agent part
with every hook, provider mode included) on the shared fake engine
`tests/fake_podman.py`; the reference's `tests/test_wrapper.py` keeps 6
shell-profile cases. Shared Python: profile fields `native.exec` and
`native.exec_tmp`, no `install.runtime_build`; installation, qualification
identity, preflight and managed-launch trust lists include the core files; a
missing mode follows the profile default; setup builds through the wrapper.
`tools/propagate.py` adopts a shared directory that the new tag introduces.

Findings during validation, fixed in this change:

- The per-wrapper runtime fixtures (`test_network_runtime.py`, shared
  `test_qualification.py`) copied installations without the core files.
- `test_setup_runtime.py`'s engine shim answered every `image inspect` of the
  prepared image with its ID, so the new freshness check read the ID as the
  `build-inputs-hash` label; the shim now answers only `{{.Id}}`.
- `test_runtime.py` asserted the old 256/16/256 MiB layout (U7).
- `tests/run-runtime.sh --wrapper` now also runs `test_launcher.py`.

Environment: WSL2 6.6.87.2, Podman server 4.9.3 (client 4.3.1), reference image
rebuilt through the new build-only path: `localhost/sandbox-container:latest`
`326bdf332f03`, `build-inputs-hash`
`5fff7415583965f884f5d901b464c60c3766c73d4f313b57c06597eb5056d593`.

| Check | Result |
| --- | --- |
| `--container-build` alone (real engine, maintenance) | Passed: built, labeled, no session container |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 440 tests, 66 skipped |
| `bash tests/run-runtime.sh --setup` | Passed: 67 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed: 2 tests (after the shim fix) |
| `bash tests/run-runtime.sh --qualification` | Passed: 29 tests, 1 skipped |
| `bash tests/run-runtime.sh --guard` | Passed: 20 tests, 1 skipped |
| `bash tests/run-runtime.sh --network` | Passed: 16 tests, 1 skipped |
| `bash tests/run-runtime.sh --network-policy` | Passed: 15 tests |
| `bash tests/run-runtime.sh --network-feasibility` | Passed: 1 test |
| `bash tests/run-runtime.sh --wrapper` | Passed: 112 tests (`test_launcher.py`, `test_wrapper.py`) |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 19 tests |
| `tools/propagate.py` dry run against a clone of `claude-container` (`sandbox-ref-21` to a temporary local tag) | Passed: adds `launcher/core.sh`, `tests/test_launcher.py`, `tests/fake_podman.py` and the fixture launcher parts; nothing "not adopted" |
| `git diff --check`, `bash -n` on the entry script and core | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator-reported, 2026-11-17); `main` pushed, `sandbox-ref-22` tagged on the merge |

The installed and qualified code changes: installations rerun `--container-setup`.

## Shared test identifiers (`sandbox-ref-23`): 2026-11-17

Change `fix-shared-test-identifiers`, found in Claude's adoption of `sandbox-ref-22`.

- **Shared `tests/test_launcher.py`:** seven lines carried Claude identifiers
  (`CLAUDE_YOLO`, `ANTHROPIC_BASE_URL`, an alias named `claude`) from the
  reference's old `tests/test_wrapper.py`. They now use `OTHER_AGENT_YOLO`,
  `OTHER_AGENT_BASE_URL` and `agent-alias`, with the same meaning.
- **Shared `tests/test_alignment.py`:** a new case scans the shared files for the
  identifiers of every wrapper checkout next to this one (only the `identifiers`
  field of each `agent/profile.json` is read); without siblings it is skipped.

| Check | Result |
| --- | --- |
| `claude-container` adopting `sandbox-ref-22`, `python3 -m unittest tests.test_alignment` | Failed as expected: `test_shared_components_contain_no_agent_identifiers` (7 lines of `tests/test_launcher.py`) |
| New sibling check with host Python against the `sandbox-ref-22` `tests/test_launcher.py` (temporary, restored) | Failed as expected: the same 7 lines |
| New sibling check with host Python after the fix | Passed |
| New sibling check in a copy without sibling checkouts | Skipped: no sibling wrapper checkout |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs; no siblings visible) | Passed: 441 tests, 67 skipped |
| `bash tests/run-runtime.sh --wrapper` | Passed: 112 tests |
| `git diff --check` | Passed |

No installed code, image or profile changes: installations need no new setup.

## Inaccessible state diagnostic (`sandbox-ref-24`): 2026-11-17

Change `fix-inaccessible-state-diagnostic`, found in Codex's adoption of
`sandbox-ref-23` (old Codex case `test_inaccessible_state`).

- **Core:** each state directory (isolated home, shared configuration, shared
  directories, read-only state) is checked for read and search access before it
  is resolved, so a directory the caller cannot enter stops with
  `<wrapper>: state directory is not accessible: <path> (...)` instead of Bash's
  `cd: ...: Permission denied`. A directory that cannot be created stops with
  `<wrapper>: cannot create state directory: <path> (...)` instead of `mkdir:`.
- **Shared `tests/test_launcher.py`:** `test_inaccessible_state_and_ignored_permissions`
  covers the six cases with the prefix, the path, the hint and no image, build or
  create call.

| Check | Result |
| --- | --- |
| Extended shared case against the previous core | Failed as expected: 6 subtests, raw `cd:` and `mkdir:` messages |
| `python3 -m unittest tests.test_launcher tests.test_wrapper tests.test_alignment` | Passed: 129 tests, 1 skipped |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 441 tests, 67 skipped |
| `bash tests/run-runtime.sh --wrapper` | Passed: 112 tests |
| `bash tests/run-runtime.sh --setup` | Passed: 67 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`) | Passed: 19 tests |
| `git diff --check` | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed |

The installed launcher core changes: installations rerun `--container-setup`.

## Delegated socket path (`sandbox-ref-25`): 2026-11-18

Change `verify-delegated-socket-path`, from the Antigravity adoption's old case
`test_complete_socket_response_required` (`true /`), which the user first
classified as a visible change and then chose to fix (2026-11-17).

- **Core and setup:** the host socket path reported by the delegated service,
  after removing `unix://`, must not consist only of slashes; when the path
  exists in the wrapper's own namespace (or is a dangling link) it must be a
  Unix socket. A path the wrapper cannot see is accepted as the remapped socket
  of a containerized wrapper, where the service's answer stays trusted.
- **Shared tests:** `test_reported_host_socket_must_be_a_socket_when_visible`
  in `tests/test_launcher.py` (`/`, `//`, `unix:///`, a directory, a regular
  file and a dangling link refused, with and without `--container-build`; the
  socket, a link to it and an invisible path accepted), and the extended
  `test_socket_validation_rejects_rootful_and_cr_responses` in
  `tests/test_setup.py`.

Environment: WSL2 6.6.87.2, Podman server 4.9.3; image
`localhost/sandbox-container:latest` `dfa6df506165`, rebuilt through the
build-only path.

| Check | Result |
| --- | --- |
| New shared cases against the previous core and setup | Failed as expected: 12 launcher refusal subtests and the setup case; the accepted subtests passed |
| `python3 -m unittest tests.test_launcher tests.test_wrapper tests.test_alignment tests.test_setup` | Passed: 197 tests, 1 skipped |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed: 442 tests, 67 skipped |
| `bash tests/run-runtime.sh --wrapper` | Passed: 113 tests |
| `bash tests/run-runtime.sh --setup` | Passed: 67 tests |
| `bash tests/run-runtime.sh` (`test_runtime.py`, real delegated child containers from the runner, whose remapped socket path is not visible to the wrapper) | Passed: 19 tests |
| `git diff --check` | Passed |
| Operator `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host | Passed (operator, 2026-11-18) |

The visible-socket branch is covered by the shared fake-engine cases; the real
runs exercise the remapped branch. The installed launcher core and setup
change: installations rerun `--container-setup`.

## ShellCheck for the shared launcher files (`lint-shared-launcher-shellcheck`): 2026-11-18

ShellCheck at warning level, checking each file alone, reported findings in the
shared launcher files: in `launcher/core.sh` (no shell directive, variables
assigned by `capture_response` with `printf -v` and the entry script's
`wrapper_dir` seen as unassigned, an unquoted `exec` value, unquoted
`--mount` and `--tmpfs` option lists in arrays) and in the launcher fixtures and
`agent/launcher.sh` (no shell directive, data and hook outputs seen as unused).
Pi's CI scans the whole tree, so the copied files fail it there.

- **Core:** a `shell=bash` directive, a comment above `capture_response`,
  `SC2154` directives naming `capture_response` on the nine commands that read
  its targets and one naming the entry script for `wrapper_dir`, and quoting
  (`'noexec'`, `'exec'`, the two `--mount` and two delegation `--tmpfs` option
  lists). The diff changes only comments and quoting; the words passed to Podman
  are identical.
- **Agent parts:** the fixtures and `agent/launcher.sh` start with
  `# shellcheck shell=bash disable=SC2034,SC2154`, as Pi's and OpenCode's do.
- **Tool:** `tools/shellcheck.sh <checkout>` (reference-only) runs ShellCheck
  0.11.0 (`docker.io/koalaman/shellcheck@sha256:b9389b73c8f26f710a7171cb7d8848a34a9c1e07a7865e727c9ec4ce99f9a83f`)
  without network on every tracked `*.sh` file at warning level.

No tag is taken for this change (user, 2026-11-18): the core is part of the
qualified identity, so the next reference change that changes the core and
takes a tag carries it, and the wrappers propagate and rerun setup once.

| Check | Result |
| --- | --- |
| `bash tools/shellcheck.sh .` before the edits | Failed as expected: 96 findings in `launcher/core.sh` (14), the two fixtures (32, 25) and `agent/launcher.sh` (25) |
| `bash tools/shellcheck.sh .` after the edits | Passed: no finding |
| `python3 -m unittest tests.test_launcher tests.test_alignment tests.test_agent_profile` (disposable container, tests unchanged) | Passed: 145 tests, 3 skipped |
| `bash tests/run-runtime.sh --wrapper` | Passed: 113 tests |
| `git diff --check` | Passed |

Wrapper checkouts, checked with `tools/shellcheck.sh` without changes:

| Wrapper | Shared files (fixed by the next tag) | Own `agent/launcher.sh` (fixed in its next adoption) |
| --- | --- | --- |
| Claude | core 14, fixtures 32 and 25 | 26 (SC2148, SC2034) |
| Codex | core 14, fixtures 32 and 25 | 27 (SC2148, SC2034, one SC2154) |
| Antigravity | core 14, fixtures 32 and 25 | 26 (SC2148, SC2034) |
| Pi | core 14, fixtures 32 and 25 | none (directive present) |
| OpenCode | core 14, fixtures 32 and 25 | none (directive present) |

## OpenSpec 2.0.0 image pin (2026-11-18)

Change `pin-openspec-2-0-0` uses the newest stable release that was at least
72 hours old on 2026-11-18. The base image remains
`node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da`.
The maintenance build continued to fetch Debian packages over HTTPS.

| Runtime image | Image ID | `openspec --version` |
| --- | --- | --- |
| Before | `dfa6df5061659650b0aaaee6360125ccd5a44b3d00be2fa0be46b8fb3ef12cb2` | `1.16.0` |
| After | `5c1c2084fe24c9bfae5d48e9960ec7453d73c9734fd2a52925ef7d18cbf14925` | `2.0.0` |

Validation used WSL2 6.6.87.2 x86_64, the Podman 4.3.1 client, and the rootless
Podman 4.9.3 server on a same-host Unix socket. The guard suites used the prepared
toolchain image `a33a4e7a708555af127d04f788dc341decf4402077064deb64bb345720365654`.

The 1.16.0 image created `.config/openspec/config.json` in a private test home.
The 2.0.0 image reused that home through a locally qualified offline installation
with guard `abi3-seccomp-mux-v1`. In a temporary project, `openspec init --tools
none`, `openspec new change`, `openspec validate --all --strict --json`, and
`openspec list --json` passed. The temporary change declared `skip_specs: true`
for validation. The guard log reported no network attempt, and the file names
and checksums in `.config/openspec` matched before and after.

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p test_image_pins.py` | Passed all 6 tests on both images' recipes |
| `tests/image-smoke.sh` through wrapper shell mode | Passed with OpenSpec 2.0.0 and HTTPS Debian sources |
| `python3 -m unittest discover -s tests` (disposable container, private executable tmpfs) | Passed, 442 cases with 69 skips |
| `bash tests/run-runtime.sh --wrapper` | Passed all 113 tests |
| `bash tests/run-runtime.sh --setup` | Passed all 67 tests |
| `bash tests/run-runtime.sh --setup-runtime` | Passed both tests |
| `bash tests/run-runtime.sh` | Passed all 19 tests on the serial rerun |
| `bash tests/run-runtime.sh --network-feasibility` | Passed |
| `bash tests/run-runtime.sh --network-policy` | Passed all 15 tests |
| `bash tests/run-runtime.sh --network` | Passed, 16 cases with the opt-in toolchain downloads skipped |
| `bash tests/run-runtime.sh --qualification` | Passed, 29 cases with the provider-only TLS stage skipped |
| `bash tests/run-runtime.sh --guard` | Passed, 20 cases with the separately enabled 305-second idle check skipped |
| `bash tools/shellcheck.sh .` and `git diff --check` | Passed |
| `openspec validate pin-openspec-2-0-0 --strict` (planning CLI 1.16.0) | Passed |

The first runtime run overlapped the guard suite. Podman removal timed out
during the shared-state `TERM` subcase of the shutdown test. Test cleanup
subsequently removed the container.

## Process rlimit fallback and cgroup manager delegation (`sandbox-ref-26`): 2026-11-19

Change: `openspec/changes/archive/2026-11-19-add-pids-rlimit-fallback/`. Without the `pids`
controller, the agent and proxy process budgets fall back to
`--ulimit nproc=N:N` when the engine kernel is Linux 5.14 or later.

**Engine representation (task 1.1).** Measured on WSL2 x86_64
(`6.18.58.1-microsoft-standard-WSL2`), with Podman client 4.3.1, server 4.9.3,
the `systemd` cgroup manager and controllers `[cpu memory pids]`. Containers
used `--userns=keep-id`, the caller's UID, `--cap-drop=all` and
no-new-privileges.

| Created with | `{{json .HostConfig.Ulimits}}` | `PidsLimit` | Effective `Max processes` (soft, hard) |
| --- | --- | --- | --- |
| no budget flags | `[]` | 2048 (`containers.conf` default) | 63948, 63948 (inherited; not listed by inspect) |
| `--pids-limit=-1 --ulimit nproc=64:64` | `[{"Name":"RLIMIT_NPROC","Soft":64,"Hard":64}]` | 0 | 64, 64; `pids.max` is `max` |

Inside the second container, `ulimit -Su 100` failed with `Invalid argument`
and `ulimit -Hu 100` with `Operation not permitted`; lowering the soft limit
worked. Podman 4.9.3 does not list its inherited default, so the launcher's
template `[{{range .HostConfig.Ulimits}}{{.Name}}={{.Soft}}:{{.Hard}},{{end}}]`
reports `[]` without the fallback.

The operator measured the same on Podman machine 6.1.4 (WSL provider, kernel
`6.6.87.2-microsoft-standard-WSL2`, `cgroupfs` manager, controllers reported
as `[cpuset cpu io memory hugetlb pids rdma]`):

| Created with | `{{json .HostConfig.Ulimits}}` | `PidsLimit` | Launcher template | Effective `Max processes` |
| --- | --- | --- | --- | --- |
| no budget flags | `[]` | 0 | `[]` | 31733, 31733 (inherited) |
| `--pids-limit=-1 --ulimit nproc=64:64` | `[{"Name":"RLIMIT_NPROC","Soft":64,"Hard":64}]` | 0 | `[RLIMIT_NPROC=64:64,]` | 64, 64; no `pids.max` interface |

Both versions use the same representation, and neither lists the inherited
default.

On that engine the reported controllers did not take effect. A wrapper session
created with `--pids-limit=512` had no `pids.max` interface, kept the
inherited 31733 rlimit, and could raise its soft limit and lower its hard limit
to 1000. Two concurrent sessions each started 1000 background processes, the
cap of the test loop. The launch check passed, because it compares only the
configured `HostConfig` values. The same engine created a container with
`--memory=64m --cpus=1 --pids-limit=64` that had no `memory.max`, `cpu.max` or
`pids.max` interface (`/proc/self/cgroup` is `0::/`). The change therefore
counts controllers as delegated only with the `systemd` cgroup manager (design
D0).

**Engine without delegation (task 6.3).** The operator ran the change on the
same Podman machine 6.1.4: `cgroupfs`, controllers
`[cpuset cpu io memory hugetlb pids rdma]`, kernel
`6.6.87.2-microsoft-standard-WSL2`. The wrapper ran from a checkout copy on the
distribution's ext4 file system, in unrestricted mode with isolated state and
without the toolchain mount. Podman also warned that `/` is not a shared mount
and that the pause process could not join a systemd cgroup (no session bus).

| Check | Result |
| --- | --- |
| Launch notices | Passed: memory and CPU `not enforced: the rootless engine uses the cgroupfs cgroup manager, which applies no cgroup limits`; process `enforced through the process rlimit (512 tasks of the session user, threads included)` with the same reason |
| Effective limit in the session | Passed: `Max processes 512 512`; no `pids.max` interface |
| Raising the limit | Passed: soft above hard failed with `Invalid argument`; hard failed with `Operation not permitted`; both stayed 512 |
| Two concurrent sessions filling the limit | Passed: 489 and 497 background processes, the second started while the first held its processes |
| Leftover containers after the run | None |

The usable count stays below 512 because of the session's own tasks and
container startup tasks, as documented.

**Delegating host and runner modes (tasks 6.2 and 6.4).** The operator ran the
portable bundle (`run.sh`, branch tree with `.git`) on a separate WSL2 host:
kernel `6.6.87.2-microsoft-standard-WSL2`, Podman server 4.9.3, `systemd`
manager, controllers `[cpu io memory pids]`, Python 3.12.3 and Bash 5.2.21. The
runtime image (`bafde53b5002…`) and the guard toolchain image
(`a33a4e7a7085…`) were rebuilt with maintenance consent.

| Check | Result |
| --- | --- |
| Direct unrestricted session | Passed: no budget notice; `pids.max=512`; `Max processes` is the inherited 31733, with no process rlimit set by the wrapper |
| `bash tests/run-runtime.sh` | Passed: 19 tests in 313 s |
| `--setup` | Passed: 68 tests |
| `--setup-runtime` | Passed: 2 tests in 159 s |
| `--qualification` | Passed: 31 tests in 135 s, 1 skipped |
| `--network` | Passed: 16 tests in 362 s, 1 skipped |
| `--guard` | Passed: 20 tests in 139 s, 1 skipped |
| `--shared` (unit discovery) | 445 tests, 67 skipped; 14 environment failures, all proxy-session tests (see below) |

The 14 `--shared` failures were all in tests that start the session proxy:
- 13 `test_session.py` subtests: `test_proxy_budgets_follow_delegated_controllers` (6),
  `test_start_fails_closed_on_identity_hardening_and_invalid_results` (6) and
  `test_start_creates_verifies_and_records_the_owned_proxy`;
- `test_launcher.py` `test_provider_session_starts_and_stops_the_proxy_with_the_selected_credential`.

The bundle's temporary directory (`~/native-tmp/host-check/tmp`) makes the
proxy's `AF_UNIX` socket path too long. The operator reran with short
temporary directories. `test_session.py` used a directory below `/tmp` and
passed all 20 tests. The launcher case needs protected ancestors, so it used a
directory directly below the home directory, and passed.

Earlier spike on Podman machine 6.1.4 (WSL provider, `cgroupfs`, no delegated
controllers, `--ulimit nproc=64:64`): two concurrent containers each started 49
background processes before fork failed, so counting is per container. About
13 slots are taken by startup tasks of unknown origin.

**Unit suites (task 6.1).** Branch working tree compared with a pristine
`git archive HEAD` copy of `main` on the same runner (Python 3.11.2; `/tmp` and
`$HOME` are `noexec`, so `SANDBOX_TEST_TMPDIR` points to native executable
storage). Session tests need a short path for `AF_UNIX` sockets and use a
symlink below `/tmp`. Setup and launcher tests need protected ancestors and use
the long native path.

| Suite | Branch | `main` |
| --- | --- | --- |
| `test_launcher.py` | 107 tests; 1 environment failure | 107 tests; the same failure |
| `test_session.py` | 20 tests, passed | 20 tests, passed |
| `test_wrapper.py` | 6 tests, passed | 6 tests, passed |
| `test_setup.py` | 68 tests, passed (1 new) | 67 tests, passed |
| `test_setup_wrapper.py` | 8 tests, passed | 8 tests, passed |
| `test_qualification.py` | 31 tests (2 new), 7 skipped; passed in the final run | 29 tests, 7 skipped; the same intermittent error |
| `test_agent_profile.py` | 21 tests, 3 skipped, passed | the same |
| `test_alignment.py` | 17 tests, passed | 1 failure in the extracted copy only |

- The launcher environment failure is
  `test_provider_session_starts_and_stops_the_proxy_with_the_selected_credential`:
  `AF_UNIX path too long` on the long native temporary path.
- The intermittent error is `test_bounded_subprocess_group_cleanup`
  (`FileNotFoundError` on `/proc/<pid>/stat`). It occurred in 1 of 6 branch runs
  and 2 of 6 `main` runs.
- The `main`-only alignment failure comes from scanning the extracted copy
  outside Git, which includes the fixture profiles.
- `bash tools/shellcheck.sh .` and `git diff --check` pass.
- The table shows the final branch run, made after the cgroup manager rule was
  added. Every branch suite matched the earlier comparison with `main`.
