# Design

## Context

See proposal.md for the defect and its measurements. Current state:
- **Mechanism.** `network/agent_budgets.py` picks `cgroup`, `rlimit` or `none`
  per container, and `launcher/core.sh` mirrors the rule. `rlimit` applies when
  `pids` is not delegated and the kernel is 5.14 or later.
- **Where `--ulimit nproc` is added.** The launcher adds it for the agent and
  for the engine (`budget_args`). `network/session.py` adds it for the proxy.
- **Configured check.** `budgets_applied` in `launcher/core.sh` requires the
  agent and the engine to carry exactly one `RLIMIT_NPROC` at the budget in
  `HostConfig.Ulimits`. `network/proxy_hardening.py` requires the same of the
  proxy.
- **Effective check.** The proxy's limit is measured in the proxy (`/proc/1/limits`
  through an `exec`) before the agent starts. Setup smoke and the
  qualification probe measure the agent's inside the agent.
- **Entry programs:**
  - restricted agent sessions start the static guard as the entrypoint (built
    by `session.py agent-args`);
  - unrestricted ones start the image entrypoint, or `/bin/bash` in shell
    mode, under `--init`;
  - the proxy starts `python3 /opt/sandbox-egress/proxy.py`;
  - the engine starts `/usr/local/bin/sandbox-engine PORT` under `--init`.
- **Shells.** All four images have `/bin/sh`. The agent images use `dash`; the
  engine image's `sh` is `bash`, which reads no startup file as a
  non-interactive `sh`.

Kernel behaviour behind the defect: a new user namespace records its creator's
`RLIMIT_NPROC`, and a fork in that namespace is also checked against it one
level up, where every container of the user is counted. A limit in effect when
the container's namespace is created thus becomes a ceiling shared by all
containers. A limit set later by a process inside the namespace only bounds the
container and its descendants.

## Goals / Non-Goals

**Goals:**
- Make the process rlimit fallback per container for the agent, the proxy and
  the engine, as the specs already require.
- Keep every existing guarantee: the value, no raising, fail-closed, the
  notices, and the checks before the agent starts.

**Non-Goals:**
- Changing the mechanism choice, the budget values, or the `cgroup` and `none`
  paths.
- Bounding processes the host starts in a container with `podman exec`
  (see Risks).
- Bounding nested containers separately: the engine's limit still bounds the
  engine and everything it runs together (design D7 of the engine change).

## Decisions

### D1. A fixed `/bin/sh` step sets the limit and executes the entry program

On the `rlimit` mechanism, the container's entrypoint becomes:

```
/bin/sh -c '{ ulimit -u <budget> 2>/dev/null || ulimit -p <budget>; } && exec "$0" "$@"' <entry program> <arguments...>
```

Bash and BusyBox name the process limit `-u`. dash, the `/bin/sh` of the agent
and proxy images, names it `-p` and rejects `-u` (found during implementation).
In Bash, `-p` is the read-only pipe size, so the second form never sets
anything there. Without `-S` or `-H`, either form sets the soft and the hard
limit together, so it never fails on a soft limit above the new hard limit.
Measured in dash, Bash and BusyBox: both limits are set, and a value above the
hard limit fails. The budget is an integer validated before use. `exec` keeps
the entry program's PID, so the guard stays PID 1 in restricted sessions. If
neither form sets the limit, `&&` stops the container before the entry program
runs.

The step runs before the guard in restricted sessions. It runs no application
code: a trusted image's shell executes a fixed script built by the launcher,
which reads no startup file and calls nothing else.

Alternatives:
- **A guard option that calls `setrlimit`.** This would keep the guard first,
  but it covers only restricted sessions, and needs a guard revision, a
  rebuild and new guard tests. The proxy, the engine and unrestricted sessions
  would still need another mechanism.
- **`prlimit` from the host after start.** Not possible: the session is created
  and then started attached, and the agent would run before the limit.
- **An engine or runtime option to apply rlimits after the user namespace
  exists.** Neither Podman nor crun offers one.
- **Dropping the fallback.** Declined by the operator: a fork bomb would then
  be bounded only by the user's own limit, shared by the whole machine.

### D2. Who builds the step

