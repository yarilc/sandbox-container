# Interactive sandbox setup

The durable contract is [container-setup](../openspec/specs/container-setup/spec.md).
The [archived change](../openspec/changes/archive/2026-11-07-add-interactive-container-setup/)
retains the design, completed tasks and delta specifications.

Setup is the mandatory first step for new users. Run
`bash ./sandbox-container.sh --container-setup` from a reviewed checkout,
as the non-root Linux/WSL user who will use the sandbox. Podman and its rootless
dependencies must already be installed. Host Python 3, Bash and GNU coreutils
are also required. Setup needs terminal stdin/stdout; redirected answers and
combinations with launch flags or shell arguments are rejected. Help is always
available through `--container-help` without loading preferences or using Podman.

## Choices and preparation

The prompts cover network access, shared/fresh isolated state, delegation,
worktree scope, host CA trust, installation/command paths and the Podman
endpoint. The reference profile declares no authentication method and no
permission bypass, so network access offers only `offline` and `unrestricted`
and there is no authentication or permission-bypass question; a profile with
methods (the agent wrappers) also offers `provider`. First-run setup defaults to
offline mode, shared state, current workspace only, delegation off and CA trust
off. Accept defaults with Enter; invalid choices are requested again. Existing
saved choices are offered for review on rerun. The managed launcher applies the
saved network choice. A direct invocation with `SANDBOX_CONTAINER_NETWORK` unset
or empty uses `offline`, which needs a protected installation: from a checkout it
stops with setup guidance before engine queries or state creation. Setup is never
started automatically. An explicit empty network override on a managed
invocation selects the offline default instead of the saved choice. Offline
sessions have no external network.

Offline networking, provider networking and delegation need a same-host Unix
Podman service. Before the network question, setup checks, without changing
anything, whether a service answers at `CONTAINER_HOST`, at the saved endpoint
or at the default endpoint. It also checks whether a usable systemd user manager
(`systemctl --user show-environment`) could start the user `podman.socket`.

A Podman machine distribution on WSL has no systemd user manager, so neither
check succeeds there. In that case setup offers only unrestricted networking:

- it explains why, and asks `Continue with unrestricted networking?`, which
  defaults to no;
- it saves the local engine as the launch endpoint;
- it skips the delegation and endpoint questions.

A saved offline mode is never changed silently: setup states that it cannot be
kept and asks for the same confirmation. Declining ends setup without changes.
To keep offline networking, make a service available first, then rerun setup:

- start a foreground `podman system service` with a private runtime directory;
- or set `CONTAINER_HOST` to the `unix://` endpoint of an existing same-host
  service.

After the worktree question, setup asks for the agent budgets and lifetime:
`Agent memory limit` (default `4g`), `Agent CPU limit` (default `2`),
`Agent process limit` (default `512`) and `Session lifetime in seconds, 0
disables` (default `0`). Invalid answers are explained and asked again; `0`,
`-1`, `max` and unitless memory are rejected, so a budget cannot be disabled.
The setup plan lists the values. They are saved in schema 2 preferences and
supplied by the managed launcher as `SANDBOX_CONTAINER_MEMORY_LIMIT`,
`SANDBOX_CONTAINER_CPU_LIMIT`, `SANDBOX_CONTAINER_PIDS_LIMIT` and
`SANDBOX_CONTAINER_RUN_TIMEOUT` unless those are exported. Smoke and
qualification use the saved values. To change a budget, rerun setup; an
exported different value makes restricted launches stop until
`--container-qualify` is run with the same environment. Preferences saved by an
earlier release (schema 1) are read with the default budgets proposed.

Setup smoke and qualification run in a private temporary workspace, never in
the directory from which setup was started. Ordinary launches refuse sensitive
workspace roots such as `/`, your home, system directories and WSL drive roots
unless exact `SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` is set.

Operators can still invoke a manually prepared wrapper with explicit `offline`
or `unrestricted` mode. All existing prerequisites, protected paths,
qualification and authority checks apply. Image maintenance additionally
requires exact `SANDBOX_CONTAINER_MAINTENANCE=1`; that consent alone does not
select a mode. Help and standalone setup/qualification retain their own dispatch checks.
Standalone `--container-qualify` keeps its offline default when no mode is set
and can run only fixed controls, never a supplied command.

This repository took over the reference role from `claude-container`; its
history and earlier validation entries were recorded for the Claude wrapper.
The installation, command, state and image names differ from that wrapper, so
an existing Claude installation is untouched and this shell needs its own setup.

