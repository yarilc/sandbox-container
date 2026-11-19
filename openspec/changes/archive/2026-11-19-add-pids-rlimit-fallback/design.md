# Design

## Context

See proposal.md for the motivation. Today the controllers reported by the
verified engine (`.Host.CgroupControllers`) decide each budget on its own:

- `launcher/core.sh` (`core_engine_session`) builds the agent budget arguments.
  It passes `--pids-limit=-1` when `pids` is missing, to override any
  `containers.conf` default, and prints one notice per missing controller.
  After creation it checks `HostConfig.{Memory,NanoCpus,PidsLimit}`.
- `network/agent_budgets.py` holds the same validation rules in Python
  (`enforced()` and `agent_hardening()`). A shared test feeds identical cases to
  the Bash and Python implementations.
- `network/session.py` builds the proxy budget (128 processes, 256 MiB). It
  verifies the result through `network/proxy_hardening.py`: a `probe` inside
  the proxy and a host-side `verify`.
- `setup/smoke.py`, `network/qualification_probe.py` and `proxy_hardening.probe`
  measure the effective cgroup v2 limits (`pids.max`, `memory.max`,
  `cpu.max`) inside the containers.
- `network/qualification_records.py` binds the agent hardening record and the
  proxy `enforced` list into the qualification identity. That identity already
  contains the validated engine kernel string and the digests of the shared
  code.

Every agent and proxy container runs with `--userns=keep-id` as the caller's
UID, with all capabilities dropped and no-new-privileges set.

## Goals / Non-Goals

**Goals:**
- One rule, implemented once in Bash and once in Python and checked against
  each other by the shared tests, that decides the mechanism enforcing the
  agent and proxy process budgets.
- Fail-closed verification of the fallback, both configured and effective,
  equivalent to the existing cgroup checks.

**Non-Goals:**
- Setting a process rlimit when `pids` is delegated (no defense-in-depth
  doubling).
- Compensating the startup-task overhead in the selected value.
- Any change to budget validation, defaults or setup questions.
- Platform support for Podman machine. That is a separate change on its own
  branch.

## Decisions

### D0. Delegation requires the systemd cgroup manager

The engine's controller list is not evidence of delegation by itself. Podman
machine 6.1.4 on WSL uses `cgroupfs` on cgroup v2 and reports
`[cpuset cpu io memory hugetlb pids rdma]`. Its rootless containers still get
no `memory.max`, `cpu.max` or `pids.max` interface, and the requested limits are
only recorded in `HostConfig` (see `docs/validation.md`). The rule is therefore:
the delegated controllers are the reported ones when `.Host.CgroupManager` is
`systemd`, and none otherwise. `network/agent_budgets.py` gains
`delegated(controllers, manager)`, which validates the manager value
(`[a-z]{1,32}`, single record) and otherwise raises `ControllerError`.
`launcher/core.sh` gets the same rule. Every consumer (launcher, proxy
session, setup plan and smoke, qualification) derives `enforced` and the
process mechanism from the delegated set, never from the raw report. The
cgroup manager is already part of the qualification engine configuration.

