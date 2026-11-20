# Sandbox shell in Podman

`sandbox-container.sh` opens a Bash shell in a read-only, rootless Podman
container with every sandbox feature of the agent wrappers: the protected
offline bootstrap (Landlock and seccomp), local qualification, guided setup,
resource budgets, private state, the toolchain library, host CA trust and
optional Podman delegation. Sessions are **offline by default**;
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
confirmation. This enables a host launch service; application delegation remains
a separate unrestricted-only choice. No `sudo`, lingering or WSL/system-wide
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

## Enable the launch service or optional Podman delegation

Restricted networking currently requires the tested same-host Unix launch
service, even with delegation disabled. An unrestricted local session needs no
API service unless `SANDBOX_CONTAINER_PODMAN=1` is selected. Host Podman is always
required for image operations and launch. See the network setup below for the
protected installation required by restricted modes.

Every session verifies that its launch engine is Linux and rootless before
image inspection, build, or launch. Unrestricted local Podman needs no API service when
delegation is disabled. An explicit same-host Unix `CONTAINER_HOST` is also
supported, including when this wrapper runs inside another container; launch
verification then queries that service even without delegating it to the shell.
Named `CONTAINER_CONNECTION` contexts, implicit remote contexts, TCP/SSH
(including the Podman machine connection that `podman.exe` uses), and rootful
engines are unsupported. On Windows, the PowerShell entry runs the sandbox
inside the Podman machine instead; see
[Windows with Podman machine](#windows-with-podman-machine). All bind sources and build
paths must exist on the same Linux host at their original absolute paths.
Unix transport alone does not prove that a forwarded service is on that host.
Launch-engine and enabled delegation verification each require exactly one
response record, with no terminator or one final LF. Additional blank or nonblank
records, including extra trailing LF characters, stop startup before image
inspection, explicit builds, or launch. Query failures remain failures even if
stdout looks valid; delegated query errors identify the selected endpoint.
Delegated socket responses containing any CR character, including a CRLF
terminator, are rejected before field parsing or use of the reported host path.
The endpoint must contain an absolute socket pathname beyond `/`; `unix://`,
`unix:///`, slash-only paths, and relative Unix paths fail before any engine
query, even when delegation is disabled or a delegation override is supplied.

When delegation is enabled, the selected socket is the first of:

1. Nonempty `SANDBOX_CONTAINER_PODMAN_SOCKET` (absolute path, without `unix://`).
2. The wrapper's explicit Unix `CONTAINER_HOST` (with `unix://` removed).
3. `${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock`.

The socket must be accessible and serve a rootless engine that reports an
absolute host-side socket path. With a remapped socket, the wrapper queries the
client-visible path and binds the reported host-side path into the session.
The launch and delegation services must be on the same host; a delegation
override does not change the launch engine. Choose **one** setup method below.

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

### Verify the socket before starting an enabled session

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
podman_socket="${SANDBOX_CONTAINER_PODMAN_SOCKET:-${CONTAINER_HOST#unix://}}"
podman_socket="${podman_socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
test -S "$podman_socket" && echo "Socket exists"
podman --remote --url "unix://$podman_socket" info --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}'
```

Continue only if the socket exists and the API command succeeds and prints
`true` followed by an absolute host-side socket path. With
`SANDBOX_CONTAINER_PODMAN=1`, the wrapper enforces this check through
that exact socket before image operations or container startup. A socket file
alone does not prove that a service is listening or that its engine is rootless.
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
| `unrestricted` | Explicit ordinary runtime networking; socket delegation is eligible |
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

Every shell container, in both modes and with Podman delegation, explicitly
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
`CONTAINER_NAME`. `SANDBOX_CONTAINER_ENV_VARS` lists further host variable names
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

### Allowing Podman access inside the container

To grant a session access to the host Podman API, complete the optional socket
setup and verification above, then run:

```bash
SANDBOX_CONTAINER_NETWORK=unrestricted SANDBOX_CONTAINER_PODMAN=1 ./sandbox-container.sh
```

Only the exact value `1` enables access. An unset or empty variable, `0`,
`true`, `yes`, and every other value disable access without an error. When
disabled, the wrapper skips delegation-endpoint validation and separate queries,
does not mount the host socket, and explicitly removes `CONTAINER_HOST` from
the container environment, including image or engine defaults. The host client
retains any Unix `CONTAINER_HOST` needed to launch the session. When enabled,
it mounts the socket at `/run/podman/podman.sock` and sets
`CONTAINER_HOST=unix:///run/podman/podman.sock` in the session.
Mandatory launch-engine verification still runs in either mode.
A missing or invalid socket stops an enabled launch with setup instructions.
The wrapper also queries the selected service and accepts only a successful
`true` rootless result and an absolute host-side socket path. An unreachable
service, rootful engine, or unexpected
result stops the launch before any image check, build, or container startup.