The toolchain library (`add-toolchain-library`) changes the wrapper and adds
`setup/toolchains.py` to the installed and qualified code, so rerun
`--container-setup` after upgrading. Setup does not manage toolchains: the
operator adds them with `--container-toolchain`, and every session mounts the
library read-only at `/toolchains` (see the README "Toolchains" section).

Setup and qualification refuse provider mode for this profile before any
image, proxy or container operation. The provider CONNECT/SNI binding, its
residual exfiltration notice and acknowledgement remain part of the shared
setup code for profiles with authentication methods; see the
[network contract](network-contract.md) and each agent wrapper's documentation.

Restricted modes admit native Linux and WSL2 x86_64 with usable Landlock ABI >= 3,
rootless same-host Unix Netavark/Podman >= 4.9 and standard OCI seccomp, followed
by mandatory local qualification. There are no exact kernel pins or server upper
bounds. Enabled SELinux/AppArmor is permitted without guaranteeing compatibility;
denials stop preparation while policies stay active. Setup diagnoses missing
Podman, UID/GID mappings/helpers, runtime directories and unsupported engines.
Fix those host prerequisites separately. Setup never installs host packages,
uses sudo, edits subordinate-ID mappings, enables lingering, changes WSL init,
disables security policy or silently selects unrestricted networking.

Every shell container, in every mode, drops all capabilities and enables
no-new-privileges. Setup smoke verifies zero capability sets, no-new-privileges
and the effective `memory.max`, `pids.max` and `cpu.max` in every mode.
Setup adapts to the cgroup v2 controllers the rootless engine delegates
(`podman info --format '{{.Host.CgroupControllers}}'`). Reported controllers
count as delegated only with the `systemd` cgroup manager
(`{{.Host.CgroupManager}}`): a rootless `cgroupfs` engine, such as a Podman
machine on WSL, reports every controller and applies none, so the plan prints
`enforced agent budgets: none` and names the `cgroupfs` manager. A budget whose
controller is not delegated is not enforced: the setup plan, the smoke and every
launch name it, and setup continues without asking. Without `pids`, the process
budget falls back to a per-session process rlimit at the saved value when the
engine kernel (`podman info --format '{{.Host.Kernel}}'`) is Linux 5.14 or
later. The plan then prints
`agent process budget enforced through the process rlimit (512 tasks of the session user, threads included)`,
and the smoke compares the effective `Max processes` with the saved budget. On
older or unrecognized kernels the plan line names the reason the fallback was
not applied. Enforced budgets are still verified exactly, unenforced ones must
be absent, and the enforced set and the process-budget mechanism are bound into
restricted qualification. Without memory or process budgets an agent can
exhaust host memory or processes for your user; without a CPU budget it can
saturate every CPU.
The installed wrapper verifies the effective limits before its smoke shell
starts. An ignored delegated limit or an incompatible image
makes setup incomplete and preserves the previous working release. Setup never
adds privileges, changes host security policy or asks for host changes.

Before activation, setup runs `--container-qualify` against its protected
candidate using fixed disposable IP/IPC/TLS controls and no real credentials.
Only a complete passing result is published atomically under the release's
private `qualification/` directory. A failed or interrupted candidate keeps the
previous release selected. Authentication remains a separate status.

Existing managed installations must rerun setup. Manually prepared installations
can invoke `--container-qualify` alone with their existing explicit environment
configuration; this command never starts an ordinary shell session or grants
maintenance. Help and unrestricted launches do not require a report.


Reports bind kernel/boot, ABI, engine/backend/security artifacts, protected code,
immutable images, selected policy/profile, CA trust and hardening. Relevant changes
require requalification. Unobservable active LSM policy state forces a new gate
each ordinary launch rather than unsafe reuse. Missing/stale/unsafe reports and
unavailable required controls block launch; permissions are not repaired.
Setup distinguishes `locally-qualified` from an exact `release-measured` record.
Local success is not a claim about every native distribution, LSM or auth flow.

For restricted launch or optional delegation, setup verifies the selected
same-host rootless Unix service. `default` derives the socket from the current
`XDG_RUNTIME_DIR` (or `/run/user/<uid>`) on every invocation; an explicit
`unix:///absolute/socket` is retained literally. `local` is available for
unrestricted launch without delegation. TCP/SSH, named contexts and implicitly
remote engines remain unsupported. Bind/build paths must exist at their real
absolute paths on that same Linux host, including when running from a container.

When available, setup can run `systemctl --user enable --now podman.socket`
after separate confirmation. This persistent user-service change does not
delegate the socket to the application. Without a working user manager, setup
prints foreground `podman system service --time=0` instructions and stays
incomplete until an endpoint is verified. It does not leave a background daemon
or repair an administrator-owned `/run` directory. A service enabled before
later cancellation is reported and retained, since other clients may use it.

