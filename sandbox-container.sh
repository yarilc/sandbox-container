#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'sandbox-container: %s\n' "$*" >&2; exit 1; }

# Keep final LF bytes while retaining the query's own exit status and stderr.
capture_response() {
    local destination=$1 captured query_status
    shift
    if captured=$("$@"; query_status=$?; printf '\034'; exit "$query_status"); then
        printf -v "$destination" '%s' "${captured%$'\034'}"
    else
        return "$?"
    fi
}

usage() {
    cat <<'EOF'
Usage: sandbox-container.sh [container option] [bash arguments...]

Opens a Bash shell in a read-only Podman container: the reference sandbox for
the agent wrappers. The current directory (or its parent with
--container-git-worktree), the shell configuration directory and the shared
OpenSpec configuration are mounted read/write. Sessions are offline by default.

Container options:
  --container-setup      interactively prepare a complete user installation
  --container-qualify    verify a prepared restricted installation with fixed local controls
  --container-build      build or refresh the container image before starting
  --container-shell      accepted for compatibility; the session is always Bash
  --container-git-worktree mount the parent of the current directory read/write
                         for Git worktrees; the container starts in the current directory
  --container-toolchain  manage the shared read-only toolchain library; must be first:
                         add <recipe.json> | list | remove <name> | verify [<name>]
  --container-help       show this wrapper help

All other arguments are passed to Bash unchanged, for example -c 'git status'.

Environment:
  SANDBOX_CONTAINER_NETWORK offline (default when unset or empty) or unrestricted;
                           provider is unavailable: the reference profile declares
                           no authentication method
  SANDBOX_CONTAINER_MAINTENANCE authorize image preparation only with exact value 1
  SANDBOX_CONTAINER_IMAGE  image name (default: localhost/sandbox-container:latest)
  SANDBOX_CONTAINER_CONFIG_DIR shell configuration directory with the Bash history
                           (default: ~/.config/sandbox-container)
  SANDBOX_CONTAINER_STATE_DIR optional isolated home; unset keeps shared configuration
                           (must not be, contain or lie inside the workspace)
  SANDBOX_CONTAINER_PODMAN_SOCKET optional absolute delegation socket override
  SANDBOX_CONTAINER_PODMAN enable host Podman API access only with exact value 1
                           and explicit unrestricted mode (default: disabled; all
                           other values disable access); requires a reachable
                           rootless service; failed verification stops startup
                           before image operations
  SANDBOX_CONTAINER_TRUST_HOST_CA  trust a host CA bundle: 1, true, or yes (default: disabled)
  SANDBOX_CONTAINER_CA_BUNDLE      CA bundle file to trust (default: first of
                                   /etc/ssl/certs/ca-certificates.crt and
                                   /etc/pki/tls/certs/ca-bundle.crt)
  SANDBOX_CONTAINER_MEMORY_LIMIT   shell memory, integer with k/m/g unit (default: 4g)
  SANDBOX_CONTAINER_CPU_LIMIT      shell CPUs, up to 3 decimals (default: 2)
  SANDBOX_CONTAINER_PIDS_LIMIT     shell process limit (default: 512)
                                   Budgets cannot be disabled; managed launches use
                                   the values saved by setup unless exported
  SANDBOX_CONTAINER_RUN_TIMEOUT    container lifetime in whole seconds
                                   (default: 0, disabled by default)
  SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE  exact 1 permits a refused sensitive
                                   workspace with a warning (default: disabled)
  SANDBOX_CONTAINER_TOOLCHAINS     0, false, or no omits the read-only /toolchains
                                   library mount (default: mounted)
  SANDBOX_CONTAINER_TOOLCHAINS_DIR toolchain library shared by the wrappers (default:
                                   ${XDG_DATA_HOME:-~/.local/share}/sandbox-toolchains)

Offline use needs a protected installation: new users first run
  bash ./sandbox-container.sh --container-setup
and then use the managed launch command printed by setup from a workspace. An
offline launch, including the default mode, from a location without a protected
installation stops with this guidance before engine queries or state creation.
Direct use from a checkout needs explicit unrestricted networking, for example:
  SANDBOX_CONTAINER_NETWORK=unrestricted bash ./sandbox-container.sh
  SANDBOX_CONTAINER_NETWORK=unrestricted SANDBOX_CONTAINER_MAINTENANCE=1 bash ./sandbox-container.sh --container-build
Offline sessions have no external network. Restricted failures never retry
unrestricted. This wrapper replaces the Claude wrapper only as the reference for
the shared sandbox components; existing agent installations are unaffected.

Configured launch requires a verified Linux rootless engine, locally or via an explicit
same-host Unix CONTAINER_HOST with an absolute socket pathname beyond /.
Named connections and TCP/SSH are unsupported.
Delegation endpoint: explicit socket override, Unix CONTAINER_HOST, then
${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock.
The socket permits host mounts beyond the workspace. Worktree mode exposes the
entire parent read/write.
State directories must belong to the caller and deny group/other access.
Unset SANDBOX_CONTAINER_CONFIG_DIR when selecting an isolated home; no state is imported.
Temporary /tmp, /run, and /var/tmp mounts are noexec, limited to 256/16/256 MiB.
Host GNU timeout is required. Shutdown is bounded to 20 seconds, with at most
5 seconds for graceful exit before forced owned-container removal. Cleanup
failures are reported without changing the shell or first signal status.
Engine verification replies must contain one record, with no terminator or a
single final LF; extra blank or nonblank records stop startup before builds.
Delegated socket verification also rejects any CR character, including CRLF.
Offline mode rejects Podman delegation. Network restriction requires a protected
installation outside writable workspace/state trees and host Python 3. Eligible
Linux/WSL2 x86_64 installations require a same-host Unix rootless Netavark
service, Podman >= 4.9, standard OCI seccomp and usable Landlock ABI >= 3.
Unsupported setups fail closed. Image pulls/build RUN steps remain outside
runtime filtering and require separate maintenance authorization.
Restricted startup requires a protected static guard and SHA-256 manifest in
network/bin plus a current protected local qualification report. Run setup or
--container-qualify alone after preparation or relevant updates. Kernel/server
exact pins and upper bounds do not determine support. SELinux/AppArmor remains
active when enabled; compatibility is not guaranteed and denials stop startup.
The guard adds
unprivileged Landlock and restrictive seccomp, preserving the OCI profile.
New Unix services are unavailable; fixed-peer pairs may have private inert names.
See network/README.md for packaging and docs/validation.md for measured evidence.
Every shell container, in all modes including delegation, drops all
capabilities, enables no-new-privileges and receives the memory, CPU and process
budgets whose cgroup v2 controller the rootless engine delegates; a budget whose
controller is missing is not enforced and a notice names it. The created
configuration is checked before the shell starts; a delegated limit that
is ignored stops startup. Without memory or process budgets a session can exhaust
host memory or processes for your user.
Budgets and tmpfs sizes do not limit workspace or state storage growth.
The workspace mount (the parent in worktree mode) must not be /, your home,
/home, /root, /etc, /usr, /var, /bin, /sbin, /lib, /lib64, /boot, /opt, /srv,
/mnt, /media, /proc, /sys, /dev, /run, /tmp or a WSL drive root such as /mnt/c.
A reached lifetime limit is reported; the exit status is preserved.
Qualification is credential-free, uses disposable fixed controls and never grants
image maintenance or forwards a command. ABI queries alone do not qualify an
installation. Changed boot, engine/backend/security, code/images, policy/profile,
CA trust or hardening, including budgets and lifetime, invalidates evidence.
Unknown active LSM policy identity requires the gate each launch.
Locally-qualified installations are visibly distinguished from exact
release-measured acceptance records.
EOF
}

# Setup must diagnose prerequisites before normal runtime configuration exists.
# Help takes precedence regardless of option order and never loads setup code.
for arg in "$@"; do
    [[ "$arg" != --container-help ]] || { usage; exit 0; }
done
# Toolchain management runs on the host and never starts a session.
if [[ "${1:-}" == --container-toolchain ]]; then
    [[ "${2:-}" != launch-env ]] || die 'usage: --container-toolchain add <recipe.json> | list | remove <name> | verify [<name>]'
    command -v python3 >/dev/null || die 'host Python 3 is required for the toolchain library'
    toolchain_script=$(readlink -f -- "${BASH_SOURCE[0]}")
    exec python3 -I "$(dirname -- "$toolchain_script")/setup/toolchains.py" "${@:2}"
fi
for arg in "$@"; do
    if [[ "$arg" == --container-qualify ]]; then
        [[ $# == 1 ]] || die '--container-qualify must be used alone'
        command -v python3 >/dev/null || die 'host Python 3 is required for qualification'
        script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
        script_dir=$(dirname -- "$script_path")
        exec python3 -I "$script_dir/network/qualify.py" qualify
    fi
done
for arg in "$@"; do
    if [[ "$arg" == --container-setup ]]; then
        [[ $# == 1 ]] || die '--container-setup must be used alone'
        [[ -t 0 && -t 1 ]] || die '--container-setup requires an interactive terminal'
        command -v python3 >/dev/null || die 'host Python 3 is required for interactive setup'
        setup_script=$(readlink -f -- "${BASH_SOURCE[0]}")
        exec python3 -I "$(dirname -- "$setup_script")/setup/setup.py"
    fi
done

build_image=0
qualification_probe=0
git_worktree=0
args=()
for arg in "$@"; do
    case "$arg" in
        --container-qualify-probe)
            [[ $# == 1 ]] || die 'the fixed qualification probe must be used alone'
            qualification_probe=1 ;;
        --container-help) usage; exit 0 ;;
        --container-build) build_image=1 ;;
        --container-shell) ;;  # The session is always Bash.
        --container-git-worktree) git_worktree=1 ;;
        --container-toolchain) die '--container-toolchain must be the first argument' ;;
        *) args+=("$arg") ;;
    esac
