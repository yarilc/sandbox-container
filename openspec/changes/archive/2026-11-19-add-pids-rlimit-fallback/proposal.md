# Proposal

## Why

When the rootless engine does not delegate the cgroup v2 `pids` controller, the
agent container runs with no process limit at all (`--pids-limit=-1` and a
notice). A runaway process tree can then exhaust the kernel PID space of the
engine host. On WSL2 that kernel is shared by every distribution, so one
session can take down all of them. It also affects Linux hosts without a
systemd user session. `RLIMIT_NPROC` needs no cgroup delegation and can bound
the process count in that case.

The Podman machine on Windows is worse. Podman 6.1.4 with the WSL provider runs
without systemd as PID 1 and uses the `cgroupfs` manager. On cgroup v2 it
reports every controller (`[cpuset cpu io memory hugetlb pids rdma]`) but
applies none of them to rootless containers: `--memory`, `--cpus` and
`--pids-limit` are accepted, recorded in `HostConfig` and silently ignored.
The launcher trusts the reported controllers and its launch check compares
only the configured values. Every session there therefore runs without any
budget, and no notice says so. A rootless engine applies cgroup limits only
through the `systemd` cgroup manager, so the reported controllers must count as
delegated only with that manager.

The Windows Podman machine support that motivates this change is developed
separately on a dedicated branch. This fallback is platform independent, so it
lands on `main` first and reaches every wrapper through the normal reference
propagation.

## What Changes

- A controller counts as delegated only when the verified rootless engine
  reports it **and** uses the `systemd` cgroup manager
  (`.Host.CgroupManager`). With `cgroupfs` or any other manager, no cgroup
  budget is requested for the agent or the proxy. Memory and CPU are announced
  as unenforced, naming the cgroup manager, and the process budget follows the
  rlimit fallback below. An unverifiable manager value stops startup before
  image operations.
- When the verified engine does not delegate the `pids` controller, the agent
  container is created with `--ulimit nproc=N:N`, where `N` is the selected
  process budget (`SANDBOX_CONTAINER_PIDS_LIMIT`, default 512). This replaces
  the current unlimited `--pids-limit=-1`. When `pids` is delegated, the cgroup
  limit remains the only mechanism, as today.
- The session proxy gets the same fallback for its fixed 128-process budget,
  because it runs with the same identity mapping and loses its process limit
  in the same way.
- The fallback is admitted only when the engine host counts the process rlimit
  per container. On kernels that count every process of the host user, it
  would be shared with the user's own processes and across sessions. There the
  process budget stays unenforced, as today, and the notice says why.
- The process budget gains an enforcement mechanism (`cgroup` or `rlimit`). The
  memory and CPU budgets have no equivalent fallback and stay unenforced, with
  their existing notice, when their controllers are missing.
- The launch notice for the process budget now states that it is enforced
  through the process rlimit instead of the `pids` cgroup controller. It also
  says that the limit counts tasks, threads included, of the session user
  inside the container.
- The post-create verification requires the soft and hard `nproc` ulimit in
  the created container to equal the selected budget when the fallback is
  used. Setup smoke and the restricted qualification probe measure the
  effective `RLIMIT_NPROC` inside the agent container instead of `pids.max`.
- The qualification identity records the enforcement mechanism of the process
  budget. A change between `cgroup` and `rlimit` requires requalification.
- README and wrapper help describe the fallback and its semantics. The limit is
  per session. The agent cannot raise it, because capabilities are dropped and
  no-new-privileges is set. Its usable capacity is slightly below `N` because
  of container startup tasks.

Evidence from a spike on Podman machine 6.1.4 (WSL provider, kernel
WSL2 x86_64, `--userns=keep-id`, `--ulimit nproc=64:64`): two concurrent
containers each reached 49 background processes before fork failed. The count
is therefore per container, not shared. About 13 slots are taken by startup
tasks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: "Agent containers have explicit resource budgets"
  applies cgroup budgets only for delegated controllers, and a new requirement
  defines delegation through the `systemd` cgroup manager. The process budget
  gains the rlimit fallback when `pids` is not delegated. "Resource budgets are
  verified, not assumed" verifies the ulimit and measures the effective
  `RLIMIT_NPROC` in that case.
- `container-launcher`: "Unenforced budgets are announced" names the cgroup
  manager when it is the reason and changes the notice for the process budget
  under the fallback. "Qualification binds agent hardening settings" binds the
  process-budget enforcement mechanism.
- `container-setup`: "Saved budgets govern managed launches and verification"
  makes the setup plan name the fallback and the smoke compare the effective
  rlimit with the saved budget.
- `network-egress`: "Session proxies have enforced resource budgets" applies
  only delegated controllers, and the 128-process budget falls back to the
  process rlimit under the same conditions as the agent's.

## Impact

- Shared code, which needs a new `sandbox-ref` tag and adoption by the five
  wrappers: `launcher/core.sh` (budget arguments, notice, post-create
  verification), `network/agent_budgets.py` (enforcement mechanism),
  `setup/` (plan and smoke), and the qualification probe and records
  (identity and effective-limit measurement).
- Shared tests: `tests/test_launcher.py`, `tests/fake_podman.py` (controller
  subsets and `HostConfig.Ulimits`), setup and qualification tests.
- Proxy code: `network/session.py` (proxy budget arguments and notice) and
  `network/proxy_hardening.py` (configured and effective proxy limits).
- Restricted installations requalify after adopting the release, as for any
  change to qualified code. On hosts without `pids` delegation the identity
  also changes because the process budget becomes enforced.
- Engines with the `cgroupfs` manager change visible behavior. Their memory and
  CPU budgets were never applied, and are now announced as unenforced. Their
  process budget becomes the per-session rlimit.
- `README.md`, wrapper help and `docs/validation.md`, with a native Linux
  measurement in addition to the WSL spike.