Review the settings and image plan before approving preparation. A separate
refresh question allows rebuilding prepared images/guard. Builds and pulls are
host maintenance: their network traffic, including build-time package downloads,
is outside runtime egress filtering even when the chosen session mode is offline.
Preparation needs outbound HTTPS (443) to the container registry (`docker.io`),
Debian (`deb.debian.org`), Alpine (`dl-cdn.alpinelinux.org`) and npm
(`registry.npmjs.org`); it does not need port 80. Debian packages are fetched
over verified HTTPS, so hosts that block plain HTTP can still build. On networks
that intercept TLS, answer yes to host CA trust and select a bundle containing the
interception CA: setup passes it to the runtime image and guard toolchain builds
as a non-persisted build secret. Without it, such builds fail with a certificate verification error.
Consent grants exact maintenance authorization only to these preparation
commands. It is not saved or enabled for subsequent ordinary launches.

Every mode needs a runtime image; offline mode also needs the static guard and
its digest manifest. Setup reuses inspected artifacts when suitable and prepares
missing ones from the existing recipes. Compiler tools are installed only in the
pinned toolchain image. Compilation uses that immutable image without
networking. Failed recipe/package acquisition does not change pins
automatically; resolve the reported maintenance stage and rerun. Unrestricted
mode skips the guard and toolchain.

## Managed installation and launch

Default paths:

- Installation: `$HOME/.local/lib/sandbox-container` on native Linux storage.
- Command: `$HOME/.local/bin/sandbox-container`.
- Optional fresh isolated home: `$HOME/.local/share/sandbox-container/home`.

Source may be on a Windows mount; installation, private state and executable
guard output need permission-enforcing native storage with protected ancestors.
Setup copies an explicit input manifest, never a whole checkout or credentials.

Every manifest input must have LF line endings. Bash cannot run a script with
CRLF line endings. Setup refuses an input that contains a carriage return,
names the file, and creates no release. The repository's `.gitattributes`
keeps scripts LF even when Git for Windows has `core.autocrlf=true`. However, a
clone made before that file existed keeps its CRLF working files. In such a
checkout without local changes, rewrite the files with LF:

```bash
git rm -r -q --cached . && git reset --hard
```

Cloning the repository again works too. `git add --renormalize .` does not
help: it fixes the index, not the working files.

Group/other-writable ancestors, unsafe existing modes and paths overlapping the
writable workspace/worktree/state are rejected without recursive repairs.
An existing safe flat manual installation can coexist with managed releases.
An absent installation directory is created with mode `0700`. An existing
caller-owned `0755` installation root is accepted without changing its mode:
installation code requires write protection, while credential/state directories
and managed releases retain their private permission checks. Invalid ownership
or inaccessible existing roots are diagnosed before maintenance confirmation.

The configuration directory, or the isolated state directory, must belong to
the caller, permit read/write/traverse access and deny all group/other
permissions. Whether shared directories (the profile's `native.shared_dirs`;
here `~/.config/openspec`) must also be private depends on the optional
profile field `native.private_shared_dirs`:

- `false`, the default and this shell's value: shared directories are created
  privately when missing and must be accessible. Existing modes are kept.
- `true`: the wrapper refuses non-private shared directories. Setup then checks
  them the same way as the configuration directory, before any image work.

A refusal names the path and the reason: not a directory, another owner,
missing access, or group/other permissions with the observed mode. Setup never
changes permissions itself; for example, a host tool that created a directory
with mode `755` is reported with the fix `chmod 700 <path>`, or with native
Linux storage when the filesystem does not enforce Unix modes. The setup
summary calls a state directory `private` only when it passed this check;
other directories are listed as `shared`.

Each `releases/<id>/` contains its runtime/setup/build inputs and private
versioned `setup.json`. `current` selects the active release. Setup holds
`.setup.lock` during preparation/activation and publishes the pointer only after
the candidate smoke check passes. A failed candidate is removed; the last
working release and credential state are preserved. Concurrent setup fails with
a busy message. Remove a stale empty `.setup.lock` only after confirming that
no setup process is active. An unrelated command file or reserved-path symlink
is never overwritten.

Use the absolute completion command, or add its directory to PATH yourself:

```bash
cd /path/to/my-project
"$HOME/.local/bin/sandbox-container"
"$HOME/.local/bin/sandbox-container" -c 'git status'
"$HOME/.local/bin/sandbox-container" --container-setup
```