Migration: earlier versions always exposed the host Podman socket. Existing
workflows that launch child containers must now select explicit unrestricted
networking as well as exact `SANDBOX_CONTAINER_PODMAN=1`. Offline mode rejects
that combination because the host API can create unfiltered child containers.
The Podman client remains installed in the image. This switch controls the
host API access supplied by the wrapper; it does not block independently
configured remote endpoints or sockets exposed through other selected mounts.

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

Migration: earlier versions always mounted the host certificate directory and
set CA variables. Those sessions no longer trust the host CA by default. Set
`SANDBOX_CONTAINER_TRUST_HOST_CA=1` to restore that behavior.

## Windows with Podman machine

On Windows, `sandbox-container.ps1` starts the sandbox from PowerShell on the
local rootless engine of a Podman machine that Podman Desktop created with the
WSL provider. The session runs inside the machine's WSL distribution
(`podman-machine-default`, user `user`). The entry uses neither `podman.exe`
nor the machine's SSH or API connection, so it works while other WSL
distributions, such as Ubuntu, are running.

Prerequisites:

- Windows PowerShell 5.1 or PowerShell 7, with a policy that allows local
  scripts, for example `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`;
- a Podman machine with the WSL provider, created with Podman Desktop, and
  started by Podman (Podman Desktop or `podman machine start`) before setup and
  sessions;
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
The machine has no launch service, so setup offers only unrestricted
networking. Rerun setup after updating the checkout, and after the machine is
recreated.

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

- the location is a network share, a path inside a WSL distribution, a drive
  the distribution does not mount, or not a file system path;