- **Agent.** `launcher/core.sh` wraps the entry program after the session's
  options are complete:
  - in restricted modes, the `--entrypoint` that `session.py agent-args`
    returns (the guard);
  - in unrestricted agent mode, the profile's agent program in place of the
    image entrypoint;
  - in shell mode, `/bin/bash`.

  One function does this, so the qualification probe and setup smoke, which go
  through the same launch, get the same step.
- **Proxy.** `network/session.py` passes `--entrypoint /bin/sh` with the step and
  the proxy program: the proxy image's own entrypoint and default command, read
  from the immutable image, or the TLS qualification fixture's program. The
  step thus runs what the image would run by itself, including the derived
  images of the test fixtures (found during implementation). The proxy image
  does not change.
- **Engine.** `launcher/engine/entrypoint.sh` takes the limit as a second
  argument, after the port, and sets it the same way under `set -eu` before
  starting its services. A second shell would add nothing. The engine image
  changes.

### D3. Verification of the created container

`budgets_applied` and `network/proxy_hardening.py` change their rule for the
fallback:
- the created container's entry command (`.Path` and the first `.Args`) is the
  step with the selected budget;
- no `RLIMIT_NPROC` at or below the budget is configured. A higher one is the
  engine's default from the user's own limits and is accepted, as before. A
  lower one would make the step fail anyway.

The launcher reads the arguments one by one with `index`, which reads the same
on Podman 4.3 and 6.2 (`sandbox-ref-32`). The proxy check reads
`[{{json .Path}},{{json .Args}}]`, which both versions print identically
(measured). A container created with `--init`, as unrestricted sessions and the
engine are, reports `/run/podman-init` as `.Path` and `--` as its first
argument, before the entry command. A mismatch stops the launch as before.

Effective checks:
- **Agent.** Setup smoke and the qualification probe keep reading
  `/proc/self/limits`.
- **Proxy.** It keeps its check through `exec` of PID 1.
- **Engine.** The readiness check also reads the limit of the engine's service
  process, the entrypoint, PID 2 under `--init`. It requires the budget there
  before the session starts. A process started with `podman exec` has the
  engine-applied limits, so only an entry-process reading is evidence.

### D4. Tests that would have caught the defect

- **Runtime, agent.** A runtime case on the fallback starts a container with
  more processes than the session budget, then a session that creates
  processes:
  - it must reach close to its own budget;
  - it must stop there.
- **Runtime, proxy.** The same holds for the proxy: a provider session starts
  beside such a container.
- **Runtime, engine.** An engine case does the same for an engine session.
- **Unit.** The launcher and proxy fakes require the step, and refuse
  `--ulimit nproc`.

These run from a session through its engine. That nested engine uses
`cgroupfs` and therefore the fallback, the configuration the defect needs.

## Risks / Trade-offs

- [`podman exec` processes get the engine-applied limits, not the step's.] →
  Only trusted host-side tooling execs into these containers, such as the
  launcher's checks and the validation script. The agent has no engine socket
  for its own container. The README and the contract say so.
- [The `--init` process of unrestricted sessions and of the engine keeps the
  engine default.] → It only starts its one child and reaps; it forks nothing
  else.
- [An image without `/bin/sh` cannot start on the fallback.] → All shipped
  images have it, and the step fails closed. The runtime image checks keep
  `/bin/sh`.
- [A session that creates its own user namespace.] → The new namespace
  records the session's limit, so its processes still count against the
  session's budget at the session's level.
- [The machine as a whole is bounded only by the user's own limit, 63948 on
  the Windows machine.] → This is the documented consequence of per-session
  budgets. Each session's tree stays within its own budget.
- [Qualification identity.] → The changed files are in `SHARED_CODE`, so every
  installation requalifies at its next setup or launch.

## Migration Plan

1. Implement and test in `sandbox-container`.
2. Record the runner modes, then tag `sandbox-ref-34`.
3. Move the Claude adoption to the tag. The operator reruns setup on Windows,
   which rebuilds the engine image and requalifies, and then the validation
   script. The other wrappers adopt with their next reference update.

Rollback: the previous release keeps `--ulimit nproc`, and setup's
last-working-release rollback restores it with its own engine image tag.