Setup does not edit shell startup files. If the command directory is absent from
PATH, the plan and completion output
show a shell-quoted `export PATH=/absolute/command/directory:"$PATH"` command and
suggest adding that line to the appropriate shell startup file for persistence.
The managed command loads validated
non-secret JSON and execs the installed wrapper; preferences are never sourced
as shell code. It preserves current directory, stdin, arguments, terminal and
exit/signal handling. Settings provide defaults only for variables absent from
the environment. Explicit values, including empty values, take precedence and
must pass normal validation. A nonempty `SANDBOX_CONTAINER_CONFIG_DIR` conflicts with an
isolated home; unset it deliberately rather than expecting setup to discard it.

The installation and command remain outside writable mounts on every managed
launch, including unrestricted mode. A future worktree parent containing them
is rejected with relocation guidance. Rerun setup to change saved workspace
scope, or invoke the installed wrapper directly for per-invocation choices.
The invoked command's own path is checked as well as the configured path,
including relative invocation, copied dispatchers and symlink aliases. A command
or alias inside the effective writable workspace/state is rejected before launch.
When setup changes the managed command path, it retires the previous owned
command after publishing the new one. A retirement/publication failure restores
the previous activation and leaves the previous command intact. The plan names
the command to be retired; unrelated files are never removed.

Existing dispatchers from before this path-check protocol are upgraded
atomically by setup. Such a dispatcher can still request help/setup, but normal
launch against the new helper fails closed until the upgrade. Run setup from the
updated checkout to install both matching components; no image refresh is needed.
Direct `sandbox-container.sh` retains its existing environment-based behavior and
does not load a global configuration. Managed help bypasses preferences and
Python, including when preferences are corrupt. Setup rerun uses saved choices;
to repair invalid JSON, first review/restore the affected file or use a reviewed
checkout and a different installation root.

Rerunning from the installed command reconfigures that installed source version.
To install updated source, run setup from the reviewed updated checkout and
select the same installation root. Runtime images use distinct candidate tags;
proxy references are immutable IDs. An explicitly authorized ordinary
`--container-build` still operates on the selected named runtime image and is
separate from setup's release transaction.

The previous release is retained. For rollback, stop setup updates, take the
same installation lock, inspect the previous release and its `setup.json`, then
atomically replace `current` with a symlink to that release. Alternatively run
the prior manual wrapper with its explicit environment. Never delete state to
roll back. Automatic pruning is not provided. New image tags and enabled user
sockets can remain after failure; setup reports persistent effects and does not
remove shared engine resources or undo service enablement automatically.
If rolling back across a command-path or dispatcher-protocol change, restore
the matching command/configuration as well; changing only `current` does not
recreate a retired command or adapt an older launch helper's interface.

## Windows with Podman machine

On Windows, setup runs from the checkout through the PowerShell entry, in an
interactive window:

```powershell
.\sandbox-container.ps1 --container-setup
```

The entry first checks these things, and stops with status 1 when one fails:

- `sandbox-container.sh`, `launcher/core.sh` and `agent/launcher.sh` have LF
  line endings; the message names the first file with CRLF and the command
  above;
- the WSL distribution is registered: `podman-machine-default`, or
  `SANDBOX_CONTAINER_WSL_DISTRO`;
- the distribution is running: start the machine with Podman Desktop or
  `podman machine start`. The entry never starts it with `wsl.exe`;
- the user's runtime directory `/run/user/<uid>` exists and is writable in the
  distribution. Podman creates it when it starts the machine. A distribution
  that `wsl.exe` alone started lacks it, and no `podman` command works there
  (status 125). Run `wsl --terminate podman-machine-default`, then start the
  machine with Podman.

It then runs `bash sandbox-container.sh --container-setup` inside that
distribution as its user (`user`, or `SANDBOX_CONTAINER_WSL_USER`), starting in
the checkout's drive mount, for example `/mnt/c/Work/sandbox-container`. No
Windows variable is forwarded to setup.

Setup then works as on Linux:

- the checkout on drvfs is only the source; the installation, the command and
  the state go to the distribution's native storage, at the default paths
  above;