- the project or the worktree parent contains the checkout, or lies inside it;
- the project is a Windows system or profile folder (see
  [Hardening, budgets and lifetime](#hardening-budgets-and-lifetime)).

The exit status, the terminal and Ctrl+C work as on Linux. Closing the window
also ends the session and removes its container.

| Variable | Meaning |
| --- | --- |
| `SANDBOX_CONTAINER_WSL_DISTRO` | WSL distribution (default `podman-machine-default`) |
| `SANDBOX_CONTAINER_WSL_USER` | user in the distribution (default `user`) |
| `SANDBOX_CONTAINER_WSL_INSTALLATION` | absolute installation path in the distribution, when setup used another one |

Set them with `$env:NAME = 'value'`. The entry forwards to the launcher in the
distribution, by name, the other `SANDBOX_CONTAINER_*` variables whose names
use only letters, digits and `_`, `SANDBOX_CONTAINER_CONFIG_DIR` when it holds
a distribution path (starting with `/`), and the names listed in
`SANDBOX_CONTAINER_ENV_VARS`. A Windows path in
`SANDBOX_CONTAINER_CONFIG_DIR` is skipped with a notice, and the directory
saved by setup applies. It forwards no other Windows variable. Path values
are distribution paths, such as `/home/user/...`.

Limits on Windows:

- Only unrestricted networking without Podman delegation.
  `SANDBOX_CONTAINER_NETWORK` may only be unset or `unrestricted`;
  `SANDBOX_CONTAINER_PODMAN=1` and `--container-qualify` are refused.
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
- A behavioral antivirus may quarantine checkout files while they are cloned
  or extracted. Bitdefender's Advanced Threat Control (`Atc4.Detection`) once
  removed `tests/fixtures/shell-agent/launcher.sh`, which only the Linux tests
  use. Setup and the entry fail when a file they need is missing: restore it
  from the antivirus quarantine, or ask the administrator, and report the
  false positive to the vendor.

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

**With `SANDBOX_CONTAINER_PODMAN=1`, the session can control the service user's
containers and volumes and request new host bind mounts beyond the workspace.**
The socket removes the project-only filesystem boundary. To pin the endpoint
explicitly, use `SANDBOX_CONTAINER_PODMAN_SOCKET=/run/user/$(id -u)/podman/podman.sock`
alongside `SANDBOX_CONTAINER_PODMAN=1`; runtime-directory or Unix launch endpoint
settings otherwise affect selection.

Internal sandboxing (Bubblewrap inside the session), filesystem isolation, the
network boundary and socket authority are separate controls. The shell has no
approval system: the wrapper reads no approval-bypass variable, so agent
variables such as `CLAUDE_YOLO` have no effect. Delegation depends only on exact
`SANDBOX_CONTAINER_PODMAN=1` with explicit unrestricted networking, in either
state mode and with any worktree scope or Bash command; offline mode rejects it.

### Hardening, budgets and lifetime

Every shell container runs with `--cap-drop=all` and
`--security-opt=no-new-privileges` in every mode. Tools that need a capability
are unsupported; the wrapper never adds one back. The delegated Podman client
works without capabilities, but the socket still grants host engine authority.

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
container gets a soft and hard process rlimit (`--ulimit nproc=N:N`) at the
selected budget, and the notice reads `agent process budget enforced through the
process rlimit (512 tasks of the session user, threads included)`. The limit is
per session: Linux 5.14 and later count it per user namespace, and every
container has its own. The session cannot raise it, because it has no
capabilities. Container startup uses a few of these tasks (about 13 were
measured), so slightly fewer than `N` processes are available. Through a Podman
API service more of them can be taken: in the runtime suite on Podman machine
6.1.4, a budget of 32 left too few to start the container. The fallback
applies only when the engine reports kernel 5.14 or later
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
./sandbox-container.sh --container-toolchain add java21.json   # install or replace from a recipe
./sandbox-container.sh --container-toolchain list              # name, version, default, size, verified base
./sandbox-container.sh --container-toolchain remove java21
./sandbox-container.sh --container-toolchain verify [java21]   # rerun the checks on the current runtime image
```

- **Sources:** a toolchain is a relocatable directory tree, taken either from
  a path inside an OCI image referenced by `@sha256:` digest, or from a local
  archive with its SHA-256. The command never downloads archives.
- **Pulls:** pulling a missing image requires exact
  `SANDBOX_CONTAINER_MAINTENANCE=1`. Like image builds, the pull happens on the
  host, outside runtime filtering.
- **Extraction:** it rejects absolute paths, `..`, device nodes and links
  that leave the toolchain, and clears setuid and setgid bits.
- **Atomic changes:** changes take a library lock and replace directories
  atomically.
- **Check:** before accepting a toolchain, `add` runs the recipe's `check`
  command in the runtime image, without network and with the session's
  identity and hardening. A toolchain that needs a newer C library than the
  image's glibc fails here. The manifest records the base image from the
  installed `Containerfile`. If that base changes, the toolchain stays visible
  but loses its default environment until `verify` succeeds, and the launcher
  prints one warning naming it.

### Recipes

A recipe is a JSON file that the operator keeps and reviews:

| Key | Meaning |
| --- | --- |
| `schema`, `name`, `version` | `1`; `[a-z0-9][a-z0-9._-]*`; free version text |
| `source` | `{"image": "<ref>@sha256:<digest>", "path": "/abs/path"}` or `{"archive": "/abs/file.tar.xz", "sha256": "<hex>", "strip_components": 1}` |
| `path` | directories relative to the toolchain, added to `PATH` (default `["bin"]`) |
| `env` | variables: `{"toolchain": "<relative path>"}` or `{"value": "<literal>"}` |
| `requires` | other toolchains whose environment is loaded first |
| `notes` | short instructions shown in `toolchains.md` |
| `check` | command run in the runtime image before the toolchain is accepted |
| `default` | `true` adds the toolchain to new sessions' environment |

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

The examples below were verified with the versions, digests and checksums
shown. See [the validation record](docs/validation.md#toolchain-library-2026-11-13).

The recipes are in [`docs/toolchains/`](docs/toolchains/), and download
sources are listed in `docs/toolchains/sources.json`:

| Recipe | Version | Source | Default | Notes |
| --- | --- | --- | --- | --- |
| `java21.json` | Temurin 21.0.13 | image `eclipse-temurin@sha256:0a3f3298…`, `/opt/java/openjdk` | yes | `JAVA_HOME` |
| `maven3.9.json` | 3.9.16 | image `maven@sha256:99e61abc…`, `/usr/share/maven` | yes | requires `java21`; local repository in `/tmp/m2`; harmless jansi warning |
| `go.json` | 1.27.4 | image `golang@sha256:4fa7c968…`, `/usr/local/go` | yes | `GOTOOLCHAIN=local`; caches in `/tmp`; `go test` needs `GOTMPDIR` in the workspace |
| `node24.json` | 24.22.3 | archive `node-v24.22.3-linux-x64.tar.xz` | no | the image's Node.js 22 stays first |
| `python3.13.json` | 3.13.18 | archive python-build-standalone `20261110` `install_only` | no | the image's `python3` stays first; virtual environments in the workspace |
| `rust.json` | 1.100.0 | image built from `rust-musl.Containerfile` | yes | target `x86_64-unknown-linux-musl` linked by `rust-lld`; crates with build scripts or procedural macros fail |

Notes on using the recipes:
- **Archive recipes:** download the file, check it against the recipe's
  SHA-256, and set `archive` to its absolute path.
- **Rust:** the runtime image has no C linker, so the recipe uses the musl
  target, whose startup files ship with Rust, and links with `rust-lld`. Build
  the image, then put its local digest in the recipe:

  ```bash
  podman build --tag localhost/sandbox-rust-musl:local \
      --file docs/toolchains/rust-musl.Containerfile docs/toolchains
  podman image inspect --format '{{.Digest}}' localhost/sandbox-rust-musl:local
  ```

`SANDBOX_TOOLCHAIN_EXAMPLES=1 bash tests/run-runtime.sh --network -k
documented_toolchain` downloads, pulls and builds all six, then checks them in
an offline session.

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
wrapper is fixed here first.

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
