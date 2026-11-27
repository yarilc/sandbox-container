# Sandbox shell in Podman

`sandbox-container.sh` opens a Bash shell in a read-only, rootless Podman
container with every sandbox feature of the agent wrappers: the protected
offline bootstrap (Landlock and seccomp), local qualification, guided setup,
resource budgets, private state, the toolchain library, host CA trust and a
private container engine for container-based tests. Sessions are **offline by default**;
`SANDBOX_CONTAINER_NETWORK=unrestricted` opens ordinary networking on request.

This repository is the **reference** for the shared sandbox components
(`network/`, `setup/` and the shared tests). The Claude, Codex, OpenCode, Pi and
Antigravity wrappers adopt them from tagged releases; see
[Shared sandbox components and the reference role](#shared-sandbox-components-and-the-reference-role).
It replaces the Claude wrapper only in that role: existing agent installations
are unaffected.

## Enable rootless Podman on the host

Setup is the mandatory first step for new users. Run this from a reviewed
checkout on the Linux/WSL host as the non-root user who will run the sandbox:

```bash
bash ./sandbox-container.sh --container-setup
```

Setup requires an interactive terminal, installed rootless Podman, host Python 3
and GNU coreutils. It asks how you want to work, explains network/state/authority
choices and prepares a protected native installation plus a managed launch
command. The first-run defaults are offline networking, shared shell state and
disabled optional authority; there is no authentication to configure. Setup
does not install Podman or any other host package. The following manual steps
remain available for prerequisite preparation and troubleshooting.

After setup, use the managed launch command it prints from your project
directory. It supplies the saved runtime mode. `offline` is the default when no
mode is set; an offline launch from a location without a protected installation,
such as this checkout, exits with setup guidance before contacting Podman or
creating state. Setup never starts automatically. Operators can still select
`unrestricted` explicitly for direct use and maintenance; offline sessions
retain all protected-path, guard and qualification checks.

See the [guided setup reference](docs/setup.md) for saved preferences, image
preparation, reruns/rollback and separate sandbox/authentication readiness.

When a Unix service is required, setup reuses the selected same-host rootless
endpoint or offers `systemctl --user enable --now podman.socket` with separate
confirmation. This enables a host launch service only: no session ever receives
a host Podman socket. No `sudo`, lingering or WSL/system-wide
configuration changes are performed. Without a working user manager, setup gives
foreground-service instructions below and stays incomplete until that endpoint
is verified. A socket file by itself is not sufficient. Missing rootless UID/GID
mappings or helpers must be addressed outside setup; `podman info` must succeed
as the intended non-root user.

Run this setup on the Linux host (or inside your Linux/WSL distribution),
using the same non-root account that will run `sandbox-container.sh`.
Install Podman and its rootless dependencies using your distribution's
[installation instructions](https://podman.io/docs/installation).
The account needs subordinate UID/GID ranges in `/etc/subuid` and
`/etc/subgid`, the `newuidmap`/`newgidmap` helpers, and a rootless networking
backend supported by the installed Podman version. If these are missing,
complete the administrator steps in the
[rootless setup guide](https://github.com/podman-container-tools/podman/blob/main/docs/tutorials/rootless_tutorial.md)
before continuing.

The host also needs GNU coreutils, including GNU `timeout` with kill-after
support. The wrapper checks this prerequisite before session operations;
`--container-help` remains usable without it.

Check that local rootless Podman works:

```bash
podman info --format '{{.Host.Security.Rootless}}'
podman run --rm docker.io/library/alpine:latest id
```

The first command must print `true`; the second must successfully start a
container. Root inside that container is normal for rootless Podman.

## Enable the launch service

Restricted networking currently requires the tested same-host Unix launch
service. An unrestricted local session needs no API service. Host Podman is
always required for image operations and launch. See the network setup below
for the protected installation required by restricted modes.

Every session verifies that its launch engine is Linux and rootless before
image inspection, build, or launch. Unrestricted local Podman needs no API service.
An explicit same-host Unix `CONTAINER_HOST` is also supported, including when
this wrapper runs inside another container; launch verification then queries
that service, which never reaches the session.
Named `CONTAINER_CONNECTION` contexts, implicit remote contexts, TCP/SSH
(including the Podman machine connection that `podman.exe` uses), and rootful
engines are unsupported. On Windows, the PowerShell entry runs the sandbox
inside the Podman machine instead; see
[Windows with Podman machine](#windows-with-podman-machine). All bind sources and build
paths must exist on the same Linux host at their original absolute paths.
Unix transport alone does not prove that a forwarded service is on that host.
Launch-engine verification requires exactly one response record, with no
terminator or one final LF. Additional blank or nonblank records, including
extra trailing LF characters, stop startup before image inspection, explicit
builds, or launch. Query failures remain failures even if stdout looks valid.
The endpoint must contain an absolute socket pathname beyond `/`; `unix://`,
`unix:///`, slash-only paths, and relative Unix paths fail before any engine
query. Choose **one** setup method below.

### With a systemd user session

From a normal login session for your account, enable socket activation:

```bash
systemctl --user enable --now podman.socket
systemctl --user status podman.socket --no-pager
```

Systemd creates the socket and its parent directory, and starts the API
service when a client connects. An inactive `podman.service` between requests
is normal. To keep the user service available after logout and start it at
boot, optionally enable lingering:

```bash
sudo loginctl enable-linger "$(id -un)"
```

If `systemctl --user` reports that it cannot connect to the bus, ensure you
are logged in directly as the intended user with a working systemd user
session. On systems without systemd, use the manual procedure below.

### Without systemd: create the directories and start the service

An error such as
`bind: no such file or directory` when creating the socket means that a
parent directory is missing. The socket file itself is created by Podman;
do not create it with `touch`.

In a terminal on the host, prepare the runtime directory. On systems without
a login manager, `/run/user/<uid>` may also be absent; creating it under
`/run` usually requires administrator privileges:

```bash
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ ! -d "$XDG_RUNTIME_DIR" ]; then
    sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$XDG_RUNTIME_DIR"
fi
ls -ld "$XDG_RUNTIME_DIR"
```

The directory must belong to your account and have mode `0700`
(`drwx------`). If an existing directory has incorrect ownership or
permissions, have the administrator correct it before continuing. Then run
the following as your normal user:

```bash
install -d -m 0700 "$XDG_RUNTIME_DIR/podman"
podman system service --time=0 "unix://$XDG_RUNTIME_DIR/podman/podman.sock"
```

Leave this terminal open and use a second terminal for the checks and wrapper
commands below. The service runs in the foreground; Ctrl+C stops it.
Repeat this setup after reboot because `/run` is temporary. Export the same
`XDG_RUNTIME_DIR` in any other terminal used to run local Podman if your
session does not set it automatically. Run the service and wrapper without
`sudo` so they use your rootless containers and configuration.

### Verify the launch service

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
podman_socket="${CONTAINER_HOST#unix://}"
podman_socket="${podman_socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
test -S "$podman_socket" && echo "Socket exists"
podman --remote --url "unix://$podman_socket" info --format '{{.Host.Security.Rootless}}'
```

Continue only if the socket exists and the API command succeeds and prints
`true`. A socket file alone does not prove that a service is listening or that
its engine is rootless.
If the API command fails, check the systemd status or foreground service output
above and your account's permission to access the socket. If it prints `false`
or another unexpected result, verify that the service was started as the intended
non-root user, without `sudo`, and repeat the rootless service setup above.
See also the official
[Podman API service documentation](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html).

## Network modes and protected installation

| `SANDBOX_CONTAINER_NETWORK` | Behavior |
| --- | --- |
| unset or empty | `offline` |
| `offline` | `--network=none` and the protected bootstrap; own loopback only |
| `unrestricted` | Explicit ordinary runtime networking |
| `provider` or any other value | Refused before any engine operation |

**No provider mode.** In the agent wrappers, provider mode lets an agent reach
the hosts of its authentication method through a CONNECT proxy that binds every
tunnel to an approved TLS server name. The reference profile declares no
authentication method, so the reference offers no provider mode. The proxy,
relay and policy code is still shared and is exercised by the shared tests with
a synthetic fixture profile; each agent wrapper documents its own provider hosts
and the residual exfiltration channel they leave open.

Offline sessions use a protected static bootstrap combining Landlock ABI 3
filesystem rules, an additional restrictive seccomp filter and private network,
PID and IPC namespaces. Native Linux and WSL2 x86_64 are eligible with usable
Landlock ABI >= 3 and successful local enforcement qualification. Kernel release
strings are recorded as evidence rather than pinned; no ABI-9 feature is required.
See [bootstrap build/tests](network/README.md) and
[versioned evidence](docs/validation.md).

The guard denies new Unix sockets, VSOCK and other families except IPv4/IPv6,
which remain inside network=none. It allows only fixed-peer connected Unix
stream/seqpacket pairs, pipes and own loopback. Existing pairs may have private
pathname/abstract names but cannot listen, change peer or publish into host binds.
New named Unix services, host SSH agents and named cache/supervisor daemons are
unavailable, including on tmpfs. io_uring, pidfd_getfd and compat/x32 syscall
bypasses are denied. Ordinary file persistence and Git/worktree operations remain
available. A private XDG_RUNTIME_DIR holds ordinary runtime files; HOME and
configuration persistence stay unchanged.

Offline sessions require a protected installation outside every writable
workspace/worktree-parent and state mount: files and all ancestor directories
must belong to the caller or root and deny group/other writes. A
session-writable launcher cannot enforce its own future invocation. Use native
Linux storage; permission-emulating Windows mounts and world-writable ancestors
such as `/tmp` are unsuitable. `--container-setup` prepares such an
installation, the static guard and its digest manifest, and qualifies it; see
the [guided setup reference](docs/setup.md). An offline launch from a location
without the guard manifest, such as this checkout, stops with setup guidance
before any engine query.

Restricted eligibility requires rootless Netavark/Podman server >= 4.9 through an
explicit same-host Unix `CONTAINER_HOST`, host Python 3, standard OCI seccomp and
actual guard enforcement. SELinux/AppArmor may remain enabled; compatibility is
not guaranteed and any policy denial stops startup without relabeling, policy
disablement or privileges.

Offline launches require a protected matching local qualification report.
Rerun `--container-setup`, or run `--container-qualify` alone from a protected,
manually prepared installation. Qualification uses disposable credential-free
controls and the production guard path; it never grants image maintenance.
Changed kernel/boot, engine/backend/security state, code, images, profile/policy,
CA trust or hardening requires requalification, and every launch still verifies
paths, engine and guard. `locally-qualified` means this installation passed its
required controls; `release-measured` additionally requires an exact matching
protected acceptance entry (the default inventory is empty). See
[qualification details](network/README.md#local-installation-qualification).

Image builds need exact `SANDBOX_CONTAINER_MAINTENANCE=1`; runtime mode never
grants maintenance authority, and pulls and build `RUN` steps stay outside
runtime filtering:

```bash
SANDBOX_CONTAINER_NETWORK=unrestricted SANDBOX_CONTAINER_MAINTENANCE=1 bash ./sandbox-container.sh --container-build
```

Every shell container, in every network mode, explicitly
drops all Linux capabilities and enables container-level `no-new-privileges`
before startup; see [Hardening, budgets and lifetime](#hardening-budgets-and-lifetime).

## Usage

After setup, run the managed launch command from a project directory. Directly
from a checkout, select unrestricted networking:

```bash
SANDBOX_CONTAINER_NETWORK=unrestricted ./sandbox-container.sh
SANDBOX_CONTAINER_NETWORK=unrestricted ./sandbox-container.sh -c 'git status'
printf 'ls\n' | SANDBOX_CONTAINER_NETWORK=unrestricted ./sandbox-container.sh
```

Every argument that is not a `--container-*` option goes to Bash unchanged,
including empty values and values with spaces; stdin is forwarded, and a TTY is
allocated only when stdin and stdout are terminals. `--container-shell` is
accepted and changes nothing, because the session is always Bash. The exit
status of Bash is the exit status of the wrapper. `--container-help` prints the
options and variables without contacting Podman.

The session receives `USER`, `EDITOR=nano` and `VISUAL=nano`, and by name
`TERM`, `COLORTERM`, `LANG` and `LC_ALL` when set. Unrestricted sessions also
receive `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and their
lowercase forms, run with `--init`, and see their container name as
`CONTAINER_NAME`. In offline and provider sessions the confined guard plays the
role of `--init`: Ctrl+C and the shutdown signals reach the command, and the
session ends with the command's status. `SANDBOX_CONTAINER_ENV_VARS` lists further host variable names
(separated by whitespace) to forward by name, never by value; an invalid name
stops the launch, an empty variable is not forwarded, and names the launcher
sets itself (and, in offline mode, proxy and CA variables) are skipped with a
notice.

Image builds use the `Containerfile` beside the physical wrapper script, also
when the wrapper is invoked through a symlink; the build context admits only
the recipe and its declared inputs (`.containerignore`). Image absence triggers
a build only with maintenance authorization; inspection errors stop startup.
A build pulls the exact `FROM` base first and then runs with `--pull=never`
and the docker format, without a timeout. Every image carries a
`build-inputs-hash` label over its build inputs (`Containerfile`,
`.containerignore`, `network/relay.py`, `network/mux.py`); a launch refuses an
image built from other inputs and names the rebuild command.
`--container-build` without other arguments, also together with
`--container-git-worktree` or `--container-shell`, validates every setting,
builds the image and exits without a session; setup uses this operation. With
arguments, it builds and then starts the session.

### Container tests

Sessions never receive the host Podman API. When the toolchain library holds at
least one image toolchain, every session instead gets a private, rootless
Podman engine of its own, in every network mode. The engine shares the
session's network namespace, so its containers have the session's egress: an
offline session's containers reach nothing outside. The session reaches it at
`CONTAINER_HOST=tcp://127.0.0.1:2375`, also given as `DOCKER_HOST` for
Docker-API clients such as Testcontainers. The engine runs the library's images
offline by their pinned references, mounts only the workspace (at the same
path) and the library's read-only image store, holds no secrets, and is removed
with its storage when the session ends. Without images in the library, or with
`SANDBOX_CONTAINER_TOOLCHAINS=0`, there is no engine and `CONTAINER_HOST` and
`DOCKER_HOST` are absent from the session, including image or engine defaults.

```bash
./sandbox-container.sh --container-toolchain add ~/recipes/postgres16.json   # see Images
./sandbox-container.sh -c 'podman run --rm --network=none docker.io/library/postgres@sha256:<digest> postgres --version'
```

- **Images:** add them as toolchains ([Images](#images)). In offline and
  provider sessions the engine pulls nothing; in unrestricted sessions it can
  also pull, and pulled or built images stay in the session's storage. An image
  added during a session is usable at once; the first image needs a new
  session, because a session without library images starts without an engine.
- **Workspace:** a container that bind-mounts a path inside the workspace sees
  the workspace files, and files its root creates there belong to you. Any
  other path a nested container mounts is the engine's own file system, never
  the host's.
- **Isolation:** each nested container has its own process view and host name
  (its container ID). Two sessions have separate engines and never see each
  other's containers.
- **Lifetime:** the launcher starts the engine before the application, waits
  until it answers as a rootless engine, and removes it with its storage when
  the session ends, also after a signal. A later launch removes the engine of a
  launch that was killed.
- **Budgets:** the engine gets the session's memory, CPU and process budgets,
  checked like the agent's; together the session can therefore use twice the
  agent's budget, and the launch says so. On the process rlimit fallback the
  engine's first process sets the limit before anything else, and the launch
  reads it from that process before the session starts; the engine and
  everything it runs share that one limit. Explicit `--memory` or
  `--pids-limit` limits on nested containers apply for every cgroup controller
  the engine has (see **Systemd containers and nested limits** below); a limit
  that needs a controller the engine lacks fails, and the container does not
  start.
- **Hardening exceptions:** the engine container is the one container that
  relaxes the standard policy, only as nested rootless containers and image
  operations need: the `SETUID` and `SETGID` capabilities for the
  user-namespace helpers and `SYS_CHROOT` for layer extraction and builds
  (with no-new-privileges kept on), the FUSE and TUN devices, an unmasked procfs,
  SELinux labelling disabled, a seccomp profile derived from the host's
  default that also allows `sethostname` and `setdomainname`, and a startup
  step that delegates the engine's own cgroup subtree. That step is the
  engine's first process: it starts as the root of the engine's user namespace
  (never you) with the `CHOWN` capability as well, hands the subtree to the
  engine user, and then runs everything else as that user. Afterwards no
  engine process runs as root, and `CHOWN` stays only in the bounding set,
  where no-new-privileges keeps it unreachable. The engine user is unprivileged
  and mapped to you (`--userns=keep-id:uid=1000,gid=1000`), which needs 65535
  of your subordinate IDs in one contiguous range. A tool that needs more
  privilege is unsupported. The engine image declares these four capabilities
  (`SETUID`, `SETGID`, `SYS_CHROOT` and `CHOWN`) in its
  `io.containers.capabilities` label, so Podman starts the engine without a
  capability error. An engine image built before `sandbox-ref-36` keeps its
  base's label, and Podman logs `Capabilities requested by user or image are
  not allowed by default` at each start. The message is harmless, because
  Podman keeps the engine's capabilities. Rerun `--container-setup` to rebuild
  the image.
- **Systemd containers and nested limits:** on an eligible engine, nested
  containers get cgroups of their own, so an image that starts systemd runs it
  as PID 1, for example to test Ansible roles that manage services:

  ```bash
  # an image toolchain whose image starts /sbin/init, such as a Rocky Linux 9 init image
  podman run --detach --name target --systemd=always docker.io/rockylinux/rockylinux@sha256:<digest>
  podman exec target timeout 120 sh -c 'until systemctl is-system-running | grep -qE "^(running|degraded)$"; do sleep 1; done'
  podman exec target systemd-run --unit=probe --property=Type=oneshot /bin/true
  ```

  The second command waits until boot completes (`running` or `degraded`).
  `systemctl is-system-running --wait` does the same only when the image
  has D-Bus; init images without it answer `Failed to connect to bus`.

  An engine is eligible when its cgroup namespace is private and its cgroup
  v2 root is mounted read-write with `nsdelegate` and belongs to the root of
  its user namespace. This holds for native Linux with the `systemd` cgroup
  manager and for the Windows Podman machine (`cgroupfs`); no host change is
  needed. Explicit nested limits apply for each controller the engine has:
  `memory` and `pids` where the rootless engine delegates them (native Linux
  with the `systemd` manager); the Windows Podman machine delegates none, so
  there they fail, and systemd's resource-control unit settings (such as
  `MemoryMax=` or `TasksMax=`) have no effect. The engine's own limit files,
  and so the session budgets, stay unwritable from the engine and from nested
  containers. When an engine is not eligible, for example on a host with
  cgroup v1, the launch says `systemd containers and explicit limits for nested
  containers are unavailable` with the reason, and the session starts without
  them. Systemd containers and the delegation are untested with SELinux
  enforcing or an active AppArmor profile.
- **Host `/sys` in the session:** the session joins the engine's network
  namespace, and a rootless container that joins another namespace cannot
  mount a sysfs of its own: Podman bind-mounts the host's `/sys` read-only
  instead. A session with an engine therefore sees the host's network
  interfaces in `/sys/class/net` (names, MAC addresses, link state and
  counters). Its network namespace still has only loopback, as `/proc/net/dev`
  shows.

Migration: host Podman delegation (`SANDBOX_CONTAINER_PODMAN=1`, with
`SANDBOX_CONTAINER_PODMAN_SOCKET`) was removed. The exact value `1` now stops
every launch with this guidance, other values are ignored, and setup drops a
saved delegation choice. Add the images your tests need as toolchains (see
[Toolchains](#toolchains)); the next session has its engine.

### Using Git worktrees

When a worktree's shared Git metadata and sibling worktrees are in its parent
directory, run the wrapper from the worktree root with
`--container-git-worktree`:

```bash
cd /path/to/root/main
/absolute/path/to/sandbox-container.sh --container-git-worktree
/absolute/path/to/sandbox-container.sh --container-git-worktree --container-shell
```

The option mounts `/path/to/root` at `/path/to/root` read/write, while the
shell starts in `/path/to/root/main`. Git and other commands run from there.
Because the parent and its contents are writable, sibling worktrees and other
files beneath it are accessible too. Git metadata referenced outside that
parent is not exposed by this option.

The wrapper mounts the immediate parent of the physical directory from which
it is launched; it does not search for a Git or worktree root. For example,
launching from `/path/to/root/main/src` mounts `/path/to/root/main`. Use the
flag from the worktree root when the shared metadata is in the common parent.
A parent that is a refused sensitive directory, such as your home, stops the
launch.

### Trusting a host CA

Host CA trust is disabled by default. To trust a CA bundle from the host, for
example a corporate TLS proxy certificate, set:

```bash
SANDBOX_CONTAINER_TRUST_HOST_CA=1 ./sandbox-container.sh
```

`SANDBOX_CONTAINER_TRUST_HOST_CA` accepts `1`, `true`, or `yes`; `0`, `false`, or
`no` (or an empty value) disable it, and any other value stops the wrapper with
an error.

When enabled, the bundle is mounted read-only at `/sandbox-home/ca/bundle.pem`,
and `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, and
`NODE_EXTRA_CA_CERTS` point at it. `NODE_EXTRA_CA_CERTS` is what makes Node.js
tools such as OpenSpec trust the bundle, because Node.js ignores `SSL_CERT_FILE`. The image's own
certificates are not replaced.

The bundle is chosen with `SANDBOX_CONTAINER_CA_BUNDLE`. When it is unset, the
wrapper uses the first existing file among `/etc/ssl/certs/ca-certificates.crt`
(Debian and Ubuntu) and `/etc/pki/tls/certs/ca-bundle.crt` (Fedora and RHEL).
If `SANDBOX_CONTAINER_CA_BUNDLE` names a missing file, or neither default exists,
the wrapper stops before starting the container.

```bash
SANDBOX_CONTAINER_TRUST_HOST_CA=1 SANDBOX_CONTAINER_CA_BUNDLE=/path/to/ca.pem ./sandbox-container.sh
```

The same bundle also verifies the runtime image build's Debian package
downloads, which use HTTPS only. With host CA trust enabled, `--container-build`,
a missing-image build and setup preparation pass it as the build secret
`build-ca`: it is mounted only for the package installation step and is not stored
in the image. Setup gives it to the guard toolchain build as well, for its Alpine
package downloads. Without host CA trust, the build trusts only the root certificates
of the pinned base image. On a network that intercepts TLS (a corporate proxy that
re-signs certificates), enable host CA trust with a bundle that contains the
interception CA, or the build fails with a certificate verification error.

With a Podman machine on Windows, the host is the machine: it must first
import the CAs that Windows trusts
([Trusting a host CA on Windows](#trusting-a-host-ca-on-windows)).

Migration: earlier versions always mounted the host certificate directory and
set CA variables. Those sessions no longer trust the host CA by default. Set
`SANDBOX_CONTAINER_TRUST_HOST_CA=1` to restore that behavior.

## Windows with Podman machine

On Windows, `sandbox-container.ps1` starts the sandbox from PowerShell on the
rootless engine of a Podman machine that Podman Desktop created with the WSL
provider. The session runs inside the machine's WSL distribution
(`podman-machine-default`, user `user`), in the PID and mount namespaces where
the machine runs systemd and its Podman service, as the machine's own login
shells do. The entry uses neither `podman.exe` nor the machine's SSH or
Windows API connection, so it works while other WSL distributions, such as
Ubuntu, are running.

Prerequisites:

- Windows PowerShell 5.1 or PowerShell 7, with a policy that allows local
  scripts, for example `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`;
- a rootless Podman machine with the WSL provider, created with Podman
  Desktop, and started by Podman (Podman Desktop or `podman machine start`)
  before setup and sessions;
- `sudo` without a password for the machine's user, which Podman machines
  provide: sessions and setup enter the machine's systemd namespaces with
  `sudo nsenter`, as its login shells do (`/usr/local/bin/enterns`);
- a checkout of this repository in a folder on a Windows drive, with LF line
  endings. The repository's `.gitattributes` keeps them LF even with
  `core.autocrlf=true`; [docs/setup.md](docs/setup.md) explains how to fix an
  older CRLF checkout.

Run setup once from the checkout, in an interactive PowerShell window:

```powershell
cd C:\Work\sandbox-container
.\sandbox-container.ps1 --container-setup
```

Setup runs the guided setup inside the machine distribution. The release,
preferences and images are installed there, in `~/.local/lib/sandbox-container`.
Its output leaves out the Linux shell guidance; the entry prints how to start
sessions.
Setup finds the machine's own Podman service, so it offers offline
networking, the default, and unrestricted networking, as on Linux. Rerun setup
after updating the checkout, and after the machine is recreated. To run the sandbox as a command without keeping the checkout,
install it instead ([Install as a command](#install-as-a-command)).

Start sessions from a project directory on a Windows drive:

```powershell
cd C:\Work\my-project
C:\Work\sandbox-container\sandbox-container.ps1
C:\Work\sandbox-container\sandbox-container.ps1 -c 'git status'
C:\Work\sandbox-container\sandbox-container.ps1 --container-help
```

The project is mounted at its drive path, for example `/mnt/c/Work/my-project`.
A launch is refused before any engine query in these cases:

- the machine is stopped: the entry does not start its distribution, because
  `wsl.exe` would start it without the user's runtime directory
  `/run/user/<uid>`, where no `podman` command works. Start the machine with
  Podman Desktop or `podman machine start`;
- the distribution runs without that directory, because `wsl.exe` alone
  started it. Run `wsl --terminate podman-machine-default`, then start the
  machine with Podman. Setup refuses both states too;
- `sudo` asks the machine's user for a password, so the entry cannot enter the
  machine's systemd namespaces. Setup refuses it too;

- the location is a network share, a path inside a WSL distribution, a drive
  the distribution does not mount, or not a file system path;
- the project or the worktree parent contains the checkout, or lies inside it;
- the project is a Windows system or profile folder (see
  [Hardening, budgets and lifetime](#hardening-budgets-and-lifetime)).

The exit status, the terminal and Ctrl+C work as on Linux. Closing the window
also ends the session and removes its container. The machine's engine uses
the `cgroupfs` manager: the memory and CPU budgets are not enforced, and the
process budget uses the process rlimit, as the launch notices state (see
[Hardening, budgets and lifetime](#hardening-budgets-and-lifetime)).

| Variable | Meaning |
| --- | --- |
| `SANDBOX_CONTAINER_NETWORK` | `unrestricted` or `offline` for one launch (default: the mode setup saved); a restricted mode needs a setup that prepared it |
| `SANDBOX_CONTAINER_WSL_DISTRO` | WSL distribution (default `podman-machine-default`) |
| `SANDBOX_CONTAINER_WSL_USER` | user in the distribution (default `user`) |
| `SANDBOX_CONTAINER_WSL_INSTALLATION` | absolute installation path in the distribution, when setup used another one |

Set them with `$env:NAME = 'value'`. The entry forwards to the launcher in the
distribution, by name, the other `SANDBOX_CONTAINER_*` variables whose names
use only letters, digits and `_`, `SANDBOX_CONTAINER_CONFIG_DIR` when it holds
a distribution path (starting with `/`), and the names listed in
`SANDBOX_CONTAINER_ENV_VARS`. A Windows path in
`SANDBOX_CONTAINER_CONFIG_DIR` is skipped with a notice, and the directory
saved by setup applies. In a wrapper whose profile declares authentication
methods, the entry also forwards their key variables, for example
`ANTHROPIC_API_KEY` in Claude: `$env:ANTHROPIC_API_KEY = '...'` before the
entry supplies the key as an exported variable does on Linux. The help lists
them. It forwards no other Windows variable. Path values are distribution
paths, such as `/home/user/...`.

Limits on Windows:

- No host Podman delegation, as on Linux: `SANDBOX_CONTAINER_PODMAN=1` is
  refused with the migration guidance, and a release whose setup saved
  delegation asks to rerun setup from Windows. Sessions with image toolchains
  get their private container engine in the machine
  ([Container tests](#container-tests)).
- PowerShell pipeline input, such as `'x' | .\sandbox-container.ps1 -c cat`, is
  refused, because PowerShell alters it. Redirect a file from `cmd.exe`
  instead:
  `cmd /c "powershell -File C:\Work\sandbox-container\sandbox-container.ps1 -c cat < input.txt"`.
- PowerShell parses the arguments first. Quote a `--` meant for Bash (`'--'`),
  values with commas (`'a,b'`), numbers whose spelling matters (`'007'`) and
  arguments of the form `-x:y`. The encoded arguments are limited to 32766
  characters.
- A variable with an empty value counts as unset.
- `podman machine stop` (`wsl --terminate`) ends running sessions.
- After the machine starts, the folder of its first session may stay in use
  by a WSL process until `wsl --shutdown`, so Windows cannot delete that
  folder meanwhile.
- Projects on a Windows drive go through drvfs, which is slow on large trees.
  Git for Windows clones with `core.autocrlf=true` look modified to Git in the
  session: set `core.autocrlf=false` for the project, or give it a
  `.gitattributes`.
- Bitdefender's Advanced Threat Control (`Atc4.Detection`) has blocked the
  operator validation script `tools/windows-validate.ps1`, and quarantined
  files while validation bundles were extracted with `tar`, for example
  `tests/fixtures/shell-agent/launcher.sh`, which only the Linux tests use.
  Setup, the installer and sessions ran with it active, and another Windows
  system with other antivirus products ran the validation without problems.
  Run the validation script with the checkout folder excluded, or with the
  protection paused for the run, as your administrator allows. Setup and the
  entry fail when a file they need is missing: restore it from the quarantine,
  and report the false positive to the vendor.

### Trusting a host CA on Windows

Setup and sessions run in the machine, so host CA trust uses a bundle of the
machine, not the Windows certificate store. On a network that intercepts TLS
(a corporate proxy that re-signs certificates), the machine trusts the
interception CA only when Podman imports the Windows store into it. Without
it, image pulls and builds in the machine and HTTPS requests in sessions fail
with a certificate verification error. With Podman 6.0 or later, enable the
import once. `podman machine set` fails while the machine runs, so stop it
first:

```powershell
podman machine stop
podman machine set --import-native-ca
podman machine start
```

The import happens at every machine start: Podman copies the CAs that Windows
trusts into the machine and runs `update-ca-trust`, so the machine's system
bundle contains them. Restart the machine after Windows gains a new CA.

Then run setup and answer yes to "Trust a host CA bundle?". Keep the bundle
setup proposes, the machine's system bundle (see
[Trusting a host CA](#trusting-a-host-ca)): setup passes it to the image builds
and saves it for sessions. Rerun setup after the machine is recreated, and
enable the import again on the new machine.

### Toolchains on Windows

The [toolchain](#toolchains) commands run from PowerShell like the other
options, from any directory outside the checkout:

```powershell
sandbox-container --container-toolchain add java21
sandbox-container --container-toolchain add C:\Users\me\recipes\x.json
sandbox-container --container-toolchain list
```

- **Location:** the library lives inside the Podman machine's distribution, in
  `~/.local/share/sandbox-toolchains` of the machine user, or in
  `SANDBOX_CONTAINER_TOOLCHAINS_DIR` (a distribution path). Every wrapper that
  runs in the machine shares it. Recreating the machine removes it: after the
  new setup, add the toolchains again.
- **Windows paths:** a recipe path or a local archive path in a recipe written
  as a Windows drive path (`C:\...` or `C:/...`) is translated to its drive
  mount in the machine. Network shares, paths inside a WSL distribution and
  drives that the distribution does not mount are refused. Keep your recipes
  outside project folders (see [Managing the library](#managing-the-library)).
- **Network:** pulls and downloads run inside the machine. On a network that
  re-signs TLS, they trust the CA that `podman machine set --import-native-ca`
  adds to the machine (see [Trusting a host CA on Windows](#trusting-a-host-ca-on-windows)).
  The entry forwards no Windows proxy variable, so `add` downloads without an
  explicit HTTP proxy; pulls follow the machine's Podman configuration.

### Install as a command

Instead of setup from the checkout, you can install the entry for your
Windows account:

```powershell
cd C:\Work\sandbox-container
.\sandbox-container.ps1 --container-install
```

The install copies the entry, the Windows scripts and every file that setup
needs into `%LOCALAPPDATA%\Programs\sandbox-container`. It then adds that
folder to your user `PATH` (`HKCU\Environment`, no administrator rights; the
other entries and their `%VAR%` references stay as they are) and runs setup
from the copy. The installer announces the `PATH` change before making it;
nothing is written to the PowerShell profile or system-wide. Afterwards the
checkout can be deleted, and a new PowerShell window runs the command from any
project directory:

```powershell
cd C:\Work\my-project
sandbox-container
sandbox-container -c 'git status'
sandbox-container --container-setup
```

New PowerShell windows and new Windows Terminal tabs find the command; the
window or tab that ran the install may not. When setup fails after the copy,
the copy and the `PATH` entry stay; finish with
`sandbox-container --container-setup`.

To update, run `--container-install` again from a newer checkout or download.
It replaces the installed files, removes the ones the new version no longer
has, and runs setup. Do not update while a setup runs from the installed
copy. The installed command refuses to install itself. An
interrupted install leaves the copy marked incomplete: the command then
refuses to start sessions until the next install completes. Two installs never
run at once.

`sandbox-container --container-uninstall` (also from a checkout) removes the
`PATH` entry and the installed copy. The installation inside the Podman machine
stays until the machine is reset. A folder still used by a WSL process is
reported; `wsl --shutdown` releases it.

The scripts are not signed. The installer writes new local files, so the
installed command runs under the default `RemoteSigned` policy. A downloaded
zip keeps the Mark of the Web on its files: run its first install as
`powershell -ExecutionPolicy Bypass -File .\sandbox-container.ps1 --container-install`,
or `Unblock-File` its files first. Running the installer is your decision to
trust that source. Policies stricter than `RemoteSigned`, such as `AllSigned`,
are unsupported.

## Mounts, identity, and persistence

The process inside the container uses `--userns=keep-id` and the caller's
UID/GID. Files created in the workspace therefore retain compatible ownership
on the host.

By default, the current workspace is mounted read/write at the same absolute
path inside the container. With `--container-git-worktree`, the wrapper mounts
the immediate parent of the current directory at that same absolute path
instead; the container's working directory remains the original current
directory. Preserving absolute paths is required because bind mounts requested
by child containers are resolved by the host Podman service.

Every shell container and qualification gate container gets an empty read-only tmpfs at
`/run/secrets`. On RHEL and Rocky hosts Podman's `mounts.conf` would otherwise
mount the host subscription secrets there, writable; with the mask Podman skips
that mount, the session sees no host subscription material, and the restricted
bootstrap accepts the layout. No host configuration change is needed.

The shell configuration directory defaults to `~/.config/sandbox-container`,
or `SANDBOX_CONTAINER_CONFIG_DIR` when nonempty, mounted read/write at
`/sandbox-home/.config/sandbox-container`. It holds the Bash history
(`HISTFILE`), so history persists across sessions; the wrapper sets `HISTFILE`
and the in-container `SANDBOX_CONTAINER_CONFIG_DIR` after the toolchain
environment, so a toolchain cannot move them. Host `~/.config/openspec` is also
mounted read/write at `/sandbox-home/.config/openspec`. In this shared mode the
rest of `/sandbox-home` is an ephemeral 512 MiB `noexec` tmpfs: files written
there disappear with the session. Commands in the session can read and change
the mounted files.

`SANDBOX_CONTAINER_READONLY_STATE` (`1`, `true` or `yes`) mounts the existing
configuration and shared directories read-only instead, from shared state or
from the isolated home; the directories must exist, nothing is created, and
the isolated home itself is not mounted.

### Optional isolated home

Set a nonempty `SANDBOX_CONTAINER_STATE_DIR` to mount a dedicated writable home
at `/sandbox-home`, without adding the shared shell/OpenSpec mounts:

```bash
unset SANDBOX_CONTAINER_CONFIG_DIR
SANDBOX_CONTAINER_STATE_DIR="$HOME/.local/share/sandbox-container/home" ./sandbox-container.sh
```

Inside the container, `HOME=/sandbox-home` and
`SANDBOX_CONTAINER_CONFIG_DIR=/sandbox-home/.config/sandbox-container` in both modes. In isolated mode,
`.config/sandbox-container` (with the Bash history), `.config/openspec`, caches,
and other home data persist under the
selected directory. A simultaneous nonempty `SANDBOX_CONTAINER_CONFIG_DIR` is rejected;
unset it to select isolation. Unset/empty `SANDBOX_CONTAINER_STATE_DIR` keeps the
shared default. A directory alias is resolved to its physical absolute path.
Existing isolated configuration symlinks escaping the selected home are rejected.
The isolated home must not be the workspace, contain it or lie inside it (the
parent directory in worktree mode), so credentials and history never land in a
repository; the wrapper and the managed launcher refuse an overlap before any
engine operation.

New state directories are created with user-only permissions. The shared
configuration directory, or isolated home and its `.config/sandbox-container`
directory, must belong to
the caller, allow read/write/search, and deny group/other access. Existing
permissions are never changed recursively. If startup rejects a directory,
inspect it and explicitly use `chmod 700` on the named directory, or select
private native Linux storage if the filesystem ignores Unix modes (some WSL
Windows-backed mounts do). Directory checks do not recursively audit old files,
encrypt state, or hide secrets from commands run in the session.

The wrapper applies `umask 077` only while creating state directories, preserving
the caller's umask for subsequent host commands. This does not set the container
process umask or guarantee private modes for files created inside a session;
those modes depend on the runtime and the application. Directory privacy checks
and measured runtime file modes are separate guarantees.

To migrate, stop sessions and use a new private dedicated directory. Either
start fresh or deliberately copy selected files from the previous shell
configuration into `<state>/.config/sandbox-container` and selected OpenSpec
configuration into
`<state>/.config/openspec`. Preserve private file permissions, protect backups,
and do not overwrite an existing profile or copy the whole host home. The
wrapper never imports, merges, or deletes profiles automatically. To return to
shared state, unset `SANDBOX_CONTAINER_STATE_DIR` and restore any previous
`SANDBOX_CONTAINER_CONFIG_DIR`; dedicated state remains on disk.

### Authority and security policies

The root filesystem is read-only; selected workspace/state mounts are writable.
`/tmp`, `/run`, and `/var/tmp` are explicit ephemeral tmpfs mounts with
`nosuid,nodev,noexec` and limits of 512 MiB, 32 MiB, and 512 MiB respectively,
the same in every wrapper. An agent profile that needs native runtime parts in
`/tmp` and the ephemeral home declares `native.exec_tmp`; `/var/tmp` and `/run`
stay `noexec` for every profile.
Podman's automatic read-only tmpfs provisioning stays enabled: with
`--read-only-tmpfs=false`, Podman 5 would mount `/dev` read-only, and newer
crun releases cannot attach a terminal there. The engine provides `/dev` and
a `devpts` at `/dev/pts` that allows pseudo-terminals, which interactive
tools such as `script`, `expect` or `tmux` need. An explicit `devpts` mount
would get `ptmxmode=000`, and no pseudo-terminal could be opened. `/dev/shm`
is an empty read-only tmpfs. On Podman 5, `/dev` is the engine's writable
tmpfs, but no device can be created without capabilities. On Podman 4.9,
`/dev` stays read-only. `/tmp` and `/var/tmp` have
sticky mode `1777`. Their contents disappear when the container is removed.
`/var/tmp` is now explicitly bounded and prevents direct execution, so tools
must not depend on executable temporary files there. No writable `/var/log`
mount is added. The optional host CA remains a single read-only file.
No full host home, SSH agent, desktop bus, or keyring is added automatically.
A selected workspace or worktree parent can itself contain those host files.
The wrapper therefore refuses sensitive workspace roots; see
[Hardening, budgets and lifetime](#hardening-budgets-and-lifetime).

No session receives a host Podman socket. A session's private container engine
mounts only the workspace and the library's read-only image store, so its
containers stay inside the project-only filesystem boundary and the session's
network boundary ([Container tests](#container-tests)).

Internal sandboxing (Bubblewrap inside the session), filesystem isolation and
the network boundary are separate controls. The shell has no approval system:
the wrapper reads no approval-bypass variable, so agent variables such as
`CLAUDE_YOLO` have no effect.

### Hardening, budgets and lifetime

Every shell container runs with `--cap-drop=all` and
`--security-opt=no-new-privileges` in every mode. Tools that need a capability
are unsupported; the wrapper never adds one back. The Podman client reaches the
session's container engine without capabilities; the engine container has its
own fixed exceptions ([Container tests](#container-tests)).

Every shell container also receives memory, CPU and process budgets, for each
budget whose cgroup v2 controller the rootless engine delegates:

| Variable | Default | Accepted values |
| --- | --- | --- |
| `SANDBOX_CONTAINER_MEMORY_LIMIT` | `4g` | positive integer with unit `k`, `m` or `g` |
| `SANDBOX_CONTAINER_CPU_LIMIT` | `2` | positive number of CPUs with at most 3 decimals |
| `SANDBOX_CONTAINER_PIDS_LIMIT` | `512` | positive integer up to 4194304 |
| `SANDBOX_CONTAINER_RUN_TIMEOUT` | `0` (disabled) | whole seconds of container lifetime |

`--container-setup` asks for these values and saves them; the managed launcher
supplies them unless a variable is exported. Change them by rerunning setup.
An exported value that differs from the saved one is used, but a restricted
launch then stops until you requalify with `--container-qualify`. Budgets
cannot be disabled: empty, `0`, `-1` and `max` are rejected before any engine
operation. Each launch checks the created container's configured limits before
the shell starts; setup smoke and restricted qualification measure the
effective cgroup v2 `memory.max`, `pids.max` and `cpu.max`, and the effective
process rlimit when the fallback below applies. Budgets and tmpfs sizes do not
limit workspace or state storage growth.

The sandbox adapts to the controllers the engine reports
(`podman info --format '{{.Host.CgroupControllers}}'`) instead of requiring host
changes. A budget whose controller (`memory`, `cpu` or `pids`) is not delegated
is not requested; every launch and the setup plan print a notice such as
`agent CPU budget not enforced: cgroup controller cpu is not delegated to the
rootless engine`, and continue without asking. The check is still strict: a
delegated budget must be applied exactly, an unenforced one must be absent, and
the enforced set is part of the restricted qualification identity, so a later
delegation change requires requalification.

A rootless engine applies cgroup limits only through the `systemd` cgroup
manager (`podman info --format '{{.Host.CgroupManager}}'`). With `cgroupfs`,
for example on a Podman machine on WSL, the engine reports every controller but
ignores the limits. The sandbox therefore treats no controller as delegated: it
prints `agent memory budget not enforced: the rootless engine uses the cgroupfs
cgroup manager, which applies no cgroup limits` and the matching CPU line, and
the process budget uses the fallback below.

The process budget has a fallback. Without the `pids` controller, the shell
container's first process sets its soft and hard process rlimit to the
selected budget, and the notice reads `agent process budget enforced through the
process rlimit (512 tasks of the session user, threads included)`:
- **Where it is set.** The container starts with a fixed `/bin/sh` step,
  `{ ulimit -u N 2>/dev/null || ulimit -p N; } && exec <program>`, before the
  shell or, in restricted modes, the guard runs (dash names the limit `-p`). If
  the limit cannot be set, the container stops before anything else runs, and
  each launch checks that the created container starts with this step.
- **Per session.** Linux 5.14 and later count the limit per user namespace, and
  the step sets it inside the container's own. The wrapper never uses
  `--ulimit nproc`: the engine applies that limit before it creates the
  container's user namespace, and the kernel then checks every fork against
  the processes of all your containers together (see `docs/validation.md`).
- **Not raisable.** The session cannot raise the limit, because it has no
  capabilities. Its own shell and init process count against it, so slightly
  fewer than `N` processes are left for commands.
- **Exceptions.** A process that host tools start in the container with
  `podman exec` gets the engine's default limits instead. Only the launcher's
  checks and the validation script do that; a session has no engine access to
  its own container.
- **The machine as a whole.** Each session, proxy and engine is bounded
  separately; together they are bounded only by your user's own process
  limit.

The fallback applies only when the engine reports kernel 5.14 or later
(`podman info --format '{{.Host.Kernel}}'`). Older or unrecognized kernels may
count every process of your user, so the process budget then stays unenforced,
and the notice names the reason. The memory and CPU budgets have no fallback.
Which mechanism enforces the process budget is part of the restricted
qualification identity.

Risk: without a memory or process budget, a compromised or runaway session can
exhaust host memory or processes for your user; without a CPU budget it can
saturate every CPU. Delegating the controllers (for example a systemd
`Delegate=cpu cpuset io memory pids` drop-in for `user@.service`) restores full
enforcement, but the sandbox never requires it.

With a lifetime limit, the engine stops the shell container after that many
seconds. The wrapper reports `session lifetime limit reached` and keeps the
engine client's exit status (255 on the measured Podman 4.9.3 server); owned resources are cleaned up within the usual
shutdown budget.

The writable workspace mount (the parent with `--container-git-worktree`) must
not be `/`, your home directory, `/home`, `/root`, `/etc`, `/usr`, `/var`, `/bin`,
`/sbin`, `/lib`, `/lib64`, `/boot`, `/opt`, `/srv`, `/mnt`, `/media`, `/proc`,
`/sys`, `/dev`, `/run`, `/tmp` or a WSL drive root such as `/mnt/c`.

On a WSL drive mount, it also must not be one of these Windows folders, in any
letter case, because drvfs ignores case:

- `/mnt/<drive>/Users`;
- a profile, `/mnt/<drive>/Users/<name>`, its `Documents`, its `OneDrive`
  (also `OneDrive - <organization>`) or `OneDrive/Documents`, which hold the
  PowerShell profile and modules;
- anything inside the profile's `AppData`, which holds the startup folder;
- `/mnt/<drive>/Windows`;
- `/mnt/<drive>/Program Files` or `/mnt/<drive>/Program Files (x86)`;
- `/mnt/<drive>/ProgramData`.

Apart from `AppData`, only these exact folders are refused. A project below
them, such as `/mnt/c/Users/me/projects/app` or
`/mnt/c/Users/me/Documents/GitHub/app`, is accepted. In worktree mode, however, a
project placed directly in a profile is refused, because its parent is the
profile.

Physical paths are compared, so symlinks do not bypass the check. Launch from a
project subdirectory instead. Exact `SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` permits a
refused directory with a warning and relaxes nothing else.

### Standard security policies

Standard seccomp and SELinux policy remain in force. The wrapper adds no
privileged mode, capabilities, custom security profiles, disabled labels, or
automatic bind relabeling (the former OpenSpec `:z` option is removed). If host
policy denies a bind, startup stops and reports the engine error; compatibility
with that policy remains unguaranteed. An internal sandbox failure does not relax these policies or tmpfs
options. `bwrap --version`, namespace probes, or a zero CLI exit status alone do
not prove a sandboxed tool operation succeeded. See [validation](docs/validation.md)
for tested environments, results, and outstanding checks.

## Included tools

The image includes Bash, Node.js/npm with the pinned OpenSpec CLI, Python 3,
Bubblewrap (`bwrap`), the Podman client, Git, local search and editing tools
(`rg`, and `nano` as `EDITOR`/`VISUAL`), archive tools, JSON support (`jq`) and
diagnostics. It installs no agent CLI. Debian packages come only from verified
HTTPS sources. Image inputs are pinned: the `Containerfile` names the base image
by digest and installs an exact OpenSpec version; change them only through the
maintenance procedure in [docs/validation.md](docs/validation.md), rebuild with
`SANDBOX_CONTAINER_MAINTENANCE=1` and rerun setup or qualification. Further
language toolchains come from the [toolchain library](#toolchains).

## Toolchains

Sessions can use extra toolchains, such as Java, Go or Python, without Podman
access, an unrestricted network or a rebuilt image. The operator keeps a
toolchain library on the host. Every session sees it read-only, with `nosuid`
and `nodev`, at `/toolchains`. The library is shared by this reference shell and the Claude, Codex,
OpenCode, Pi and Antigravity wrappers. A toolchain adds no network, IPC or
privilege capability: it runs under the same restrictions as the rest of the
session.

- **Location:** `${XDG_DATA_HOME:-~/.local/share}/sandbox-toolchains`, or
  `SANDBOX_CONTAINER_TOOLCHAINS_DIR`. The launcher creates it private (`0700`)
  when it is missing. It must stay outside the workspace, the state
  directories and the installation. A home directory exposed as the workspace
  with `SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` contains the default
  library, so that launch stops. Move the library with
  `SANDBOX_CONTAINER_TOOLCHAINS_DIR`, or omit it.
- **Disable:** `SANDBOX_CONTAINER_TOOLCHAINS=0` starts a session without the
  mount.
- **Live updates:** a toolchain added or removed on the host appears in
  running sessions without a restart.

### Managing the library

The operator runs these commands on the host; `--container-toolchain` must be
the first argument:

```bash
./sandbox-container.sh --container-toolchain add java21            # install or replace a catalog recipe
./sandbox-container.sh --container-toolchain add ~/recipes/x.json  # install or replace an operator recipe
./sandbox-container.sh --container-toolchain list                  # installed toolchains, then the catalog
./sandbox-container.sh --container-toolchain remove java21
./sandbox-container.sh --container-toolchain verify [java21]       # rerun the checks on the current runtime image
```

An argument without `/` that does not end in `.json` names a recipe of the
release's catalog (see [Recipes](#recipes)); any other argument is a recipe
file. `list` shows the name, version, default flag, size, requirements and
verified base of each installed toolchain, then the catalog recipes that are
not installed.

- **Sources:** a toolchain is a relocatable directory tree, assembled from one
  or more sources: a path inside an OCI image referenced by `@sha256:` digest,
  an HTTPS archive URL with its SHA-256, or a local archive with its SHA-256.
  A toolchain can also, or only, provide container images for the session
  container engine (see [Images](#images)); `list` shows them with the others,
  and `remove` deletes images no other toolchain lists, once no session engine
  runs.
- **Operator recipes:** keep them outside project directories, for example in
  `~/recipes`. A session can write its workspace and state directories, so an
  agent could have written a recipe found there: `add` refuses a recipe file
  inside the directory it runs from (its parent, when setup saved the worktree
  scope) or inside a state directory, before fetching anything. It cannot
  recognize the directories of other projects. Catalog names are not affected,
  and neither are the local archives that a recipe pins by SHA-256.
- **Fetching:** `add` fetches what the recipe names by itself and prints each
  image and URL first. It pulls a missing image and downloads archive URLs
  without `SANDBOX_CONTAINER_MAINTENANCE`, because the content is fixed by its
  digest or SHA-256 and no code runs while it is fetched and extracted.
  Downloads use HTTPS only and follow redirects only to HTTPS. They trust the
  host CA bundle that setup saved when host CA trust is enabled, and the system
  trust otherwise, and they use the host's proxy variables. Like image builds,
  pulls and downloads happen on the host, outside runtime filtering. `add`
  never builds an image; image builds still require maintenance.
- **Extraction:** every archive is checked against its SHA-256 before anything
  is extracted, and is extracted from a private copy in the library, so a local
  archive changed afterwards cannot reach the toolchain. Extraction rejects
  absolute paths, `..`, device nodes and links that leave the toolchain, and
  clears setuid and setgid bits. A file that two sources provide fails the
  command.
- **Atomic changes:** changes take a library lock and replace directories
  atomically.
- **Check:** before accepting a toolchain, `add` runs the recipe's `check`
  command in the runtime image, without network and with the session's
  identity and hardening. A toolchain that needs a newer C library than the
  image's glibc fails here. The manifest records the base image from the
  installed `Containerfile`.
- **After an update:** when setup selects a new release, it reruns the check of
  every installed toolchain verified on another base, records the new base
  when the check passes, and prints the result for each. A failed check does
  not fail setup: that toolchain stays visible but loses its default
  environment until `verify` succeeds, and the launcher prints one warning
  naming it.

### Recipes

The release contains a catalog of reviewed recipes in
`setup/toolchain-catalog/`, shared by every wrapper: `add <name>` installs one
with nothing else to prepare. An operator recipe is a JSON file that the
operator keeps and reviews, and gives to `add` by its path:

| Key | Meaning |
| --- | --- |
| `schema`, `name`, `version` | `2`; `[a-z0-9][a-z0-9._-]*`; free version text |
| `sources` | 1 to 16 sources, extracted in order into one toolchain (see below); optional with `images` |
| `images` | 1 to 16 container images for the session container engine (see [Images](#images)) |
| `path` | directories relative to the toolchain, added to `PATH` (default `["bin"]`) |
| `env` | variables: `{"toolchain": "<relative path>"}` or `{"value": "<literal>"}` |
| `requires` | other toolchains whose environment is loaded first |
| `notes` | short instructions shown in `toolchains.md` |
| `check` | command run in the runtime image before the toolchain is accepted |
| `default` | `true` adds the toolchain to new sessions' environment |

Each source is one of:

| Source | Keys |
| --- | --- |
| Image | `{"image": "<ref>@sha256:<digest>", "path": "/abs/dir", "target": "rel/dir"}` |
| Archive URL | `{"url": "https://...", "sha256": "<hex>", "path": "member/dir", "target": "rel/dir"}` |
| Local archive | `{"archive": "/abs/file.tar.xz", "sha256": "<hex>", "path": "member/dir", "target": "rel/dir"}` |

- **Placement:** an image source copies the directory `path` of the image. For
  an archive, `path` selects one directory inside it, or `strip_components`
  drops that many leading directories instead. The result goes to `target`
  (default: the toolchain root). Directories of several sources merge; a file
  that two sources provide fails `add`. An archive that several sources use is
  fetched once.
- **Schema 1:** recipes with `"schema": 1` and one `source` object (an image or
  a local archive, with `strip_components`) stay valid.
- **Catalog recipes** use only images and archive URLs, never local files.
- **Protected variables:** recipes cannot set `PATH`, `HOME`, loader, proxy
  or CA variables, any `XDG_` or `SANDBOX_` variable, or
  `DBUS_SESSION_BUS_ADDRESS` (no session has a bus). These rules are the same in
  every wrapper. Each agent wrapper also protects its own prefix,
  configuration, approval and credential variables and the agent variables its
  profile lists in `native.protected_env`; the reference shell declares none
  beyond its `SANDBOX_CONTAINER_` names. `add` rejects them. If another wrapper
  installed a toolchain that sets a variable only that wrapper protects, the
  shell still receives it; a wrapper that protects it leaves it out of its
  sessions with a warning naming the toolchain.
- **Default toolchains:** in new sessions, their `PATH` entries come **after**
  the image's. They never replace the runtime's own `node` or `python3`, which
  OpenSpec and the image tools use.
- **Conflicts:** two default toolchains cannot share a command or a variable.
  Install a second version with `"default": false` and use it through its
  `env.sh`.
- **Writable locations:** `/sandbox-home` is read-only in shared-state mode, and
  `/tmp` is writable but `noexec`. Point caches to `/tmp` with literal values,
  and use `notes` to say when a tool must run files from a
  workspace directory.
- **Dependency downloads** (Maven, npm, pip, Cargo, Go modules) need network
  access that offline mode does not grant. Provide dependencies in
  the workspace, or use an unrestricted session.

#### Images

A recipe can also list container images. Sessions started while the library
holds at least one image get a private container engine that runs them
([Container tests](#container-tests)). Each image is one of:

| Image | Form |
| --- | --- |
| Registry image | `"<ref>@sha256:<digest>"`; a reference without a digest is refused |
| Local image | `{"local": "sha256:<full image ID>", "name": "localhost/<name>[:tag]"}` |

```json
{"schema": 2, "name": "postgres16", "version": "16.4", "default": false,
 "images": ["docker.io/library/postgres@sha256:<digest>"],
 "check": ["podman", "run", "--rm", "--network=none", "docker.io/library/postgres@sha256:<digest>", "postgres", "--version"]}
```

- **Store:** `add` keeps the images in the library's image store, `.images`,
  through a helper container of the engine image. Registry images are pulled on
  the host, with host CA trust when setup enabled it, and keep both their index
  and platform digests. A local image is copied from the host engine by its
  full ID (`podman image inspect --format '{{.Id}}' <image>`) and named as the
  recipe says; `add` fails if the host engine has no image with that ID. An image
  several toolchains list is stored once.
- **Image-only recipes** have no `sources`, `path` or `env`, and `default` must
  be `false`; `toolchains.md` lists their images with a `podman run` example.
- **Check:** for a recipe with images, `check` runs in the runtime image against
  a temporary engine like a session's, without network, so a check that runs
  the image proves it runs offline.
- **Live updates:** an image added while sessions run is usable by their engines
  at once. Removing an image, or replacing a toolchain with one that drops an
  image, waits until no session engine runs: the command fails and names the
  running sessions.
- **Catalog recipes** never list local images.
- **Cleanup:** image layers in `.images` can belong to your subordinate IDs, as in
  any rootless Podman storage. Remove image toolchains with `remove`, which
  deletes their layers through the helper; deleting the directory directly needs
  `podman unshare rm -rf`.

The catalog recipes pin the versions, digests and checksums below; the
recipe files hold the full values. See [the validation
record](docs/validation.md#toolchain-library-2026-11-13) for the checks.

| Name | Version | Source | Default | Notes |
| --- | --- | --- | --- | --- |
| `java21` | Temurin 21.0.13 | image `eclipse-temurin@sha256:0a3f3298…`, `/opt/java/openjdk` | yes | `JAVA_HOME` |
| `maven3.9` | 3.9.16 | image `maven@sha256:99e61abc…`, `/usr/share/maven` | yes | requires `java21`; local repository in `/tmp/m2`; harmless jansi warning |
| `go` | 1.27.4 | image `golang@sha256:4fa7c968…`, `/usr/local/go` | yes | `GOTOOLCHAIN=local`; caches in `/tmp`; `go test` needs `GOTMPDIR` in the workspace |
| `node24` | 24.22.3 | archive `node-v24.22.3-linux-x64.tar.xz` from `nodejs.org` | no | the image's Node.js 22 stays first |
| `python3.13` | 3.13.18 | python-build-standalone `20261110` `install_only` archive from GitHub | no | the image's `python3` stays first; virtual environments in the workspace |
| `rust` | 1.100.0 | `rustc`, `cargo` and `rust-std` (host and `x86_64-unknown-linux-musl`) archives from `static.rust-lang.org` | yes | target `x86_64-unknown-linux-musl` linked by `rust-lld`; crates with build scripts or procedural macros fail |

The runtime image has no C linker, so the `rust` recipe uses the musl target,
whose startup files ship with Rust, and links with `rust-lld`.

`SANDBOX_TOOLCHAIN_EXAMPLES=1 bash tests/run-runtime.sh --network -k
documented_toolchain` adds all six by name, which pulls and downloads them,
then checks them in an offline session.

### Using toolchains in the shell

The wrapper never edits shell startup files. The library contains a generated
`/toolchains/toolchains.md` with the usage rules and every installed toolchain,
plus a machine-readable `/toolchains/index.json`. Default toolchains are already
on `PATH`; any toolchain runs in one command with
`. /toolchains/<name>/env.sh && <command>`, which also works for toolchains
added after the session started. Agent wrappers point their agents at
`toolchains.md` through the agent's own instruction file.

SELinux and AppArmor enforcement were not tested with the library mount. On
hosts that enforce them, profile the tools you add.

## Shared sandbox components and the reference role

`network/`, `setup/`, `launcher/` and the shared tests listed in
`tests/test_alignment.py` are written here and copied unchanged to the Claude,
Codex, OpenCode, Pi and Antigravity wrappers. They contain no agent-specific
names. `launcher/core.sh` is the whole launcher of every wrapper: each
`<wrapper>-container.sh` is the same thin entry script, and `agent/launcher.sh`
holds the profile values the core needs and the agent's hooks
([docs/launcher-contract.md](docs/launcher-contract.md)). The shared launcher
tests (`tests/test_launcher.py`, with the fake engine `tests/fake_podman.py`)
run the core against fixture agent parts. Every
agent-specific value comes from the protected `agent/profile.json`; for this
shell:
- the wrapper name and the `SANDBOX_CONTAINER_*` variable prefix;
- the `localhost/sandbox-container*` images and `io.sandbox-container.*` labels;
- installation and state names;
- `/sandbox-home`, `bash` and `SANDBOX_CONTAINER_CONFIG_DIR`;
- no authentication method (`"auth": {}`) and no approval-bypass variable, so
  `agent/policies/default.json` declares no policy profiles.

Inside containers the sandbox uses neutral paths: `/opt/sandbox-egress`,
`/run/sandbox-egress`, `/tmp/sandbox-runtime` and the `sandbox-egress-guard`
binary. Shared tests run the shared modules against the agent-neutral fixture
profiles in `tests/fixtures/`, so they behave the same in every wrapper; only
tests that launch this checkout's wrapper use its real profile.

Each wrapper pins its copy to an annotated `sandbox-ref-N` tag of this
repository. Tags `sandbox-ref-1` to `sandbox-ref-18` were created while
`claude-container` held this role and keep their commits here. A shared change
gets a new tag and reaches every wrapper through `tools/propagate.py`, as
described in [docs/propagation.md](docs/propagation.md); a defect found in a
wrapper is fixed here first. An adoption is validated in its working session;
after it closes, `tools/adoption-run.sh` runs its checklist on WSL or the native
Linux host, with full logs and one archive.

## Verification

```bash
bash -n sandbox-container.sh
python3 -m unittest discover -s tests -v
bash tests/run-runtime.sh --wrapper
bash tests/run-runtime.sh
git diff --check
```

Unit and wrapper tests use synthetic HOME/state and a fake Podman, without host
credentials or a real engine. They need executable temporary storage with Unix
permissions; set `SANDBOX_TEST_TMPDIR` to a suitable native Linux directory when
`/tmp` is `noexec`. Runtime tests are opt-in and require a built image and a
rootless engine. The runner uses a disposable native Linux volume for state,
preserves host absolute paths, and removes only its own test resources. See
`AGENTS.md` for every runner mode and [docs/validation.md](docs/validation.md)
for recorded results.