- the distribution has no launch service, so setup offers only unrestricted
  networking (see [Choices and preparation](#choices-and-preparation));
- the images are built by the machine's engine.

After a successful setup the entry says to start sessions with
`sandbox-container.ps1` from a project directory. A launch looks for the
installation at `~/.local/lib/sandbox-container` in the distribution. When
setup installed it elsewhere, set `SANDBOX_CONTAINER_WSL_INSTALLATION` to that
absolute path. When the machine is recreated, the installation is gone, and a
launch asks to rerun setup.

## Readiness and authentication

Setup smoke-checks the actual installed wrapper with the selected state, network
and CA settings, without credentials in its environment. It checks the Bash
shell; offline smoke also exercises enforced Unix socket denial, direct egress
denial and own-loopback/pair compatibility. ABI query success alone is not
accepted. Failure prevents activation and returns nonzero.

When the smoke launch fails, or does not confirm readiness, setup prints the
last lines of the wrapper's standard error, labeled `sandbox-container: smoke:`,
before `setup incomplete`. For example, a wrapper refusal of a state directory
appears there. The excerpt holds at most 5 non-empty lines of at most 2048
characters, with control characters removed. A successful smoke prints none of
it, so routine wrapper notices stay hidden.

Completion distinguishes:

| Result | Meaning |
| --- | --- |
| `Sandbox: ready`, authentication not applicable | Installation and smoke passed. The reference profile has nothing to authenticate. |
| setup incomplete | A prerequisite/preparation/smoke step failed. Setup returns nonzero and leaves the last activated release selected. |

Profiles with authentication methods (the agent wrappers) add login assistance
and a separate authentication status here; the reference shell never asks for
a login or a key.

The wrapper reclassifies Podman 4.3's successful `Should restart: false` message
as informational (`INFO[...]` or `level=info`), preserving its timestamp and
message. All other stderr bytes, including actual restart-check errors, remain
unchanged; interactive prompts do not wait for a newline. The host-side adapter
is installed by setup and its owned process shares the wrapper shutdown budget.
Legacy direct unrestricted installations lacking host Python or the adapter keep
their original Podman diagnostics instead of gaining a Python prerequisite.

## Verification

Synthetic tests use fake engines, PTYs and disposable native state:

```bash
python3 -m unittest discover -s tests -p test_setup.py -v
bash tests/run-runtime.sh --setup       # container-provided Python/native storage
bash tests/run-runtime.sh --setup-runtime  # opt-in real rootless setup acceptance
bash tests/run-runtime.sh --qualification  # installed-path gate and report checks
```

Runtime checks use existing prepared images, disposable installation/state and
an existing same-host service; they do not enable user services or access real
credentials. Real systemd activation requires a user to accept its setup
prompt. Record unexercised variants as unavailable in `docs/validation.md`.

The `container-setup` requirement coverage is:

| Requirement | Verification |
| --- | --- |
| Dedicated interactive setup invocation | PTY early-dispatch, mixed-argument/pipeline rejection and help precedence tests |
| Workflow questionnaire with explicit defaults | Default/retry/conflict PTY checks; fixture profiles with and without methods; saved-choice rerun; real offline/unrestricted paths |
| Setup without a launch service offers only unrestricted networking | Probe order and user-manager unit tests; confirmed, declined and saved-offline questionnaires; real-wrapper PTY run with a failing `systemctl` |
| Optional authority requires deliberate selection | Delegation conflict questionnaire; separate service confirmation; saved worktree/TTY checks |
| Installed host prerequisites only | Missing command, unsupported context/platform and strict failed/malformed engine-response tests |
| User-scoped Podman service preparation | Synthetic accepted/declined/unavailable systemd and exact-endpoint tests; real existing-service reuse |
| Reviewed setup mutations and maintenance | Declined plan has no filesystem/image mutation; scoped maintenance/environment tests |
| Protected complete installation | Native manifest copy from Windows checkout; path/ancestor/overlap/state/privacy checks |
| Installation inputs with carriage returns are refused | CRLF manifest input refused before a release exists, with the LF re-checkout command |
| Mode-specific image and guard preparation | Inspection/recipe pin/build failure/guard preflight tests; real compilation and offline/unrestricted smoke |
| Persistent non-secret managed launch preferences | Schema/privacy/secret rejection, empty overrides, argv/stdin/cwd/TTY/status/signal and future-mount tests |
| Credential-preserving authentication assistance | Fixture-profile login success/failure/cancellation and absent-key cases; no-method profile skips authentication |
| Verified readiness with separate authentication status | Actual installed guard, CA off/on, shell smoke and not-applicable authentication |
| Repeatable setup with owned recovery | Lock/publication/interruption/container cleanup tests; real rerun and failed-candidate rollback |

Adversarial regression checks additionally cover managed-command relocation,
retirement failure/rollback, legacy dispatcher upgrade and writable aliases.
Timeout checks include an already-exited group leader and a descendant that
closes pipes on TERM while continuing to run. Tests use a separate Linux
subreaper to collect their own orphaned descendants without leaving zombies.