Alternatives considered:
- **Measure the effective limits at every launch** (a probe container, or the
  started container's cgroup read from the host). Rejected for this change. It
  costs one container or host read per launch, and a wrapper running inside
  another container cannot read the host cgroup tree. It remains a possible
  follow-up that would also catch engines that misreport in other ways.
- **Trust the reported controllers** (today's behavior). Rejected: it reports
  budgets as enforced on an engine that applies none.

### D1. A single mechanism rule: `cgroup`, `rlimit` or `none`

`network/agent_budgets.py` gains a pure function `process_mechanism(controllers,
kernel)`, and `core.sh` gets a Bash equivalent:

1. `pids` among the delegated controllers (D0) gives `cgroup`.
2. Otherwise, a kernel string whose leading `major.minor` is at least `5.14`
   gives `rlimit`.
3. Otherwise, including a kernel string that cannot be parsed, it gives `none`.

The same function serves the agent and the proxy, so they cannot diverge. The
shared Bash/Python consistency test gains cases for kernel strings: WSL
(`6.6.87.2-microsoft-standard-WSL2`), distribution suffixes, `5.13.x`,
`5.14.0` and malformed values.

Alternatives considered:
- **Startup probe** (spawn processes under a small rlimit and infer the
  counting semantics). Rejected. The ~13-task startup overhead seen in the
  spike is unexplained, so any threshold is fragile. Detecting shared counting
  needs the user's host process count, which a wrapper running inside another
  container cannot see. It also costs one extra container per launch.
- **Kernel gate.** Chosen. Since Linux 5.14 (`ucounts`), `RLIMIT_NPROC` is
  counted per user namespace, and `keep-id` gives each container its own. A
  backport into an older version number only produces a false negative, which
  keeps today's behavior. No kernel numbered 5.14 or later lacks this
  semantics.
- **Fallback regardless of kernel.** Rejected. On shared-counting kernels the
  limit includes the user's desktop processes, and sessions could fail to fork
  at all. That is safe but unusable.

### D2. Kernel and cgroup manager come from the launch engine

The rule reads `.Host.Kernel` and `.Host.CgroupManager` from the verified
engine, because the engine host is the one that counts and applies limits. The wrapper may run inside another container on
the same host, or later inside a Podman machine distribution. `core.sh` adds one
single-record query each for the kernel and the manager, next to the
controller query. `session.py` and
`setup/setup.py` read the same field when they read the controllers.
Qualification uses the kernel already validated in the platform record.

### D3. Container arguments

- Agent with `rlimit`: `--pids-limit=-1 --ulimit nproc=N:N`, where `N` is the
  selected `PIDS_LIMIT`.
- Proxy with `rlimit`: `--pids-limit=-1 --ulimit nproc=128:128`.
- `--pids-limit=-1` stays in place to neutralize a `containers.conf` default.

The soft and hard values are equal. Without `CAP_SYS_RESOURCE` the hard limit
cannot be raised, and no soft headroom is left to use.

### D4. Verification

- **Configured.** The agent check additionally reads the `RLIMIT_NPROC` entry
  of `HostConfig.Ulimits` (`{{json .HostConfig.Ulimits}}`, parsed by name). With
  `rlimit` it requires exactly one such entry, with `Soft == Hard == N`, and a
  `PidsLimit` of `0` or `-1`. With `cgroup` or `none` it does not constrain that
  entry. Rootless Podman may add a default `nproc` rlimit inherited from the
  user's own limits, and that is not a budget. The proxy's host-side
  `verify` gets the same rule with `N = 128`.
- **Effective.** `setup/smoke.py`, `network/qualification_probe.py` and
  `proxy_hardening.probe` read the `Max processes` row of `/proc/self/limits`
  (the proxy probe uses `/proc/1/limits`). With `rlimit` they require both
  values to equal `N` and the `pids.max` interface to be absent or `max`.
- Any mismatch fails closed with the existing ownership-confirmed cleanup and
  names the process rlimit fallback in its diagnostic.

### D5. Identity and record shape

The `enforced` lists keep their meaning: the cgroup controllers applied. The
agent hardening record gains `process: "cgroup"|"rlimit"|"none"`, and the
proxy hardening record gains `process` alongside its `enforced`. A change of
mechanism changes the identity and requires requalification. Keeping
`enforced` unchanged avoids touching the comparisons and notices for memory and
CPU.

### D6. Notices

A budget whose controller is reported but not delegated names the manager:
"agent memory budget not enforced: the rootless engine uses the cgroupfs cgroup
manager, which applies no cgroup limits". The same reason replaces "cgroup
controller pids is not delegated to the rootless engine" in the process-budget
lines below. Each existing notice site prints one line per process budget:
- `rlimit`: "agent process budget enforced through the process rlimit (N tasks
  of the session user, threads included): cgroup controller pids is not
  delegated to the rootless engine". The proxy line is the same, with `proxy`
  and 128.
- `none` without `pids`: the existing "not enforced" line, followed by the
  reason the fallback was not applied: "kernel <k> counts the process rlimit
  per user, not per container (Linux 5.14 or later is required)", or
  "unrecognized kernel version <k>".

The README "Hardening, budgets and lifetime" section and the wrapper help
replace the sentence "a budget whose controller is missing is not enforced"
with the fallback rule. They also state the per-session scope, the startup-task
overhead and that memory and CPU have no fallback.

## Risks / Trade-offs

- [A rootless `cgroupfs` engine with a writable delegated cgroup subtree could
  apply limits, but now loses them] → The loss is announced and safe. Memory and
  CPU become unenforced and the process budget uses the rlimit. Measured
  `cgroupfs` engines (Podman machine on WSL) apply none.
- [Engines that misreport delegation in another way stay undetected at launch]
  → Setup smoke and restricted qualification still measure the effective
  limits. A per-launch effective check is a possible follow-up (D0).
- [A future Podman version reports `--ulimit` differently in `HostConfig`]
  → Verification reads the entries by name through an inspect template and
  fails closed. Servers 4.9.3 and 6.1.4 were measured with the same shape, and
  neither lists its inherited default.
- [The ~13-task startup overhead is unexplained and could vary between
  runtimes or versions] → The overhead is documented, not compensated. Very
  small budgets (for example `PIDS_LIMIT=16`) may leave few usable processes.
  Validation stays as it is, and the README names the effect.
- [`RLIMIT_NPROC` does not bind a process with `CAP_SYS_RESOURCE` or
  `CAP_SYS_ADMIN`] → Agent and proxy drop all capabilities and set
  no-new-privileges. Any future change that grants capabilities must revisit
  this.
- [`podman exec` processes, such as the proxy hardening probe, count toward the
  proxy limit] → The probe uses one task. The 128 budget leaves room, as it
  already does under the cgroup limit.
- [A distribution kernel numbered below 5.14 with the semantics backported
  loses the fallback] → This is today's behavior, and the notice states the
  reason.

## Migration Plan

1. Implement on `main` in the reference. Run the runner modes that
   `docs/propagation.md` requires for changes to `launcher/`, `setup/`,
   `network/session.py`, `network/proxy_hardening.py` and the qualification
   code: `--shared`, `--setup`, `--setup-runtime`, `--qualification`,
   `--guard` and `--network`.
2. Record measurements in `docs/validation.md`: a native Linux host with
   `pids` delegated (no change expected), an engine without `pids` on a kernel
   of 5.14 or later (for example the Podman machine WSL distribution, run
   manually with `unrestricted`), and the synthetic old-kernel path.
3. Tag `sandbox-ref-N` on the merge commit and propagate to the five wrappers
   with `tools/propagate.py` (dry run first, then `--apply`).
4. Restricted installations requalify through the normal setup update.
   Rollback uses setup's existing last-working-release rollback.

## Open Questions

- The origin of the ~13 startup tasks. It is not needed for correctness, only
  for the wording of the documentation.
