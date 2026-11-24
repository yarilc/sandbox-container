# Proposal

## Why

Where the rootless engine applies no cgroup limits, as on the Windows Podman
machine with the `cgroupfs` manager, each container's process budget falls
back to `--ulimit nproc`:
- 512 for the agent and the session engine;
- 128 for the egress proxy.

The specs and `network/agent_budgets.py` state that this limit counts per
container, because Linux 5.14 and later count the process rlimit per user
namespace and keep-id gives every container its own.

The limit takes effect before the container's user namespace exists. The kernel
records the creator's limit on a new user namespace and checks it against the
parent level, where every container of the user is counted. Every fork in such
a container therefore counts the processes of all the user's containers.
Measured with nested rootless containers:
- a container limited to 100 could neither start nor fork while another
  container held 81 processes;
- with the limit set from inside the container after creation, it created 60
  processes beside the same 81, and stopped at 99 of 150 requested.

The Claude adoption's Windows validation failed this way: new sessions, proxy
checks and qualification stopped with `crun: clone: Resource temporarily
unavailable` once the operator's own session, its engine and the validation's
sessions were running. Sessions with an engine made it frequent. The defect
predates the engine: the scenario "Concurrent sessions have independent limits"
was never true on this fallback, and no test exercised it.

## What Changes

- **Limit set inside each container.** On the process rlimit fallback, the
  agent container, the egress proxy and the session engine no longer receive
  `--ulimit nproc`. Their first process sets the soft and hard process limit to
  the budget, then executes the container's program:
  - a fixed `/bin/sh` step for the agent (before the guard in restricted modes)
    and for the proxy;
  - the engine's entrypoint for the engine.

  The step stops the container if the limit cannot be set. The session still
  cannot raise the limit: it has no capabilities and no-new-privileges.
- **Verification.** Each launch requires the created container to carry that
  step with the selected budget, and no configured process rlimit. The
  proxy's effective limit is still measured before the agent starts. The
  engine's is measured through its readiness check. Setup smoke and
  restricted qualification still measure the agent's effective limit.
- **Independence tested.** Runtime tests start the agent, the proxy and the
  engine beside a container that holds more processes than their budget, and
  require each to start and create processes up to its own budget.
- **Documentation.** The README, `docs/network-contract.md`, `AGENTS.md` and
  the comments in `network/agent_budgets.py` and `launcher/core.sh` describe
  where the limit is set and why `--ulimit nproc` is not per container.
- **Unchanged.** When the `pids` controller is delegated, the cgroup limit
  stays the only process budget. When the kernel is older than 5.14, the
  process budget stays unenforced with its notice. Memory and CPU keep no
  fallback. The budget values do not change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: the process rlimit fallback is set inside the
  container by its first process, is independent of other containers, and is
  verified on the created container and inside it.
- `network-egress`: the proxy's process rlimit fallback is set inside the proxy
  and is independent of other containers.

The session engine's budgets follow the agent's rules by reference
(`session-container-engine`, "Engine budgets", in the active change
`replace-podman-delegation-with-session-engine`), so that requirement needs no
change.

## Impact

- Shared code: `launcher/core.sh` (budget arguments, entry step,
  verification), `network/session.py` (proxy arguments),
  `network/proxy_hardening.py`, `network/agent_budgets.py`,
  `launcher/engine/entrypoint.sh`, `setup/engine.py`, and `setup/setup.py`
  notices. `network/qualification_probe.py` and `setup/smoke.py` keep
  measuring the effective limit.
- Images: the engine image changes, because its entrypoint sets the limit. The
  agent and proxy images do not change.
- Tests: `tests/test_launcher.py`, `tests/fake_podman.py`,
  `tests/test_qualification.py`, `tests/test_engine.py`, and the runtime
  suites (`tests/test_runtime.py`, `tests/test_network_runtime.py`) in every
  wrapper.
- Qualification: the hardening identity changes, so existing installations
  requalify at their next setup.
- Release: a new reference tag, then the Claude adoption moves to it before its
  Windows validation is repeated.