done

# Offline is the default runtime mode; unrestricted applies only when explicit.
network_mode=${SANDBOX_CONTAINER_NETWORK:-offline}
case "$network_mode" in
    offline|unrestricted) ;;
    provider) die 'SANDBOX_CONTAINER_NETWORK=provider is unavailable: the reference profile declares no authentication method; use offline or unrestricted' ;;
    *) die 'SANDBOX_CONTAINER_NETWORK must be offline or unrestricted' ;;
esac
# Host tools are diagnosed later, so a missing readlink leaves the path empty here.
script_path=$(readlink -f -- "${BASH_SOURCE[0]}" 2>/dev/null) || script_path=''
script_dir=${script_path%/*}
# An offline session needs a protected installation with the built guard and its
# manifest. Without one, give setup guidance before any engine or state operation;
# session.py prepare still validates the installation fully.
if [[ "$network_mode" == offline ]] \
    && { [[ -z "$script_path" ]] || ! compgen -G "$script_dir/network/bin/*.sha256" >/dev/null; }; then
    setup_wrapper=${BASH_SOURCE[0]}
    [[ "$setup_wrapper" == /* ]] || setup_wrapper="$PWD/$setup_wrapper"
    printf -v setup_command 'bash %q --container-setup' "$setup_wrapper"
    die "setup required: offline sessions need a protected installation; run $setup_command and use the managed launcher, or set SANDBOX_CONTAINER_NETWORK=unrestricted for a direct session"
fi

boolean() {
    case "${2,,}" in
        1|true|yes) printf 1 ;;
        ''|0|false|no) printf 0 ;;
        *) die "$1 must be 0, 1, true, false, yes, or no" ;;
    esac
}
toolchains_enabled=$(boolean SANDBOX_CONTAINER_TOOLCHAINS "${SANDBOX_CONTAINER_TOOLCHAINS:-1}")
podman_access=0
[[ "${SANDBOX_CONTAINER_PODMAN:-}" != 1 ]] || podman_access=1
trust_host_ca=$(boolean SANDBOX_CONTAINER_TRUST_HOST_CA "${SANDBOX_CONTAINER_TRUST_HOST_CA:-}")
if [[ "$network_mode" != unrestricted ]] && ((podman_access)); then
    die 'restricted networking rejects SANDBOX_CONTAINER_PODMAN=1: the host API bypasses egress enforcement; select explicit unrestricted mode for delegation'
fi
[[ -z "${SANDBOX_CONTAINER_STATE_DIR:-}" || -z "${SANDBOX_CONTAINER_CONFIG_DIR:-}" ]] \
    || die 'SANDBOX_CONTAINER_STATE_DIR conflicts with SANDBOX_CONTAINER_CONFIG_DIR; unset SANDBOX_CONTAINER_CONFIG_DIR to isolate state'

# Agent budgets and lifetime. network/agent_budgets.py implements the same
# rules for setup and qualification; unrestricted installs may lack host Python.
# Only an unset budget selects its default; no value disables a budget.
memory_text=${SANDBOX_CONTAINER_MEMORY_LIMIT-4g}
cpu_text=${SANDBOX_CONTAINER_CPU_LIMIT-2}
pids_text=${SANDBOX_CONTAINER_PIDS_LIMIT-512}
timeout_text=${SANDBOX_CONTAINER_RUN_TIMEOUT:-0}
memory_bytes=0
if [[ "$memory_text" =~ ^([1-9][0-9]{0,15})([kmgKMG])$ ]]; then
    case "${BASH_REMATCH[2],,}" in
        k) unit=1024 ;;
        m) unit=1048576 ;;
        *) unit=1073741824 ;;
    esac
    ((10#${BASH_REMATCH[1]} > (1 << 50) / unit)) || memory_bytes=$((10#${BASH_REMATCH[1]} * unit))
fi
((memory_bytes > 0)) || die 'SANDBOX_CONTAINER_MEMORY_LIMIT must be a positive integer with unit k, m or g, for example 4g'
cpu_nano=0
if [[ "$cpu_text" =~ ^([0-9]{1,4})(\.([0-9]{1,3}))?$ ]]; then
    fraction=${BASH_REMATCH[3]}000
    cpu_nano=$((10#${BASH_REMATCH[1]} * 1000000000 + 10#${fraction:0:3} * 1000000))
    ((cpu_nano <= 1024000000000)) || cpu_nano=0
fi
((cpu_nano > 0)) || die 'SANDBOX_CONTAINER_CPU_LIMIT must be a positive number of CPUs with at most 3 decimals, for example 2 or 1.5'
[[ "$pids_text" =~ ^(0|[1-9][0-9]{0,9})$ ]] && ((pids_text > 0 && pids_text <= 4194304)) \
    || die 'SANDBOX_CONTAINER_PIDS_LIMIT must be a positive integer process count up to 4194304'
[[ "$timeout_text" =~ ^(0|[1-9][0-9]{0,9})$ ]] && ((timeout_text <= 2147483647)) \
    || die 'SANDBOX_CONTAINER_RUN_TIMEOUT must be whole seconds; 0 disables the lifetime limit'
pids_limit=$((10#$pids_text))
run_timeout=$((10#$timeout_text))

# Refuse sensitive writable workspaces before any engine or state operation.
workspace=$(pwd -P)
workspace_mount=$workspace
((git_worktree == 0)) || workspace_mount=$(dirname -- "$workspace")
[[ "${HOME:-}" == /* ]] || die 'HOME must be an absolute path'
# Builtins only: tool prerequisites are diagnosed later. A missing home cannot
# be a workspace, so its lexical path is sufficient then.
physical_home=$(cd -- "$HOME" 2>/dev/null && pwd -P) || physical_home=$HOME
unsafe_workspace=0
case "$workspace_mount" in
    /|/home|/root|/etc|/usr|/var|/bin|/sbin|/lib|/lib64|/boot|/opt|/srv|/mnt|/media|/proc|/sys|/dev|/run|/tmp)
        unsafe_workspace=1 ;;
esac
[[ "$workspace_mount" != "$physical_home" && ! "$workspace_mount" =~ ^/mnt/[A-Za-z]$ ]] || unsafe_workspace=1
if ((unsafe_workspace)); then
    [[ "${SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE:-}" == 1 ]] \
        || die "refusing sensitive workspace $workspace_mount; launch from a project subdirectory or set exact SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1"
    printf 'sandbox-container: WARNING: sensitive workspace explicitly exposed read/write: %s\n' "$workspace_mount" >&2
fi

command -v podman >/dev/null || die 'Podman is required on the host'
command -v timeout >/dev/null && [[ $(timeout --version 2>/dev/null) == *'GNU coreutils'* ]] \
    || die 'GNU timeout is required on the host; install GNU coreutils'
[[ -n "$script_path" ]] || die 'GNU readlink is required on the host; install GNU coreutils'
# Isolated credentials and history must never land in, or contain, the workspace.
# Compare physical paths; readlink -m also resolves a directory not created yet.
if [[ -n "${SANDBOX_CONTAINER_STATE_DIR:-}" ]]; then
    state_physical=$(readlink -m -- "$SANDBOX_CONTAINER_STATE_DIR")
    [[ "$state_physical/" != "$workspace_mount/"* && "$workspace_mount/" != "$state_physical/"* ]] \
        || die "SANDBOX_CONTAINER_STATE_DIR must not overlap the workspace: $SANDBOX_CONTAINER_STATE_DIR"
fi
# Unix service access also supports running this wrapper inside another container
# on the same host. TCP/SSH transports and Podman Machine are not supported.
[[ -z "${CONTAINER_CONNECTION:-}" ]] || die 'named remote connections are not supported; use local Podman or a local Unix CONTAINER_HOST'
case "${CONTAINER_HOST:-}" in
    '') ;;
    unix://*)
        launch_socket=${CONTAINER_HOST#unix://}
        [[ "$launch_socket" == /* && -n "${launch_socket//\//}" ]] \
            || die 'CONTAINER_HOST requires an absolute Unix socket path beyond /'
        ;;
    *) die 'remote TCP/SSH Podman contexts are not supported; use a local Unix socket' ;;
esac
capture_response runtime_info podman info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}' \
    || die 'cannot query Podman; check the local rootless service'
runtime_info=${runtime_info%$'\n'}
[[ "$runtime_info" != *$'\n'* ]] || die 'invalid Podman engine response: expected one record with at most one final LF'
[[ "$runtime_info" == "true linux false" || "$runtime_info" == "true linux true" ]] || die 'a verified Linux rootless Podman engine is required (unexpected engine response)'
read -r _ _ remote <<< "$runtime_info"
if [[ "$remote" == true && "${CONTAINER_HOST:-}" != unix:///* ]]; then
    die 'remote Podman contexts are not supported; set CONTAINER_HOST to a local Unix socket'
fi

# A budget is enforced only when the verified engine reports its cgroup v2
# controller as delegated. Unenforced budgets are not requested, are announced,
# and must be absent from the created configuration (see network/agent_budgets.py).
capture_response cgroup_controllers podman info --format '{{.Host.CgroupControllers}}' \
    || die 'cannot query the rootless cgroup controllers'
cgroup_controllers=${cgroup_controllers%$'\n'}
[[ "$cgroup_controllers" =~ ^\[([a-z_]+( [a-z_]+)*)?\]$ ]] \
    || die 'unverifiable cgroup controller list from the Podman engine'
controller_delegated() {
    [[ " ${cgroup_controllers:1:${#cgroup_controllers}-2} " == *" $1 "* ]]
}
budget_args=()
expected_memory=0
expected_cpu=0
pids_enforced=0
if controller_delegated memory; then
    budget_args+=("--memory=$memory_bytes")
    expected_memory=$memory_bytes
else
    printf 'sandbox-container: agent memory budget not enforced: cgroup controller memory is not delegated to the rootless engine\n' >&2
fi
if controller_delegated cpu; then
    budget_args+=("--cpus=$cpu_text")
    expected_cpu=$cpu_nano
else
    printf 'sandbox-container: agent CPU budget not enforced: cgroup controller cpu is not delegated to the rootless engine\n' >&2
fi
if controller_delegated pids; then
    budget_args+=("--pids-limit=$pids_limit")
    pids_enforced=1
else
    # Override any containers.conf default that would request the missing controller.
    budget_args+=(--pids-limit=-1)
    printf 'sandbox-container: agent process budget not enforced: cgroup controller pids is not delegated to the rootless engine\n' >&2
fi
if [[ "$network_mode" != unrestricted ]]; then
    command -v python3 >/dev/null || die 'host Python 3 is required for restricted network policy validation'
    [[ "$remote" == true ]] || die 'restricted networking currently requires the tested same-host Unix service; local-engine enforcement is unverified'
    capture_response network_backend podman info --format '{{.Host.NetworkBackend}}' \
        || die 'cannot verify restricted network backend'
    capture_response network_version podman version --format '{{.Server.Version}}' \
        || die 'cannot verify restricted network server version'
    capture_response network_platform podman info --format '{{json .Host}}' \
        || die 'cannot verify restricted platform security policy'
elif ((qualification_probe)); then
    die 'qualification probes require restricted networking'
fi

caller_uid=$(id -u)
caller_gid=$(id -g)
socket="${SANDBOX_CONTAINER_PODMAN_SOCKET:-${XDG_RUNTIME_DIR:-/run/user/$caller_uid}/podman/podman.sock}"
if [[ -z "${SANDBOX_CONTAINER_PODMAN_SOCKET:-}" && "${CONTAINER_HOST:-}" == unix:///* ]]; then
    socket=${CONTAINER_HOST#unix://}
fi
if ((podman_access)); then
    [[ "$socket" == /* ]] || die "Podman socket must be an absolute path: $socket"
    [[ -S "$socket" && -r "$socket" && -w "$socket" ]] || die "Podman socket not accessible: $socket; enable 'systemctl --user start podman.socket' or start 'podman system service --time=0'"
    socket=$(readlink -f -- "$socket")
    capture_response socket_info podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}' \
        || die "cannot query Podman socket: $socket; check the rootless service, permissions and SELinux policy"
    [[ "$socket_info" != *$'\r'* ]] || die "invalid Podman socket response: $socket"
    socket_info=${socket_info%$'\n'}
    [[ "$socket_info" != *$'\n'* ]] || die "invalid Podman socket response: $socket"
    read -r socket_rootless host_socket <<< "$socket_info"
    # Podman 5 reports the service socket as a unix:// URL; earlier releases report the bare path.
    host_socket=${host_socket#unix://}
    [[ "$socket_rootless" == true ]] || die "Podman socket must serve a rootless engine: $socket"
    # A wrapper already inside a container sees a remapped Unix socket. Bind
    # sources are resolved by the service, so use its host-side socket path.
    [[ "$host_socket" == /* && "$host_socket" != *$'\n'* ]] || die "Podman socket $socket did not report an absolute host socket path"
fi

image="${SANDBOX_CONTAINER_IMAGE:-localhost/sandbox-container:latest}"
state_dir="${SANDBOX_CONTAINER_STATE_DIR:-}"

private_directory() {
    local path=$1 mode
    [[ -d "$path" && -r "$path" && -w "$path" && -x "$path" ]] \
        || die "state directory is not accessible: $path"
    [[ $(stat -c '%u' -- "$path") == "$caller_uid" ]] \
        || die "state directory must belong to the calling user: $path"
    mode=$(stat -c '%a' -- "$path")
    (( (8#$mode & 077) == 0 )) \
        || die "state directory must be private: $path (chmod 700; use native Linux storage if permissions are not enforced)"
}

create_private_directory() (
    umask 077
    mkdir -p -- "$@"
)

state_mounts=()
if [[ -n "$state_dir" ]]; then
    create_private_directory "$state_dir"
    state_dir=$(cd -- "$state_dir" && pwd -P)
    private_directory "$state_dir"
    # Resolve before creating children so an existing parent symlink cannot
    # redirect configuration creation outside the dedicated application home.
    for relative in .config/sandbox-container .config/openspec; do
        resolved=$(readlink -m -- "$state_dir/$relative")
        [[ "$resolved" == "$state_dir/"* ]] \
            || die "isolated configuration escapes state home: $state_dir/$relative"
        create_private_directory "$state_dir/$relative"
    done
    private_directory "$state_dir/.config/sandbox-container"
    if ((trust_host_ca)); then
        # Prevent the engine from creating a nested CA mount parent owned by a
        # subordinate mapped UID inside the writable isolated home.
        create_private_directory "$state_dir/ca"
        private_directory "$state_dir/ca"
    fi
    state_mounts+=(--volume "$state_dir:/sandbox-home:rw")
else
    config_dir="${SANDBOX_CONTAINER_CONFIG_DIR:-$HOME/.config/sandbox-container}"
    create_private_directory "$config_dir"
    config_dir=$(cd -- "$config_dir" && pwd -P)
    private_directory "$config_dir"
    create_private_directory "$HOME/.config/openspec"
    openspec_dir=$(cd -- "$HOME/.config/openspec" && pwd -P)
    state_mounts+=(
        --volume "$config_dir:/sandbox-home/.config/sandbox-container:rw"
        --volume "$openspec_dir:/sandbox-home/.config/openspec:rw"
    )
fi

ca_bundle=""
if ((trust_host_ca)); then
    if [[ -n "${SANDBOX_CONTAINER_CA_BUNDLE:-}" ]]; then
        [[ -f "$SANDBOX_CONTAINER_CA_BUNDLE" ]] || die "SANDBOX_CONTAINER_CA_BUNDLE is not a file: $SANDBOX_CONTAINER_CA_BUNDLE"
        ca_bundle=$(readlink -f -- "$SANDBOX_CONTAINER_CA_BUNDLE")
    else
        for candidate in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt; do
            if [[ -f "$candidate" ]]; then
                ca_bundle=$candidate
                break
            fi
        done
        [[ -n "$ca_bundle" ]] || die 'no default CA bundle found; set SANDBOX_CONTAINER_CA_BUNDLE to a bundle file'
    fi
fi

# The operator's toolchain library is mounted read-only; the shared module
# checks it stays private and outside every writable mount and the installation,
# and lists the default toolchains verified for this runtime recipe.
toolchain_library=''
toolchain_path=''
toolchain_env=()
if ((toolchains_enabled && ! qualification_probe)); then
    command -v python3 >/dev/null \
        || die 'host Python 3 is required for the toolchain library; set SANDBOX_CONTAINER_TOOLCHAINS=0 to omit it'
    toolchain_avoid=(--avoid "$workspace_mount")
    if [[ -n "$state_dir" ]]; then
        toolchain_avoid+=(--avoid "$state_dir")
    else
        toolchain_avoid+=(--avoid "$config_dir" --avoid "$openspec_dir")
    fi
    toolchain_output=$(python3 -I "$script_dir/setup/toolchains.py" launch-env "${toolchain_avoid[@]}") \
        || die 'toolchain library check failed; set SANDBOX_CONTAINER_TOOLCHAINS=0 to start without it'
    while IFS=$'\t' read -r toolchain_kind toolchain_first toolchain_second; do
        case "$toolchain_kind" in
            library) toolchain_library=$toolchain_first ;;
            path) toolchain_path+=":$toolchain_first" ;;
            env) toolchain_env+=(--env "$toolchain_first=$toolchain_second") ;;
            *) die 'unexpected toolchain library output' ;;
        esac
    done <<<"$toolchain_output"
    [[ "$toolchain_library" == /* ]] || die 'toolchain library check returned no library'
fi

# Restricted sessions use the shared helper; this wrapper keeps only the
# agent-specific command, environment, state and credentials.
session_helper=(python3 -I "$script_dir/network/session.py")
network_inputs=()
qualification_inputs=()
guard_digest=''
if [[ "$network_mode" != unrestricted ]]; then
    network_inputs=(--installation "$script_dir" --writable "$workspace_mount"
        --mount-target "$workspace_mount" --mount-target /sandbox-home)
    [[ -z "$toolchain_library" ]] || network_inputs+=(--mount-target /toolchains)
    if [[ -n "$state_dir" ]]; then
        network_inputs+=(--writable "$state_dir")
    else
        network_inputs+=(--writable "$config_dir" --writable "$openspec_dir")
    fi
    prepare_inputs=(--mode "$network_mode" --server-version "${network_version%$'\n'}"
        --backend "${network_backend%$'\n'}" --endpoint "${CONTAINER_HOST:-}" --engine "$runtime_info")
    if ((qualification_probe)); then
        prepare_inputs+=(--probe --qualification-input "${SANDBOX_CONTAINER_QUALIFICATION_INPUT:-}"
            --workspace "$workspace")
    fi
    prepared=$(printf '%s' "$network_platform" | "${session_helper[@]}" prepare "${network_inputs[@]}" "${prepare_inputs[@]}")
    read -r guard_digest qualification_token qualification_tls <<< "$prepared"
    if ((qualification_probe)); then
        qualification_inputs=(--probe --token "$qualification_token" --workspace "$workspace"
            --qualification-input "${SANDBOX_CONTAINER_QUALIFICATION_INPUT:-}")
        [[ "$qualification_tls" != 1 ]] || qualification_inputs+=(--tls)
    fi
fi

# The opted-in host CA bundle also verifies the runtime build's package fetches.
# It is a build secret: mounted only for its RUN step and never stored in a layer.
build_secret=()
if [[ -n "$ca_bundle" ]]; then
    build_secret=(--secret "id=build-ca,src=$ca_bundle")
fi
if ((build_image)); then
    [[ "${SANDBOX_CONTAINER_MAINTENANCE:-}" == 1 ]] || die 'image refresh requires exact SANDBOX_CONTAINER_MAINTENANCE=1; host pulls/build RUN steps are outside runtime filtering'
    podman build "${build_secret[@]}" --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
elif podman image exists "$image"; then
    :
else
    image_status=$?
    [[ "$image_status" == 1 ]] || die "cannot inspect image: $image"
    [[ "${SANDBOX_CONTAINER_MAINTENANCE:-}" == 1 ]] || die 'image is absent; prepare it with exact SANDBOX_CONTAINER_MAINTENANCE=1 (build traffic is outside runtime filtering)'
    podman build "${build_secret[@]}" --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
fi

if [[ "$network_mode" != unrestricted ]]; then
    capture_response runtime_image_id podman image inspect --format '{{.Id}}' "$image" \
        || die 'cannot resolve restricted runtime image identity'
    runtime_image_id=${runtime_image_id%$'\n'}
    [[ "$runtime_image_id" =~ ^(sha256:)?[a-f0-9]{64}$ ]] || die 'invalid restricted runtime image identity'
    image=$runtime_image_id
fi
# Default toolchain entries follow the image PATH, so they never replace the
# runtime's own node or python3; env.sh puts a toolchain first explicitly.
if [[ -n "$toolchain_path" ]]; then
    capture_response image_environment podman image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$image" \
        || die 'cannot inspect the runtime image environment'
    image_path=''
    while IFS= read -r image_variable; do
        [[ "$image_variable" != PATH=* ]] || { image_path=${image_variable#PATH=}; break; }
    done <<<"$image_environment"
    [[ -n "$image_path" ]] || image_path=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    toolchain_env=(--env "PATH=$image_path$toolchain_path" "${toolchain_env[@]}")
fi

container_args=(
    --rm --interactive --read-only
    --userns=keep-id --user "$caller_uid:$caller_gid"
    --cap-drop=all --security-opt=no-new-privileges
    "${budget_args[@]}"
    --workdir "$workspace"
    --tmpfs '/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777'
    --tmpfs '/run:rw,nosuid,nodev,noexec,size=16m'
    --tmpfs '/var/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777'
    # Mask engine default mounts at /run/secrets (RHEL subscription secrets from
    # mounts.conf): Podman skips its own mount there, leaving an empty read-only
    # tmpfs that the guard accepts and that exposes no host material.
    --mount type=tmpfs,destination=/run/secrets,ro=true
    # Podman forces /dev read-only with --read-only-tmpfs=false, and crun >= 1.27
    # must replace /dev/console to attach a terminal, so automatic provisioning
    # stays on. /dev and /dev/pts are left to the engine: an explicit /dev/pts mount
    # gets ptmxmode=000 (Podman rejects the option), so no pseudo-terminal could
    # be opened. Only /dev/shm is overridden, with an empty read-only tmpfs.
    --mount type=tmpfs,destination=/dev/shm,ro=true
    --env HOME=/sandbox-home
    --env EDITOR=nano --env VISUAL=nano
    --volume "$workspace_mount:$workspace_mount:rw"
    "${state_mounts[@]}"
)
if [[ -n "$toolchain_library" ]]; then
    container_args+=(--volume "$toolchain_library:/toolchains:ro,nosuid,nodev" "${toolchain_env[@]}")
fi
# The shell's own state follows the toolchain environment, so a toolchain cannot
# move the configuration directory or the Bash history.
container_args+=(--env SANDBOX_CONTAINER_CONFIG_DIR=/sandbox-home/.config/sandbox-container
    --env HISTFILE=/sandbox-home/.config/sandbox-container/bash_history)
((run_timeout == 0)) || container_args+=(--timeout "$run_timeout")
if [[ -t 0 && -t 1 ]]; then
    container_args+=(--tty)
    [[ -z "${TERM:-}" ]] || container_args+=(--env TERM)
fi
if ((podman_access)); then
    container_args+=(
        --volume "$host_socket:/run/podman/podman.sock:rw"
        --env CONTAINER_HOST=unix:///run/podman/podman.sock
    )
else
    container_args+=(--unsetenv CONTAINER_HOST)
fi
if ((trust_host_ca)); then
    container_args+=(
        --volume "$ca_bundle:/sandbox-home/ca/bundle.pem:ro"
        --env SSL_CERT_FILE=/sandbox-home/ca/bundle.pem
        --env REQUESTS_CA_BUNDLE=/sandbox-home/ca/bundle.pem
        --env CURL_CA_BUNDLE=/sandbox-home/ca/bundle.pem
        --env NODE_EXTRA_CA_CERTS=/sandbox-home/ca/bundle.pem
    )
fi

# The session is always Bash; --container-shell is accepted as a no-op and the
# remaining arguments go to Bash unchanged.
if ((qualification_probe)); then
    args=()  # The shared helper supplies the fixed probe command.
else
    container_args+=(--entrypoint /bin/bash)
fi

prefix=${workspace##*/}
prefix=$(printf '%s' "$prefix" | sed -E 's/[^a-zA-Z0-9_.-]+/-/g; s/^[.-]+//; s/[.-]+$//')
prefix=${prefix:-sandbox-container}
names=$(podman ps --all --format '{{.Names}}') || die 'cannot list Podman containers'
next_index=0
while IFS= read -r name; do
    [[ "$name" == "$prefix-"* ]] || continue
    suffix=${name#"$prefix-"}
    [[ "$suffix" =~ ^[0-9]+$ && ${#suffix} -lt 10 ]] || continue
    numeric=$((10#$suffix))
    ((numeric < next_index)) || next_index=$((numeric + 1))
done <<< "$names"

# Reserve the name with create, so an actual process exit code 125 is never
# confused with a create-time naming collision. Remove only our own container.
container_id=''
client_pid=''
diagnostics_pid=''
diagnostics_fd=''
create_pid=''
session_dir=''
session_token=''
cid_file=''
create_output=''
creation_pending=0
shutdown_deadline=0
ownership_label=io.sandbox-container.session
qualification_check_pid=''

cleanup_warning() {
    printf 'sandbox-container: cleanup %s (container=%s session=%s); inspect the Podman engine for remaining session containers\n' \
        "$*" "${container_id:-unknown}" "${session_token:-unknown}" >&2
}

# All shutdown engine calls share a deadline and reserve time for local clients.
control() {
    local remaining=$((shutdown_deadline - SECONDS - 2)) duration status
    if ((remaining < 2)); then
        cleanup_warning "deadline exhausted before $1"
        return 124
    fi
    duration=$((remaining - 1))
    ((duration <= 2)) || duration=2
    if timeout --kill-after=1s "${duration}s" podman "$@"; then
        return 0
    else
        status=$?
        cleanup_warning "$1 failed or timed out (status $status)"
        return "$status"
    fi
}

# Consult Bash's child table, so a recycled PID cannot select another process.
child_running() {
    local child=$1 running
    [[ -n "$child" ]] || return 1
    while IFS= read -r running; do
        [[ "$running" != "$child" ]] || return 0
    done < <(jobs -pr)
    return 1
}

reap_client() {
    local child=$1 until
    [[ -n "$child" ]] || return 0
    if child_running "$child"; then
        kill -TERM "$child" 2>/dev/null || true
        until=$((SECONDS + 1))
        while child_running "$child" && ((SECONDS < until && SECONDS < shutdown_deadline - 1)); do
            sleep 0.05
        done
        if child_running "$child"; then
            kill -KILL "$child" 2>/dev/null || true
        fi
    fi
    while child_running "$child" && ((SECONDS < shutdown_deadline)); do
        sleep 0.05
    done
    if child_running "$child"; then
        cleanup_warning "local client $child did not terminate within the deadline"
    else
        wait "$child" 2>/dev/null || true
    fi
}

recover_container() {
    local candidate='' owner ids
    [[ -z "$container_id" && "$creation_pending" == 1 ]] || return 0
    if [[ -s "$cid_file" ]]; then
        candidate=$(<"$cid_file")
    elif [[ -s "$create_output" ]]; then
        candidate=$(<"$create_output")
    fi
    if [[ ! "$candidate" =~ ^[a-f0-9]{64}$ ]]; then
        if ! ids=$(control ps --all --no-trunc --filter "label=$ownership_label=$session_token" --format '{{.ID}}'); then
            return 1
        fi
        candidate=$ids
    fi
    [[ -n "$candidate" ]] || return 0
    [[ "$candidate" =~ ^[a-f0-9]{64}$ ]] || { cleanup_warning 'invalid recovered container identity'; return 1; }
    if owner=$(control inspect --type container --format "{{index .Config.Labels \"$ownership_label\"}}" "$candidate") \
        && [[ "$owner" == "$session_token" ]]; then
        container_id=$candidate
    else
        cleanup_warning 'could not confirm recovered container ownership'
        return 1
    fi
}

# Keep collision reconciliation interruptible just like the create request.
creation_lookup() {
    local lookup_status=0
    podman "$@" >"$session_dir/lookup" &
    create_pid=$!
    wait "$create_pid" || lookup_status=$?
    create_pid=''
    return "$lookup_status"
}

# shellcheck disable=SC2329 # Invoked by EXIT and signal traps.
shutdown() {
    local primary_status=$1 signal=${2:-} graceful_until diagnostics_until
    trap - EXIT
    trap '' TERM INT HUP
    set +e
    shutdown_deadline=$((SECONDS + 20))
    if [[ -n "$qualification_check_pid" ]]; then
        kill -TERM "$qualification_check_pid" 2>/dev/null || true
        graceful_until=$((SECONDS + 13))
        while child_running "$qualification_check_pid" && ((SECONDS < graceful_until && SECONDS < shutdown_deadline - 4)); do
            sleep 0.05
        done
        if child_running "$qualification_check_pid"; then
            cleanup_warning 'qualification helper did not confirm cleanup before the deadline'
            kill -KILL "$qualification_check_pid" 2>/dev/null || true
        fi
        reap_client "$qualification_check_pid"
    fi
    if [[ -n "$diagnostics_fd" ]]; then
        exec {diagnostics_fd}>&-
        diagnostics_fd=''
    fi
    if [[ -n "$session_dir" ]]; then
        recover_container
        if [[ -n "$signal" && -n "$container_id" && -n "$client_pid" ]]; then
            control kill --signal "$signal" "$container_id" >/dev/null
            graceful_until=$((SECONDS + 5))
            while child_running "$client_pid" && ((SECONDS < graceful_until && SECONDS < shutdown_deadline - 6)); do
                sleep 0.05
            done
        fi
        [[ -z "$container_id" ]] || control rm --force --time 0 --ignore "$container_id" >/dev/null
        reap_client "$create_pid"
        reap_client "$client_pid"
        # Drain the final client log before reaping its owned stderr adapter.
        diagnostics_until=$((SECONDS + 1))
        while child_running "$diagnostics_pid" && ((SECONDS < diagnostics_until && SECONDS < shutdown_deadline - 1)); do
            sleep 0.01
        done
        reap_client "$diagnostics_pid"
        # Cancellation can race with the server publishing its create result.
        if ((creation_pending)) && [[ -z "$container_id" ]]; then
            recover_container
            if [[ -n "$container_id" ]]; then
                control rm --force --time 0 --ignore "$container_id" >/dev/null
            elif [[ -n "$signal" ]]; then
                cleanup_warning 'interrupted creation could not be reconciled'
            fi
        fi
        rm -rf -- "$session_dir"
    fi
    exit "$primary_status"
}
trap 'shutdown "$?"' EXIT
trap 'shutdown 143 TERM' TERM
trap 'shutdown 130 INT' INT
trap 'shutdown 129 HUP' HUP
session_dir=$(umask 077; mktemp -d)
session_token=${session_dir##*/}
printf 'sandbox-container: network mode=%s\n' "$network_mode" >&2
if [[ "$network_mode" != unrestricted ]] && ((qualification_probe == 0)); then
    SANDBOX_CONTAINER_IMAGE="$image" python3 -I "$script_dir/network/qualify.py" check &
    qualification_check_pid=$!
    if wait "$qualification_check_pid"; then
        qualification_check_pid=''
    else
        qualification_status=$?
        qualification_check_pid=''
        exit "$qualification_status"
    fi
fi
if [[ "$network_mode" != unrestricted ]]; then
    application=()
    ((qualification_probe)) || application=(/bin/bash "${args[@]}")
    "${session_helper[@]}" agent-args --installation "$script_dir" --mode "$network_mode" \
        --session "$session_dir" --guard-digest "$guard_digest" "${qualification_inputs[@]}" \
        -- "${application[@]}" >"$session_dir/agent.args"
    mapfile -d '' -t restricted <"$session_dir/agent.args"
    [[ "${restricted[0]:-}" =~ ^[0-9]+$ ]] || die 'invalid restricted session arguments'
    container_args+=("${restricted[@]:1:${restricted[0]}}")
    args=("${restricted[@]:$((1 + restricted[0]))}")
fi
# Measure the session from just before the container is created, so the
# engine's lifetime limit cannot have started earlier, with a monotonic clock:
# WSL2 steps the wall clock to resynchronise with the host, which moves
# EPOCHREALTIME and SECONDS by seconds at a time, and whole-second SECONDS would
# also report a short failing session crossing a second boundary as a reached
# limit. /proc/uptime counts centiseconds since boot.
elapsed_centiseconds() {
    local now=''
    read -r now _ 2>/dev/null </proc/uptime || now=''
    now=${now//[!0-9]/}
    [[ -n "$now" ]] || now=$((SECONDS * 100))
    printf '%s' "$((10#$now - ${1:-0}))"
}
started_at=$(elapsed_centiseconds)
for ((attempt=0; attempt<20; attempt++)); do
    name="$prefix-$next_index"
    cid_file=$session_dir/$attempt.cid
    create_output=$session_dir/$attempt.stdout
    create_error=$session_dir/$attempt.stderr
    creation_pending=1
    podman create --name "$name" --cidfile "$cid_file" --label "$ownership_label=$session_token" \
        "${container_args[@]}" "$image" "${args[@]}" >"$create_output" 2>"$create_error" &
    create_pid=$!
    if wait "$create_pid"; then
        create_pid=''
        container_id=$(<"$create_output")
        [[ "$container_id" =~ ^[a-f0-9]{64}$ ]] || die 'invalid container ID returned by Podman create'
        creation_pending=0
        break
    else
        create_status=$?
        create_pid=''
        if [[ ! -s "$cid_file" && ! -s "$create_output" ]] && creation_lookup container exists "$name" \
            && creation_lookup inspect --type container --format "{{index .Config.Labels \"$ownership_label\"}}" "$name" \
            && [[ $(<"$session_dir/lookup") != "$session_token" ]]; then
            creation_pending=0
            next_index=$((next_index + 1))
        else
            cat -- "$create_error" >&2
            exit "$create_status"
        fi
    fi
done
[[ -n "$container_id" ]] || die 'could not reserve a container name after 20 attempts'

# Engine flags alone are not evidence: require the created configuration to
# carry every enforced budget and no unenforced one. Setup smoke and
# qualification measure the effective cgroups.
capture_response configured_budgets timeout --kill-after=1s 10s podman inspect --type container \
    --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}' "$container_id" \
    || die 'cannot inspect agent resource budgets; agent not started'
read -r configured_memory configured_cpu configured_pids extra <<< "${configured_budgets%$'\n'}"
budgets_applied=0
if [[ -z "${extra:-}" && "$configured_memory" == "$expected_memory" && "$configured_cpu" == "$expected_cpu" ]]; then
    if ((pids_enforced)); then
        [[ "$configured_pids" == "$pids_limit" ]] && budgets_applied=1
    else
        [[ "$configured_pids" =~ ^(0|-1)$ ]] && budgets_applied=1
    fi
fi
((budgets_applied)) \
    || die "agent resource budgets were not applied as expected (memory=$expected_memory nano_cpus=$expected_cpu pids=$( ((pids_enforced)) && printf '%s' "$pids_limit" || printf 'unenforced')); engine reports controllers $cgroup_controllers; check rootless cgroup v2 controller delegation; agent not started"

# Explicit stdin redirection prevents Bash from replacing stdin with /dev/null
# for the background client; traps can forward signals while wait is active.
if [[ -f "$script_dir/setup/diagnostics.py" ]] && command -v python3 >/dev/null; then
    # Optional for legacy unrestricted installs without host Python. Only the
    # exact successful Podman 4.3 restart-check line changes level; errors pass.
    mkfifo -- "$session_dir/diagnostics.pipe"
    python3 -I "$script_dir/setup/diagnostics.py" <"$session_dir/diagnostics.pipe" >&2 &
    diagnostics_pid=$!
    exec {diagnostics_fd}>"$session_dir/diagnostics.pipe"
    podman start --attach --interactive --sig-proxy=false "$container_id" <&0 2>&"$diagnostics_fd" {diagnostics_fd}>&- &
    client_pid=$!
    exec {diagnostics_fd}>&-
    diagnostics_fd=''
else
    podman start --attach --interactive --sig-proxy=false "$container_id" <&0 &
    client_pid=$!
fi
status=0
wait "$client_pid" || status=$?
if ((run_timeout > 0 && status != 0 && $(elapsed_centiseconds "$started_at") >= run_timeout * 100)); then
    printf 'sandbox-container: session lifetime limit reached (%s s); exit status %s\n' "$run_timeout" "$status" >&2
fi
exit "$status"
